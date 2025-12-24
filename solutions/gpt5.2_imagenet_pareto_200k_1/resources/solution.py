import os
import math
import copy
import time
from typing import Dict, Optional, Tuple, List

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import TensorDataset, DataLoader


class _Standardize(nn.Module):
    def __init__(self, mean: torch.Tensor, std: torch.Tensor, eps: float = 1e-6):
        super().__init__()
        self.register_buffer("mean", mean.detach().clone())
        self.register_buffer("std", std.detach().clone())
        self.eps = float(eps)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        if x.dim() == 1:
            x = x.unsqueeze(0)
        return (x - self.mean) / (self.std + self.eps)


class _FeatureMLP(nn.Module):
    def __init__(self, input_dim: int, hidden_dim: int, dropout: float):
        super().__init__()
        self.fc1 = nn.Linear(input_dim, hidden_dim, bias=True)
        self.ln1 = nn.LayerNorm(hidden_dim)
        self.fc2 = nn.Linear(hidden_dim, hidden_dim, bias=True)
        self.ln2 = nn.LayerNorm(hidden_dim)
        self.drop = nn.Dropout(dropout)
        self.act = nn.GELU()

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self.fc1(x)
        x = self.ln1(x)
        x = self.act(x)
        x = self.drop(x)
        x = self.fc2(x)
        x = self.ln2(x)
        x = self.act(x)
        x = self.drop(x)
        return x


class _MLPClassifier(nn.Module):
    def __init__(self, input_dim: int, num_classes: int, hidden_dim: int, dropout: float,
                 mean: torch.Tensor, std: torch.Tensor):
        super().__init__()
        self.norm = _Standardize(mean, std)
        self.feat = _FeatureMLP(input_dim, hidden_dim, dropout)
        self.head = nn.Linear(hidden_dim, num_classes, bias=True)

    def embed(self, x: torch.Tensor) -> torch.Tensor:
        x = self.norm(x)
        return self.feat(x)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        z = self.embed(x)
        return self.head(z)


class _ProtoClassifier(nn.Module):
    def __init__(self, base: _MLPClassifier, prototypes: torch.Tensor, scale: float, use_cosine: bool = True):
        super().__init__()
        self.norm = base.norm
        self.feat = base.feat
        self.use_cosine = bool(use_cosine)
        if self.use_cosine:
            prototypes = F.normalize(prototypes, dim=1)
        self.register_buffer("prototypes", prototypes.detach().clone())
        self.register_buffer("scale", torch.tensor(float(scale), dtype=torch.float32))

    def embed(self, x: torch.Tensor) -> torch.Tensor:
        x = self.norm(x)
        return self.feat(x)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        z = self.embed(x)
        if self.use_cosine:
            z = F.normalize(z, dim=1)
        logits = (z @ self.prototypes.t()) * self.scale
        return logits


class _EMA:
    def __init__(self, model: nn.Module, decay: float = 0.995):
        self.decay = float(decay)
        self.shadow = {}
        for name, p in model.named_parameters():
            if p.requires_grad:
                self.shadow[name] = p.detach().clone()

    @torch.no_grad()
    def update(self, model: nn.Module):
        d = self.decay
        for name, p in model.named_parameters():
            if not p.requires_grad:
                continue
            if name not in self.shadow:
                self.shadow[name] = p.detach().clone()
            else:
                self.shadow[name].mul_(d).add_(p.detach(), alpha=(1.0 - d))

    @torch.no_grad()
    def copy_to(self, model: nn.Module):
        for name, p in model.named_parameters():
            if p.requires_grad and name in self.shadow:
                p.data.copy_(self.shadow[name])

    @torch.no_grad()
    def state_dict(self, model: nn.Module) -> Dict[str, torch.Tensor]:
        sd = model.state_dict()
        for name, p in model.named_parameters():
            if p.requires_grad and name in self.shadow:
                sd[name] = self.shadow[name].detach().clone()
        return sd


def _count_trainable_params(model: nn.Module) -> int:
    return int(sum(p.numel() for p in model.parameters() if p.requires_grad))


