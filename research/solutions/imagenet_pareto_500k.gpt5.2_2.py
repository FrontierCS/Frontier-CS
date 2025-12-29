import os
import math
import time
import copy
from typing import Optional, Tuple

import torch
import torch.nn as nn


def _count_trainable_params(model: nn.Module) -> int:
    return sum(p.numel() for p in model.parameters() if p.requires_grad)


def _loader_to_tensors(loader, device: torch.device) -> Tuple[torch.Tensor, torch.Tensor]:
    xs = []
    ys = []
    for x, y in loader:
        if not torch.is_tensor(x):
            x = torch.tensor(x)
        if not torch.is_tensor(y):
            y = torch.tensor(y)
        xs.append(x)
        ys.append(y)
    X = torch.cat(xs, dim=0).to(device=device)
    Y = torch.cat(ys, dim=0).to(device=device)
    if X.dtype != torch.float32:
        X = X.float()
    if Y.dtype != torch.long:
        Y = Y.long()
    return X, Y


class _Standardize(nn.Module):
    def __init__(self, mean: torch.Tensor, std: torch.Tensor, eps: float = 1e-6):
        super().__init__()
        self.register_buffer("mean", mean.detach().clone())
        self.register_buffer("std", std.detach().clone())
        self.eps = eps

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        if x.dtype != torch.float32:
            x = x.float()
        return (x - self.mean) / (self.std + self.eps)


class _ResidualBottleneckBlock(nn.Module):
    def __init__(self, d: int, b: int, dropout: float):
        super().__init__()
        self.norm = nn.LayerNorm(d)
        self.fc1 = nn.Linear(d, b, bias=True)
        self.fc2 = nn.Linear(b, d, bias=True)
        self.drop1 = nn.Dropout(dropout)
        self.drop2 = nn.Dropout(dropout)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        y = self.norm(x)
        y = self.fc1(y)
        y = torch.nn.functional.gelu(y)
        y = self.drop1(y)
        y = self.fc2(y)
        y = self.drop2(y)
        return x + y


class _BottleneckResidualMLP(nn.Module):
    def __init__(
        self,
        input_dim: int,
        num_classes: int,
        depth: int,
        bottleneck: int,
        dropout: float,
        mean: torch.Tensor,
        std: torch.Tensor,
    ):
        super().__init__()
        self.input_dim = input_dim
        self.num_classes = num_classes
        self.std_layer = _Standardize(mean=mean, std=std)
        d = input_dim
        self.blocks = nn.ModuleList([_ResidualBottleneckBlock(d=d, b=bottleneck, dropout=dropout) for _ in range(depth)])
        self.norm = nn.LayerNorm(d)
        self.head = nn.Linear(d, num_classes, bias=True)
        self._init_weights()

    def _init_weights(self):
        for m in self.modules():
            if isinstance(m, nn.Linear):
                nn.init.trunc_normal_(m.weight, std=0.02)
                if m.bias is not None:
                    nn.init.zeros_(m.bias)
            elif isinstance(m, nn.LayerNorm):
                nn.init.ones_(m.weight)
                nn.init.zeros_(m.bias)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self.std_layer(x)
        for blk in self.blocks:
            x = blk(x)
        x = self.norm(x)
        return self.head(x)


def _estimate_params(input_dim: int, num_classes: int, depth: int, bottleneck: int) -> int:
    d = input_dim
    b = bottleneck
    per_block = (2 * d * b) + b + (3 * d)  # fc1+fc2 + biases + LayerNorm
    total = depth * per_block + (2 * d) + (d * num_classes + num_classes)  # final norm + head
    return total


@torch.inference_mode()
def _accuracy(model: nn.Module, X: torch.Tensor, y: torch.Tensor, batch_size: int = 512) -> float:
    model.eval()
    n = X.shape[0]
    correct = 0
    for i in range(0, n, batch_size):
        xb = X[i : i + batch_size]
        yb = y[i : i + batch_size]
        logits = model(xb)
        pred = logits.argmax(dim=1)
        correct += (pred == yb).sum().item()
    return correct / max(1, n)


