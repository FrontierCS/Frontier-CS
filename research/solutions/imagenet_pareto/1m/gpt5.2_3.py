import os
import math
import copy
from typing import Optional, Tuple, Dict, Any, List

import torch
import torch.nn as nn
import torch.nn.functional as F


class CosineLinear(nn.Module):
    def __init__(self, in_features: int, out_features: int, init_scale: float = 30.0):
        super().__init__()
        self.in_features = in_features
        self.out_features = out_features
        self.weight = nn.Parameter(torch.empty(out_features, in_features))
        nn.init.normal_(self.weight, mean=0.0, std=0.02)
        self.scale = nn.Parameter(torch.tensor(float(init_scale), dtype=torch.float32))

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = F.normalize(x, dim=-1)
        w = F.normalize(self.weight, dim=-1)
        return F.linear(x, w) * self.scale


class HybridNet(nn.Module):
    def __init__(
        self,
        input_dim: int,
        num_classes: int,
        hidden_dim: int,
        mean: torch.Tensor,
        std: torch.Tensor,
        centroids: Optional[torch.Tensor] = None,
        dropout: float = 0.10,
        input_noise: float = 0.03,
        proto_scale: float = 15.0,
        proto_coef: float = 0.0,
    ):
        super().__init__()
        self.register_buffer("mean", mean.view(1, -1).contiguous())
        self.register_buffer("std", std.view(1, -1).contiguous())

        self.fc1 = nn.Linear(input_dim, hidden_dim, bias=True)
        self.ln1 = nn.LayerNorm(hidden_dim)
        self.fc2 = nn.Linear(hidden_dim, hidden_dim, bias=True)
        self.ln2 = nn.LayerNorm(hidden_dim)
        self.ln3 = nn.LayerNorm(hidden_dim)

        self.drop = nn.Dropout(dropout)
        self.head = CosineLinear(hidden_dim, num_classes, init_scale=30.0)

        self.input_noise = float(input_noise)

        if centroids is None:
            self.register_buffer("centroids_norm", None)
        else:
            c = centroids.contiguous()
            c = F.normalize(c, dim=1)
            self.register_buffer("centroids_norm", c)

        self.proto_scale = float(proto_scale)
        self.proto_coef = float(proto_coef)

    def set_dropout(self, p: float) -> None:
        self.drop.p = float(p)

    def set_input_noise(self, s: float) -> None:
        self.input_noise = float(s)

    def set_proto_coef(self, c: float) -> None:
        self.proto_coef = float(c)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        if x.dtype != torch.float32:
            x = x.float()

        z = (x - self.mean) / self.std
        if self.training and self.input_noise > 0.0:
            z = z + torch.randn_like(z) * self.input_noise

        h = self.fc1(z)
        h = self.ln1(h)
        h = F.gelu(h)
        h = self.drop(h)

        r = h
        h = self.fc2(h)
        h = self.ln2(h)
        h = F.gelu(h)
        h = self.drop(h)
        h = h + r

        h = self.ln3(h)
        logits = self.head(h)

        if self.centroids_norm is not None and self.proto_coef != 0.0:
            z_norm = F.normalize(z, dim=1)
            proto_logits = (z_norm @ self.centroids_norm.t()) * self.proto_scale
            logits = logits + proto_logits * self.proto_coef

        return logits


def _collect_from_loader(loader) -> Tuple[torch.Tensor, torch.Tensor]:
    xs = []
    ys = []
    for batch in loader:
        if isinstance(batch, (list, tuple)) and len(batch) >= 2:
            x, y = batch[0], batch[1]
        else:
            raise ValueError("Expected DataLoader to yield (inputs, targets).")
        if not torch.is_tensor(x):
            x = torch.as_tensor(x)
        if not torch.is_tensor(y):
            y = torch.as_tensor(y)
        if x.ndim > 2:
            x = x.view(x.shape[0], -1)
        xs.append(x.detach().cpu())
        ys.append(y.detach().cpu())
    X = torch.cat(xs, dim=0).contiguous()
    Y = torch.cat(ys, dim=0).contiguous()
    return X, Y


