import os
import math
import copy
import random
from dataclasses import dataclass

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import TensorDataset, DataLoader


class _ResidualBottleneckBlock(nn.Module):
    def __init__(self, hidden_dim: int, bottleneck_dim: int, dropout: float):
        super().__init__()
        self.ln = nn.LayerNorm(hidden_dim)
        self.fc1 = nn.Linear(hidden_dim, bottleneck_dim)
        self.fc2 = nn.Linear(bottleneck_dim, hidden_dim)
        self.act = nn.GELU()
        self.drop = nn.Dropout(dropout)
        self.alpha = nn.Parameter(torch.tensor(0.1, dtype=torch.float32))

        nn.init.xavier_uniform_(self.fc1.weight)
        nn.init.zeros_(self.fc1.bias)
        nn.init.xavier_uniform_(self.fc2.weight)
        with torch.no_grad():
            self.fc2.weight.mul_(0.1)
        nn.init.zeros_(self.fc2.bias)

    def forward(self, x):
        h = self.ln(x)
        h = self.fc1(h)
        h = self.act(h)
        h = self.fc2(h)
        h = self.drop(h)
        return x + self.alpha * h


class _ResidualMLP(nn.Module):
    def __init__(self, input_dim: int, num_classes: int, hidden_dim: int, bottleneck_dim: int, n_blocks: int, dropout: float):
        super().__init__()
        self.inp = nn.Linear(input_dim, hidden_dim)
        self.blocks = nn.ModuleList([_ResidualBottleneckBlock(hidden_dim, bottleneck_dim, dropout) for _ in range(n_blocks)])
        self.ln_out = nn.LayerNorm(hidden_dim)
        self.head = nn.Linear(hidden_dim, num_classes)

        nn.init.xavier_uniform_(self.inp.weight)
        nn.init.zeros_(self.inp.bias)
        nn.init.xavier_uniform_(self.head.weight)
        nn.init.zeros_(self.head.bias)

    def forward(self, x):
        x = self.inp(x)
        for blk in self.blocks:
            x = blk(x)
        x = self.ln_out(x)
        return self.head(x)


class _HybridModel(nn.Module):
    def __init__(
        self,
        input_dim: int,
        num_classes: int,
        mean: torch.Tensor,
        inv_std: torch.Tensor,
        centroid_w_t: torch.Tensor,
        centroid_b: torch.Tensor,
        hidden_dim: int,
        bottleneck_dim: int,
        n_blocks: int,
        dropout: float,
    ):
        super().__init__()
        self.register_buffer("mean", mean.detach().clone().to(dtype=torch.float32))
        self.register_buffer("inv_std", inv_std.detach().clone().to(dtype=torch.float32))
        self.register_buffer("centroid_w_t", centroid_w_t.detach().clone().to(dtype=torch.float32))
        self.register_buffer("centroid_b", centroid_b.detach().clone().to(dtype=torch.float32))
        self.backbone = _ResidualMLP(input_dim, num_classes, hidden_dim, bottleneck_dim, n_blocks, dropout)
        self.centroid_scale = nn.Parameter(torch.tensor(0.5, dtype=torch.float32))

    def forward(self, x):
        if x.dim() > 2:
            x = x.view(x.size(0), -1)
        x = x.to(dtype=torch.float32)
        x = (x - self.mean) * self.inv_std
        logits = self.backbone(x)
        logits = logits + self.centroid_scale * (x.matmul(self.centroid_w_t) + self.centroid_b)
        return logits


def _count_trainable_params(m: nn.Module) -> int:
    return sum(p.numel() for p in m.parameters() if p.requires_grad)


def _accuracy(model: nn.Module, loader: DataLoader, device: torch.device) -> float:
    model.eval()
    correct = 0
    total = 0
    with torch.inference_mode():
        for xb, yb in loader:
            xb = xb.to(device, non_blocking=True)
            yb = yb.to(device, non_blocking=True)
            logits = model(xb)
            pred = logits.argmax(dim=1)
            correct += (pred == yb).sum().item()
            total += yb.numel()
    if total == 0:
        return 0.0
    return correct / total


