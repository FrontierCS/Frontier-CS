import math
import os
import random
from copy import deepcopy
from typing import Dict, Optional, Tuple

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import DataLoader, TensorDataset


def _set_seed(seed: int = 42) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)


def _count_trainable_params(model: nn.Module) -> int:
    return sum(p.numel() for p in model.parameters() if p.requires_grad)


@torch.no_grad()
def _loader_to_tensors(loader: DataLoader) -> Tuple[torch.Tensor, torch.Tensor]:
    xs = []
    ys = []
    for x, y in loader:
        if not torch.is_tensor(x):
            x = torch.as_tensor(x)
        if not torch.is_tensor(y):
            y = torch.as_tensor(y)
        xs.append(x.detach().cpu())
        ys.append(y.detach().cpu())
    X = torch.cat(xs, dim=0).contiguous().to(dtype=torch.float32)
    Y = torch.cat(ys, dim=0).contiguous().to(dtype=torch.long)
    return X, Y


def _infer_input_dim_num_classes(train_loader: DataLoader) -> Tuple[int, int]:
    x0, y0 = next(iter(train_loader))
    if not torch.is_tensor(x0):
        x0 = torch.as_tensor(x0)
    if not torch.is_tensor(y0):
        y0 = torch.as_tensor(y0)
    input_dim = int(x0.shape[-1])
    num_classes = int(torch.max(y0).item() + 1)
    return input_dim, num_classes


def _compute_mean_std(X: torch.Tensor, eps: float = 1e-6) -> Tuple[torch.Tensor, torch.Tensor]:
    mean = X.mean(dim=0)
    var = X.var(dim=0, unbiased=False)
    std = torch.sqrt(var + eps)
    return mean, std


class InputNorm(nn.Module):
    def __init__(self, mean: torch.Tensor, std: torch.Tensor):
        super().__init__()
        self.register_buffer("mean", mean.clone().detach())
        self.register_buffer("std", std.clone().detach())

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return (x - self.mean) / self.std


class ResidualBlock(nn.Module):
    def __init__(self, dim: int, dropout: float = 0.1):
        super().__init__()
        self.bn = nn.BatchNorm1d(dim, eps=1e-5, momentum=0.05, affine=True)
        self.act = nn.SiLU()
        self.fc = nn.Linear(dim, dim, bias=False)
        self.drop = nn.Dropout(p=dropout)
        self.scale = nn.Parameter(torch.tensor(1e-3, dtype=torch.float32))

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        y = self.fc(self.act(self.bn(x)))
        y = self.drop(y)
        return x + self.scale * y


class MLPResNet(nn.Module):
    def __init__(
        self,
        input_dim: int,
        num_classes: int,
        mean: torch.Tensor,
        std: torch.Tensor,
        hidden_dim: int = 330,
        num_blocks: int = 3,
        dropout: float = 0.1,
    ):
        super().__init__()
        self.norm = InputNorm(mean, std)
        self.fc0 = nn.Linear(input_dim, hidden_dim, bias=False)
        self.bn0 = nn.BatchNorm1d(hidden_dim, eps=1e-5, momentum=0.05, affine=True)
        self.act0 = nn.SiLU()
        self.drop0 = nn.Dropout(p=dropout)

        self.blocks = nn.ModuleList([ResidualBlock(hidden_dim, dropout=dropout) for _ in range(num_blocks)])

        self.bn_head = nn.BatchNorm1d(hidden_dim, eps=1e-5, momentum=0.05, affine=True)
        self.act_head = nn.SiLU()
        self.fc_out = nn.Linear(hidden_dim, num_classes, bias=True)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = x.to(dtype=torch.float32)
        x = self.norm(x)
        x = self.drop0(self.act0(self.bn0(self.fc0(x))))
        for blk in self.blocks:
            x = blk(x)
        x = self.act_head(self.bn_head(x))
        return self.fc_out(x)


class EMA:
    def __init__(self, model: nn.Module, decay: float = 0.995):
        self.decay = float(decay)
        self.shadow = {}
        for n, p in model.named_parameters():
            if p.requires_grad:
                self.shadow[n] = p.detach().clone()

    @torch.no_grad()
    def update(self, model: nn.Module):
        d = self.decay
        for n, p in model.named_parameters():
            if not p.requires_grad:
                continue
            self.shadow[n].mul_(d).add_(p.detach(), alpha=(1.0 - d))

    @torch.no_grad()
    def copy_to(self, model: nn.Module):
        for n, p in model.named_parameters():
            if p.requires_grad:
                p.copy_(self.shadow[n])

    @torch.no_grad()
    def store(self, model: nn.Module):
        self._backup = {}
        for n, p in model.named_parameters():
            if p.requires_grad:
                self._backup[n] = p.detach().clone()

    @torch.no_grad()
    def restore(self, model: nn.Module):
        for n, p in model.named_parameters():
            if p.requires_grad:
                p.copy_(self._backup[n])
        self._backup = None


@torch.no_grad()
def _accuracy(model: nn.Module, loader: DataLoader, device: torch.device) -> float:
    model.eval()
    correct = 0
    total = 0
    for x, y in loader:
        x = x.to(device=device, dtype=torch.float32, non_blocking=False)
        y = y.to(device=device, dtype=torch.long, non_blocking=False)
        logits = model(x)
        pred = logits.argmax(dim=1)
        correct += (pred == y).sum().item()
        total += y.numel()
    return float(correct) / float(total) if total > 0 else 0.0