@torch.no_grad()
def _compute_centroids(z: torch.Tensor, y: torch.Tensor, num_classes: int) -> torch.Tensor:
    d = z.shape[1]
    centroids = torch.zeros((num_classes, d), dtype=z.dtype, device=z.device)
    counts = torch.zeros((num_classes,), dtype=torch.float32, device=z.device)
    for c in range(num_classes):
        m = (y == c)
        if m.any():
            centroids[c] = z[m].mean(dim=0)
            counts[c] = float(m.sum().item())
    for c in range(num_classes):
        if counts[c] == 0:
            centroids[c].zero_()
    return centroids


@torch.no_grad()
def _accuracy(model: nn.Module, X: torch.Tensor, y: torch.Tensor, batch_size: int = 512) -> float:
    model.eval()
    n = X.shape[0]
    correct = 0
    for i in range(0, n, batch_size):
        xb = X[i:i + batch_size]
        yb = y[i:i + batch_size]
        logits = model(xb)
        pred = logits.argmax(dim=1)
        correct += (pred == yb).sum().item()
    return float(correct) / float(n)


def _make_param_groups(model: nn.Module, weight_decay: float) -> List[Dict[str, Any]]:
    decay = []
    no_decay = []
    for name, p in model.named_parameters():
        if not p.requires_grad:
            continue
        if p.ndim == 1 or name.endswith(".bias") or ".ln" in name or "layernorm" in name.lower() or "norm" in name.lower():
            no_decay.append(p)
        else:
            decay.append(p)
    groups = []
    if decay:
        groups.append({"params": decay, "weight_decay": float(weight_decay)})
    if no_decay:
        groups.append({"params": no_decay, "weight_decay": 0.0})
    return groups