def _make_cached_tensors(loader, device: torch.device):
    xs = []
    ys = []
    for xb, yb in loader:
        xb = xb.detach().to("cpu")
        yb = yb.detach().to("cpu")
        if xb.dim() > 2:
            xb = xb.view(xb.size(0), -1)
        xs.append(xb.to(dtype=torch.float32, non_blocking=True))
        ys.append(yb.to(dtype=torch.long, non_blocking=True))
    if len(xs) == 0:
        return None, None
    X = torch.cat(xs, dim=0)
    Y = torch.cat(ys, dim=0)
    return X, Y


def _compute_standardization(X: torch.Tensor, eps: float = 1e-6):
    mean = X.mean(dim=0)
    var = X.var(dim=0, unbiased=False)
    std = torch.sqrt(var + eps)
    inv_std = 1.0 / std
    return mean, inv_std


def _compute_centroids_standardized(X: torch.Tensor, y: torch.Tensor, num_classes: int):
    n, d = X.shape
    sums = torch.zeros((num_classes, d), dtype=torch.float32)
    counts = torch.zeros((num_classes, 1), dtype=torch.float32)
    ones = torch.ones((n, 1), dtype=torch.float32)
    sums.index_add_(0, y, X)
    counts.index_add_(0, y, ones)
    counts = counts.clamp_min(1.0)
    mu = sums / counts
    w = 2.0 * mu
    b = -(mu * mu).sum(dim=1)
    return w.t().contiguous(), b.contiguous()