class Solution:
    def solve(self, train_loader, val_loader, metadata: dict = None) -> torch.nn.Module:
        _set_seed(42)
        try:
            torch.set_num_threads(min(8, os.cpu_count() or 8))
        except Exception:
            pass

        if metadata is None:
            metadata = {}

        if "input_dim" in metadata and "num_classes" in metadata:
            input_dim = int(metadata["input_dim"])
            num_classes = int(metadata["num_classes"])
        else:
            input_dim, num_classes = _infer_input_dim_num_classes(train_loader)

        param_limit = int(metadata.get("param_limit", 500_000))
        device_str = str(metadata.get("device", "cpu"))
        device = torch.device(device_str)

        Xtr, Ytr = _loader_to_tensors(train_loader)
        Xva, Yva = _loader_to_tensors(val_loader)

        mean, std = _compute_mean_std(Xtr)

        hidden_dim = 330
        num_blocks = 3
        dropout = 0.12
        model = MLPResNet(
            input_dim=input_dim,
            num_classes=num_classes,
            mean=mean,
            std=std,
            hidden_dim=hidden_dim,
            num_blocks=num_blocks,
            dropout=dropout,
        ).to(device)

        if _count_trainable_params(model) > param_limit:
            # Fallback: slightly smaller
            model = MLPResNet(
                input_dim=input_dim,
                num_classes=num_classes,
                mean=mean,
                std=std,
                hidden_dim=320,
                num_blocks=3,
                dropout=dropout,
            ).to(device)

        if _count_trainable_params(model) > param_limit:
            model = MLPResNet(
                input_dim=input_dim,
                num_classes=num_classes,
                mean=mean,
                std=std,
                hidden_dim=300,
                num_blocks=3,
                dropout=dropout,
            ).to(device)

        if _count_trainable_params(model) > param_limit:
            model = MLPResNet(
                input_dim=input_dim,
                num_classes=num_classes,
                mean=mean,
                std=std,
                hidden_dim=280,
                num_blocks=2,
                dropout=dropout,
            ).to(device)

        # Cached loaders
        bs = getattr(train_loader, "batch_size", None)
        if bs is None or bs <= 0:
            bs = 64
        bs = int(bs)

        train_ds = TensorDataset(Xtr, Ytr)
        val_ds = TensorDataset(Xva, Yva)
        train_cached = DataLoader(train_ds, batch_size=bs, shuffle=True, num_workers=0, drop_last=False)
        val_cached = DataLoader(val_ds, batch_size=256, shuffle=False, num_workers=0, drop_last=False)

        # Stage 1 training with early stopping on val
        epochs = 140
        mixup_epochs = int(epochs * 0.75)
        label_smoothing = 0.06
        mixup_alpha = 0.20
        noise_std = 0.010

        criterion = nn.CrossEntropyLoss(label_smoothing=label_smoothing)
        optimizer = torch.optim.AdamW(model.parameters(), lr=2.6e-3, weight_decay=1.0e-2, betas=(0.9, 0.99))
        steps_per_epoch = len(train_cached)
        total_steps = max(1, epochs * steps_per_epoch)
        scheduler = torch.optim.lr_scheduler.OneCycleLR(
            optimizer,
            max_lr=2.6e-3,
            total_steps=total_steps,
            pct_start=0.12,
            anneal_strategy="cos",
            div_factor=20.0,
            final_div_factor=200.0,
        )

        ema = EMA(model, decay=0.995)

        best_acc = -1.0
        best_state = None
        patience = 28
        bad = 0

        global_step = 0
        for epoch in range(epochs):
            model.train()
            for xb, yb in train_cached:
                xb = xb.to(device=device, dtype=torch.float32, non_blocking=False)
                yb = yb.to(device=device, dtype=torch.long, non_blocking=False)

                if epoch < mixup_epochs:
                    if noise_std > 0:
                        xb = xb + noise_std * torch.randn_like(xb)
                    if mixup_alpha > 0:
                        lam = np.random.beta(mixup_alpha, mixup_alpha)
                        if lam < 0.5:
                            lam = 1.0 - lam
                        perm = torch.randperm(xb.size(0), device=device)
                        xb2 = xb[perm]
                        yb2 = yb[perm]
                        xb = lam * xb + (1.0 - lam) * xb2

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

                global_step += 1
                if global_step > 50:
                    ema.update(model)
                else:
                    ema.update(model)

            ema.store(model)
            ema.copy_to(model)
            va = _accuracy(model, val_cached, device)
            ema.restore(model)

            if va > best_acc + 1e-4:
                best_acc = va
                best_state = deepcopy(ema.shadow)
                bad = 0
            else:
                bad += 1
                if bad >= patience:
                    break

        if best_state is not None:
            for n, p in model.named_parameters():
                if p.requires_grad and n in best_state:
                    p.data.copy_(best_state[n])

        # Stage 2: short fine-tune on train+val (no mixup)
        Xall = torch.cat([Xtr, Xva], dim=0)
        Yall = torch.cat([Ytr, Yva], dim=0)
        all_ds = TensorDataset(Xall, Yall)
        all_loader = DataLoader(all_ds, batch_size=bs, shuffle=True, num_workers=0, drop_last=False)

        ft_epochs = 25
        ft_criterion = nn.CrossEntropyLoss(label_smoothing=0.02)
        ft_optimizer = torch.optim.AdamW(model.parameters(), lr=6.0e-4, weight_decay=6.0e-3, betas=(0.9, 0.99))
        ft_scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(ft_optimizer, T_max=max(1, ft_epochs))

        for _ in range(ft_epochs):
            model.train()
            for xb, yb in all_loader:
                xb = xb.to(device=device, dtype=torch.float32, non_blocking=False)
                yb = yb.to(device=device, dtype=torch.long, non_blocking=False)

                logits = model(xb)
                loss = ft_criterion(logits, yb)

                ft_optimizer.zero_grad(set_to_none=True)
                loss.backward()
                torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
                ft_optimizer.step()
            ft_scheduler.step()

        model.eval()
        return model