def _train_mlp(
    model: nn.Module,
    X_train: torch.Tensor,
    y_train: torch.Tensor,
    X_val: torch.Tensor,
    y_val: torch.Tensor,
    epochs: int,
    batch_size: int,
    lr: float,
    weight_decay: float,
    label_smoothing: float,
    warmup_frac: float = 0.08,
    patience: int = 30,
    min_epochs: int = 40,
) -> Tuple[nn.Module, float]:
    n = X_train.shape[0]
    steps_per_epoch = max(1, (n + batch_size - 1) // batch_size)
    total_steps = max(1, steps_per_epoch * epochs)
    warmup_steps = int(total_steps * warmup_frac)
    warmup_steps = max(1, warmup_steps)

    optimizer = torch.optim.AdamW(_make_param_groups(model, weight_decay), lr=float(lr), betas=(0.9, 0.999), eps=1e-8)

    def lr_lambda(step: int) -> float:
        if step < warmup_steps:
            return float(step + 1) / float(warmup_steps)
        t = float(step - warmup_steps) / float(max(1, total_steps - warmup_steps))
        return 0.5 * (1.0 + math.cos(math.pi * t))

    scheduler = torch.optim.lr_scheduler.LambdaLR(optimizer, lr_lambda=lr_lambda)
    criterion = nn.CrossEntropyLoss(label_smoothing=float(label_smoothing))

    best_acc = -1.0
    best_state = None
    bad_epochs = 0
    global_step = 0

    for epoch in range(epochs):
        model.train()
        perm = torch.randperm(n)
        for i in range(0, n, batch_size):
            idx = perm[i:i + batch_size]
            xb = X_train[idx]
            yb = y_train[idx]

            logits = model(xb)
            loss = criterion(logits, yb)

            optimizer.zero_grad(set_to_none=True)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
            scheduler.step()
            global_step += 1

        val_acc = _accuracy(model, X_val, y_val, batch_size=1024)
        if val_acc > best_acc + 1e-6:
            best_acc = val_acc
            best_state = copy.deepcopy(model.state_dict())
            bad_epochs = 0
        else:
            bad_epochs += 1

        if epoch + 1 >= min_epochs and bad_epochs >= patience:
            break

    if best_state is not None:
        model.load_state_dict(best_state)
    return model, float(best_acc)


class Solution:
    def solve(self, train_loader, val_loader, metadata: dict = None) -> torch.nn.Module:
        if metadata is None:
            metadata = {}
        input_dim = int(metadata.get("input_dim", 384))
        num_classes = int(metadata.get("num_classes", 128))
        param_limit = int(metadata.get("param_limit", 1_000_000))
        device = str(metadata.get("device", "cpu"))

        try:
            torch.set_num_threads(min(8, os.cpu_count() or 8))
        except Exception:
            pass

        torch.manual_seed(0)

        X_train, y_train = _collect_from_loader(train_loader)
        if val_loader is None:
            X_val, y_val = X_train.clone(), y_train.clone()
        else:
            X_val, y_val = _collect_from_loader(val_loader)

        if X_train.ndim != 2 or X_train.shape[1] != input_dim:
            X_train = X_train.view(X_train.shape[0], -1)
        if X_val.ndim != 2 or X_val.shape[1] != input_dim:
            X_val = X_val.view(X_val.shape[0], -1)

        X_train = X_train.to(device=device, dtype=torch.float32).contiguous()
        y_train = y_train.to(device=device, dtype=torch.long).contiguous()
        X_val = X_val.to(device=device, dtype=torch.float32).contiguous()
        y_val = y_val.to(device=device, dtype=torch.long).contiguous()

        mean = X_train.mean(dim=0)
        std = X_train.std(dim=0, unbiased=False).clamp_min(1e-6)

        with torch.no_grad():
            z_train = (X_train - mean) / std
            centroids = _compute_centroids(z_train, y_train, num_classes=num_classes)

        def build_with_hidden(h: int) -> HybridNet:
            return HybridNet(
                input_dim=input_dim,
                num_classes=num_classes,
                hidden_dim=h,
                mean=mean,
                std=std,
                centroids=centroids,
                dropout=0.10,
                input_noise=0.03,
                proto_scale=15.0,
                proto_coef=0.0,
            ).to(device)

        hidden_dim = 768
        for h in range(hidden_dim, 255, -8):
            m = build_with_hidden(h)
            trainable_params = sum(p.numel() for p in m.parameters() if p.requires_grad)
            if trainable_params <= param_limit:
                hidden_dim = h
                model = m
                break
        else:
            model = build_with_hidden(256)

        trainable_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
        if trainable_params > param_limit:
            while trainable_params > param_limit and hidden_dim > 64:
                hidden_dim = max(64, hidden_dim - 16)
                model = build_with_hidden(hidden_dim)
                trainable_params = sum(p.numel() for p in model.parameters() if p.requires_grad)

        model.set_proto_coef(0.0)

        model, _ = _train_mlp(
            model=model,
            X_train=X_train,
            y_train=y_train,
            X_val=X_val,
            y_val=y_val,
            epochs=220,
            batch_size=256,
            lr=3.5e-3,
            weight_decay=1.2e-2,
            label_smoothing=0.05,
            warmup_frac=0.10,
            patience=35,
            min_epochs=60,
        )

        model.set_dropout(0.0)
        model.set_input_noise(0.0)

        model, _ = _train_mlp(
            model=model,
            X_train=X_train,
            y_train=y_train,
            X_val=X_val,
            y_val=y_val,
            epochs=90,
            batch_size=256,
            lr=1.2e-3,
            weight_decay=4.0e-3,
            label_smoothing=0.00,
            warmup_frac=0.08,
            patience=25,
            min_epochs=25,
        )

        best_coef = 0.0
        best_acc = _accuracy(model, X_val, y_val, batch_size=1024)
        for coef in (0.0, 0.15, 0.3, 0.5, 0.8, 1.2, 1.8, 2.5, 3.5):
            model.set_proto_coef(coef)
            acc = _accuracy(model, X_val, y_val, batch_size=1024)
            if acc > best_acc + 1e-6:
                best_acc = acc
                best_coef = coef
        model.set_proto_coef(best_coef)

        model.eval()
        return model