@torch.no_grad()
def _accuracy(model: nn.Module, loader: DataLoader, device: torch.device) -> float:
    model.eval()
    correct = 0
    total = 0
    for xb, yb in loader:
        xb = xb.to(device=device, dtype=torch.float32, non_blocking=True)
        yb = yb.to(device=device, dtype=torch.long, non_blocking=True)
        logits = model(xb)
        pred = logits.argmax(dim=1)
        correct += (pred == yb).sum().item()
        total += yb.numel()
    return float(correct) / float(max(1, total))


def _collect_loader(loader, device: torch.device) -> Tuple[torch.Tensor, torch.Tensor]:
    xs = []
    ys = []
    for xb, yb in loader:
        xs.append(xb.to(device=device, dtype=torch.float32, non_blocking=True).cpu())
        ys.append(yb.to(device=device, dtype=torch.long, non_blocking=True).cpu())
    x = torch.cat(xs, dim=0)
    y = torch.cat(ys, dim=0)
    return x, y


def _compute_mean_std(x: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
    mean = x.mean(dim=0)
    var = x.var(dim=0, unbiased=False)
    std = torch.sqrt(var + 1e-6)
    return mean, std


@torch.no_grad()
def _compute_prototypes(model: _MLPClassifier, loader: DataLoader, num_classes: int, device: torch.device) -> torch.Tensor:
    model.eval()
    sums = None
    counts = torch.zeros((num_classes,), dtype=torch.long)
    for xb, yb in loader:
        xb = xb.to(device=device, dtype=torch.float32, non_blocking=True)
        yb = yb.to(device=device, dtype=torch.long, non_blocking=True)
        z = model.embed(xb)
        z = z.detach().cpu()
        yb = yb.detach().cpu()
        if sums is None:
            sums = torch.zeros((num_classes, z.shape[1]), dtype=torch.float32)
        for c in range(num_classes):
            mask = (yb == c)
            if mask.any():
                sums[c] += z[mask].sum(dim=0)
                counts[c] += int(mask.sum().item())
    counts = counts.clamp_min(1).to(dtype=torch.float32).unsqueeze(1)
    protos = sums / counts
    return protos


def _make_tensor_loader(x: torch.Tensor, y: torch.Tensor, batch_size: int, shuffle: bool) -> DataLoader:
    ds = TensorDataset(x, y)
    return DataLoader(ds, batch_size=batch_size, shuffle=shuffle, num_workers=0, pin_memory=False, drop_last=False)


class Solution:
    def solve(self, train_loader, val_loader, metadata: dict = None) -> torch.nn.Module:
        if metadata is None:
            metadata = {}
        input_dim = int(metadata.get("input_dim", 384))
        num_classes = int(metadata.get("num_classes", 128))
        param_limit = int(metadata.get("param_limit", 200000))
        device_str = str(metadata.get("device", "cpu"))
        device = torch.device(device_str)

        try:
            cpu_threads = os.cpu_count() or 8
            torch.set_num_threads(max(1, min(8, int(cpu_threads))))
        except Exception:
            pass

        x_train_cpu, y_train_cpu = _collect_loader(train_loader, device=torch.device("cpu"))
        x_val_cpu, y_val_cpu = _collect_loader(val_loader, device=torch.device("cpu"))

        mean, std = _compute_mean_std(x_train_cpu)
        mean = mean.to(dtype=torch.float32)
        std = std.to(dtype=torch.float32)

        hidden_dim = 256
        dropout = 0.10

        model = _MLPClassifier(input_dim, num_classes, hidden_dim, dropout, mean, std).to(device)
        if _count_trainable_params(model) > param_limit:
            for h in [248, 240, 232, 224, 216, 208, 200, 192, 184]:
                candidate = _MLPClassifier(input_dim, num_classes, h, dropout, mean, std).to(device)
                if _count_trainable_params(candidate) <= param_limit:
                    model = candidate
                    hidden_dim = h
                    break

        if _count_trainable_params(model) > param_limit:
            for p in model.parameters():
                p.requires_grad_(False)
            model.eval()
            return model

        batch_size = 128
        train_dl = _make_tensor_loader(x_train_cpu, y_train_cpu, batch_size=batch_size, shuffle=True)
        val_dl = _make_tensor_loader(x_val_cpu, y_val_cpu, batch_size=256, shuffle=False)

        max_epochs = 220
        base_lr = 5e-3
        min_lr = 3e-5
        warmup_epochs = 8
        weight_decay = 2e-2
        label_smoothing = 0.10
        mixup_alpha = 0.20
        grad_clip = 1.0
        noise_std = 0.02

        optimizer = torch.optim.AdamW(model.parameters(), lr=base_lr, weight_decay=weight_decay, betas=(0.9, 0.999))
        total_steps = max(1, max_epochs * max(1, len(train_dl)))
        warmup_steps = max(1, warmup_epochs * max(1, len(train_dl)))

        def lr_at_step(step: int) -> float:
            if step < warmup_steps:
                return base_lr * float(step + 1) / float(warmup_steps)
            t = float(step - warmup_steps) / float(max(1, total_steps - warmup_steps))
            c = 0.5 * (1.0 + math.cos(math.pi * min(1.0, max(0.0, t))))
            return min_lr + (base_lr - min_lr) * c

        ema = _EMA(model, decay=0.995)

        best_val = -1.0
        best_state = None
        patience = 30
        bad = 0
        global_step = 0

        rng = np.random.default_rng(12345)

        for epoch in range(max_epochs):
            model.train()
            for xb, yb in train_dl:
                xb = xb.to(device=device, dtype=torch.float32, non_blocking=True)
                yb = yb.to(device=device, dtype=torch.long, non_blocking=True)

                if noise_std > 0.0:
                    xb = xb + (noise_std * torch.randn_like(xb))

                if mixup_alpha > 0.0:
                    lam = float(rng.beta(mixup_alpha, mixup_alpha))
                    perm = torch.randperm(xb.size(0), device=xb.device)
                    xb_mix = xb.mul(lam).add_(xb[perm], alpha=(1.0 - lam))
                    y_a = yb
                    y_b = yb[perm]
                    logits = model(xb_mix)
                    loss = lam * F.cross_entropy(logits, y_a, label_smoothing=label_smoothing) + (1.0 - lam) * F.cross_entropy(
                        logits, y_b, label_smoothing=label_smoothing
                    )
                else:
                    logits = model(xb)
                    loss = F.cross_entropy(logits, yb, label_smoothing=label_smoothing)

                optimizer.zero_grad(set_to_none=True)
                loss.backward()
                if grad_clip is not None and grad_clip > 0:
                    nn.utils.clip_grad_norm_(model.parameters(), grad_clip)
                lr = lr_at_step(global_step)
                for pg in optimizer.param_groups:
                    pg["lr"] = lr
                optimizer.step()
                ema.update(model)
                global_step += 1

            if (epoch + 1) % 2 == 0 or epoch == max_epochs - 1:
                prev = {k: v.detach().clone() for k, v in model.state_dict().items()}
                ema.copy_to(model)
                val_acc = _accuracy(model, val_dl, device=device)
                model.load_state_dict(prev, strict=True)

                if val_acc > best_val + 1e-6:
                    best_val = val_acc
                    best_state = ema.state_dict(model)
                    bad = 0
                else:
                    bad += 1
                    if bad >= patience:
                        break

        if best_state is not None:
            model.load_state_dict(best_state, strict=True)

        base_val = _accuracy(model, val_dl, device=device)

        protos = _compute_prototypes(model, train_dl, num_classes=num_classes, device=device)
        scale_candidates = [4.0, 6.0, 8.0, 10.0, 12.0, 15.0, 20.0, 30.0]
        best_proto_acc = -1.0
        best_scale = 10.0

        for sc in scale_candidates:
            pm = _ProtoClassifier(model, protos.to(device=device), scale=sc, use_cosine=True).to(device)
            acc = _accuracy(pm, val_dl, device=device)
            if acc > best_proto_acc + 1e-9:
                best_proto_acc = acc
                best_scale = sc

        if best_proto_acc > base_val + 1e-6:
            final_model = _ProtoClassifier(model, protos.to(device=device), scale=best_scale, use_cosine=True).to(device)
        else:
            final_model = model

        final_model.eval()
        return final_model