class Solution:
    def solve(self, train_loader, val_loader, metadata: dict = None) -> torch.nn.Module:
        if metadata is None:
            metadata = {}
        input_dim = int(metadata.get("input_dim", 384))
        num_classes = int(metadata.get("num_classes", 128))
        param_limit = int(metadata.get("param_limit", 500_000))
        device_str = metadata.get("device", "cpu")
        device = torch.device(device_str)

        torch.set_num_threads(min(8, os.cpu_count() or 1))

        X_train, y_train = _loader_to_tensors(train_loader, device=device)
        X_val, y_val = _loader_to_tensors(val_loader, device=device)

        mean = X_train.mean(dim=0)
        std = X_train.std(dim=0, unbiased=False).clamp_min(1e-3)

        # Choose architecture to maximize parameter usage under limit (bounded depth for speed/stability)
        best = None
        for depth in range(2, 13):
            for b in range(32, min(input_dim, 512) + 1, 16):
                est = _estimate_params(input_dim, num_classes, depth, b)
                if est <= param_limit:
                    if best is None or est > best[0]:
                        best = (est, depth, b)
        if best is None:
            # Fallback: linear
            model = nn.Sequential(_Standardize(mean, std), nn.Linear(input_dim, num_classes)).to(device)
            if _count_trainable_params(model) > param_limit:
                # Extremely unlikely given provided limits, but keep hard-safe
                model = nn.Sequential(_Standardize(mean, std), nn.Linear(input_dim, max(1, num_classes // 2)), nn.ReLU(), nn.Linear(max(1, num_classes // 2), num_classes)).to(device)
            return model

        _, depth, bottleneck = best

        dropout = 0.10 if _estimate_params(input_dim, num_classes, depth, bottleneck) > 350_000 else 0.05
        model = _BottleneckResidualMLP(
            input_dim=input_dim,
            num_classes=num_classes,
            depth=depth,
            bottleneck=bottleneck,
            dropout=dropout,
            mean=mean,
            std=std,
        ).to(device)

        # Hard check
        if _count_trainable_params(model) > param_limit:
            # Reduce bottleneck until within limit
            b = bottleneck
            while b >= 16 and _count_trainable_params(model) > param_limit:
                b -= 16
                model = _BottleneckResidualMLP(
                    input_dim=input_dim,
                    num_classes=num_classes,
                    depth=depth,
                    bottleneck=max(16, b),
                    dropout=dropout,
                    mean=mean,
                    std=std,
                ).to(device)

        ema_model = copy.deepcopy(model).to(device)
        for p in ema_model.parameters():
            p.requires_grad_(False)

        n_train = int(X_train.shape[0])
        batch_size = min(256, n_train)
        steps_per_epoch = max(1, (n_train + batch_size - 1) // batch_size)

        max_epochs = 220
        warmup_epochs = 10
        warmup_steps = warmup_epochs * steps_per_epoch
        total_steps = max_epochs * steps_per_epoch

        base_lr = 2.0e-3
        min_lr = 1.0e-4
        weight_decay = 0.04
        ema_decay = 0.992

        optimizer = torch.optim.AdamW(model.parameters(), lr=base_lr, betas=(0.9, 0.95), weight_decay=weight_decay)
        criterion = nn.CrossEntropyLoss(label_smoothing=0.06)

        best_state = None
        best_acc = -1.0
        patience = 45
        bad_epochs = 0

        start_time = time.time()
        time_budget_s = 3300.0  # safety
        global_step = 0

        model.train()
        for epoch in range(max_epochs):
            if time.time() - start_time > time_budget_s:
                break

            model.train()
            perm = torch.randperm(n_train, device=device)
            for s in range(0, n_train, batch_size):
                idx = perm[s : s + batch_size]
                xb = X_train.index_select(0, idx)
                yb = y_train.index_select(0, idx)

                # Manual cosine schedule with warmup
                if global_step < warmup_steps:
                    lr_scale = (global_step + 1) / max(1, warmup_steps)
                else:
                    t = (global_step - warmup_steps) / max(1, (total_steps - warmup_steps))
                    lr_scale = 0.5 * (1.0 + math.cos(math.pi * min(1.0, t)))
                lr = min_lr + (base_lr - min_lr) * lr_scale
                for pg in optimizer.param_groups:
                    pg["lr"] = lr

                optimizer.zero_grad(set_to_none=True)
                logits = model(xb)
                loss = criterion(logits, yb)
                loss.backward()
                torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
                optimizer.step()

                with torch.no_grad():
                    for p_ema, p in zip(ema_model.parameters(), model.parameters()):
                        p_ema.mul_(ema_decay).add_(p, alpha=(1.0 - ema_decay))
                    for b_ema, b_m in zip(ema_model.buffers(), model.buffers()):
                        b_ema.copy_(b_m)

                global_step += 1

            val_acc = _accuracy(ema_model, X_val, y_val, batch_size=512)
            if val_acc > best_acc + 1e-4:
                best_acc = val_acc
                best_state = copy.deepcopy(ema_model.state_dict())
                bad_epochs = 0
            else:
                bad_epochs += 1
                if bad_epochs >= patience:
                    break

        if best_state is not None:
            model.load_state_dict(best_state, strict=True)
        model.eval()
        return model