def _build_best_model(input_dim: int, num_classes: int, param_limit: int, mean: torch.Tensor, inv_std: torch.Tensor, centroid_w_t: torch.Tensor, centroid_b: torch.Tensor, device: torch.device):
    hidden_candidates = [1536, 1408, 1280, 1152, 1088, 1024, 992, 960, 928, 896, 864, 832, 800, 768, 736, 704, 672, 640, 608, 576, 544, 512, 480, 448, 416, 384, 352, 320, 288, 256]
    block_candidates = [10, 9, 8, 7, 6, 5, 4, 3, 2]
    dropout_candidates = [0.08, 0.10, 0.05]

    best = None
    best_params = -1
    margin_limit = int(param_limit * 0.998)

    for dropout in dropout_candidates:
        for hidden_dim in hidden_candidates:
            bottleneck_dim = max(64, hidden_dim // 4)
            for n_blocks in block_candidates:
                model = _HybridModel(
                    input_dim=input_dim,
                    num_classes=num_classes,
                    mean=mean,
                    inv_std=inv_std,
                    centroid_w_t=centroid_w_t,
                    centroid_b=centroid_b,
                    hidden_dim=hidden_dim,
                    bottleneck_dim=bottleneck_dim,
                    n_blocks=n_blocks,
                    dropout=dropout,
                ).to(device)
                pcount = _count_trainable_params(model)
                if pcount <= margin_limit and pcount > best_params:
                    best_params = pcount
                    best = (hidden_dim, bottleneck_dim, n_blocks, dropout)
                del model
    if best is None:
        best = (512, max(64, 512 // 4), 3, 0.08)

    hidden_dim, bottleneck_dim, n_blocks, dropout = best
    model = _HybridModel(
        input_dim=input_dim,
        num_classes=num_classes,
        mean=mean,
        inv_std=inv_std,
        centroid_w_t=centroid_w_t,
        centroid_b=centroid_b,
        hidden_dim=hidden_dim,
        bottleneck_dim=bottleneck_dim,
        n_blocks=n_blocks,
        dropout=dropout,
    ).to(device)
    return model


def _make_optimizer(model: nn.Module, lr: float, weight_decay: float):
    decay = []
    no_decay = []
    for n, p in model.named_parameters():
        if not p.requires_grad:
            continue
        if n.endswith(".bias") or (".ln." in n) or (".ln_out." in n) or ("layernorm" in n.lower()) or n.endswith(".alpha") or n.endswith("centroid_scale"):
            no_decay.append(p)
        else:
            no_decay_names = ("ln.weight", "ln.bias", "ln_out.weight", "ln_out.bias")
            if any(s in n for s in no_decay_names):
                no_decay.append(p)
            else:
                decay.append(p)
    param_groups = [
        {"params": decay, "weight_decay": weight_decay},
        {"params": no_decay, "weight_decay": 0.0},
    ]
    return torch.optim.AdamW(param_groups, lr=lr, betas=(0.9, 0.95), eps=1e-8)


class Solution:
    def solve(self, train_loader, val_loader, metadata: dict = None) -> torch.nn.Module:
        if metadata is None:
            metadata = {}
        input_dim = int(metadata.get("input_dim", 384))
        num_classes = int(metadata.get("num_classes", 128))
        param_limit = int(metadata.get("param_limit", 2_500_000))
        device_str = metadata.get("device", "cpu")
        device = torch.device(device_str if device_str else "cpu")

        try:
            n_threads = min(8, os.cpu_count() or 8)
            torch.set_num_threads(n_threads)
            torch.set_num_interop_threads(1)
        except Exception:
            pass

        seed = 0
        random.seed(seed)
        np.random.seed(seed)
        torch.manual_seed(seed)

        X_train, y_train = _make_cached_tensors(train_loader, device=device)
        if X_train is None:
            model = nn.Linear(input_dim, num_classes).to(device)
            return model.eval()

        X_val, y_val = _make_cached_tensors(val_loader, device=device) if val_loader is not None else (None, None)

        mean, inv_std = _compute_standardization(X_train, eps=1e-6)
        Xs_train = (X_train - mean) * inv_std
        centroid_w_t, centroid_b = _compute_centroids_standardized(Xs_train, y_train, num_classes=num_classes)

        model = _build_best_model(
            input_dim=input_dim,
            num_classes=num_classes,
            param_limit=param_limit,
            mean=mean,
            inv_std=inv_std,
            centroid_w_t=centroid_w_t,
            centroid_b=centroid_b,
            device=device,
        )

        if _count_trainable_params(model) > param_limit:
            model = _HybridModel(
                input_dim=input_dim,
                num_classes=num_classes,
                mean=mean,
                inv_std=inv_std,
                centroid_w_t=centroid_w_t,
                centroid_b=centroid_b,
                hidden_dim=640,
                bottleneck_dim=160,
                n_blocks=3,
                dropout=0.08,
            ).to(device)

        train_bs = min(256, int(X_train.size(0)))
        val_bs = 512 if (X_val is not None and X_val.size(0) >= 512) else (min(512, int(X_val.size(0))) if X_val is not None else 512)

        gen = torch.Generator(device="cpu")
        gen.manual_seed(seed)

        train_ds = TensorDataset(X_train, y_train)
        train_dl = DataLoader(train_ds, batch_size=train_bs, shuffle=True, generator=gen, num_workers=0, drop_last=False)

        if X_val is not None:
            val_ds = TensorDataset(X_val, y_val)
            val_dl = DataLoader(val_ds, batch_size=val_bs, shuffle=False, num_workers=0, drop_last=False)
        else:
            val_dl = None

        base_lr = 2.5e-3 * math.sqrt(train_bs / 256.0)
        weight_decay = 0.06
        optimizer = _make_optimizer(model, lr=base_lr, weight_decay=weight_decay)

        max_epochs = 220 if val_dl is not None else 160
        steps_per_epoch = max(1, len(train_dl))
        total_steps = max_epochs * steps_per_epoch
        warmup_steps = max(20, int(0.08 * total_steps))
        min_lr_mult = 0.02

        def lr_lambda(step: int):
            if step < warmup_steps:
                return float(step) / float(max(1, warmup_steps))
            t = (step - warmup_steps) / float(max(1, total_steps - warmup_steps))
            return min_lr_mult + 0.5 * (1.0 - min_lr_mult) * (1.0 + math.cos(math.pi * t))

        scheduler = torch.optim.lr_scheduler.LambdaLR(optimizer, lr_lambda=lr_lambda)

        label_smoothing = 0.06
        criterion = nn.CrossEntropyLoss(label_smoothing=label_smoothing)

        use_mixup = True
        mixup_alpha = 0.2
        noise_std = 0.01

        model_ema = copy.deepcopy(model).to(device)
        ema_decay = 0.995

        best_state = None
        best_acc = -1.0
        no_improve = 0
        patience = 40 if val_dl is not None else 25

        global_step = 0
        for epoch in range(max_epochs):
            model.train()
            for xb, yb in train_dl:
                xb = xb.to(device, non_blocking=True)
                yb = yb.to(device, non_blocking=True)

                if noise_std > 0:
                    xb = xb + noise_std * torch.randn_like(xb)

                if use_mixup and xb.size(0) > 1:
                    if torch.rand((), device=device).item() < 0.5:
                        perm = torch.randperm(xb.size(0), device=device)
                        xb2 = xb[perm]
                        yb2 = yb[perm]
                        lam = np.random.beta(mixup_alpha, mixup_alpha)
                        lam = float(lam)
                        xb = xb.mul(lam).add_(xb2, alpha=(1.0 - lam))
                        logits = model(xb)
                        loss = lam * criterion(logits, yb) + (1.0 - lam) * criterion(logits, yb2)
                    else:
                        logits = model(xb)
                        loss = criterion(logits, yb)
                else:
                    logits = model(xb)
                    loss = criterion(logits, yb)

                optimizer.zero_grad(set_to_none=True)
                loss.backward()
                torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
                optimizer.step()
                scheduler.step()

                with torch.no_grad():
                    for p_ema, p in zip(model_ema.parameters(), model.parameters()):
                        p_ema.mul_(ema_decay).add_(p, alpha=(1.0 - ema_decay))

                global_step += 1

            if val_dl is not None:
                acc = _accuracy(model_ema, val_dl, device=device)
                if acc > best_acc + 1e-4:
                    best_acc = acc
                    best_state = {k: v.detach().cpu().clone() for k, v in model_ema.state_dict().items()}
                    no_improve = 0
                else:
                    no_improve += 1
                if no_improve >= patience:
                    break
            else:
                if epoch == max_epochs - 1:
                    best_state = {k: v.detach().cpu().clone() for k, v in model_ema.state_dict().items()}

        if best_state is not None:
            model_ema.load_state_dict(best_state, strict=True)

        if X_val is not None and y_val is not None and X_val.numel() > 0:
            X_comb = torch.cat([X_train, X_val], dim=0)
            y_comb = torch.cat([y_train, y_val], dim=0)
            comb_bs = min(256, int(X_comb.size(0)))
            comb_ds = TensorDataset(X_comb, y_comb)
            comb_dl = DataLoader(comb_ds, batch_size=comb_bs, shuffle=True, generator=gen, num_workers=0, drop_last=False)

            ft_lr = base_lr * 0.25
            ft_wd = weight_decay * 0.7
            optimizer_ft = _make_optimizer(model_ema, lr=ft_lr, weight_decay=ft_wd)
            ft_epochs = 25
            for _ in range(ft_epochs):
                model_ema.train()
                for xb, yb in comb_dl:
                    xb = xb.to(device, non_blocking=True)
                    yb = yb.to(device, non_blocking=True)
                    if noise_std > 0:
                        xb = xb + noise_std * torch.randn_like(xb)
                    logits = model_ema(xb)
                    loss = criterion(logits, yb)
                    optimizer_ft.zero_grad(set_to_none=True)
                    loss.backward()
                    torch.nn.utils.clip_grad_norm_(model_ema.parameters(), max_norm=1.0)
                    optimizer_ft.step()

        if _count_trainable_params(model_ema) > param_limit:
            model_ema = nn.Linear(input_dim, num_classes).to(device)

        model_ema.eval()
        return model_ema
