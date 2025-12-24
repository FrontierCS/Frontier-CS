import os
import math
import copy
import random
from typing import Dict, Tuple, Optional, List

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F


class _Standardize(nn.Module):
    def __init__(self, input_dim: int, eps: float = 1e-6):
        super().__init__()
        self.eps = eps
        self.register_buffer("mean", torch.zeros(input_dim, dtype=torch.float32))
        self.register_buffer("invstd", torch.ones(input_dim, dtype=torch.float32))

    def set_stats(self, mean: torch.Tensor, std: torch.Tensor):
        mean = mean.detach().to(dtype=torch.float32)
        std = std.detach().to(dtype=torch.float32)
        invstd = 1.0 / torch.clamp(std, min=self.eps)
        self.mean.copy_(mean)
        self.invstd.copy_(invstd)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return (x - self.mean) * self.invstd


class _ResidualMLPBlock(nn.Module):
    def __init__(self, dim: int, hidden: int, dropout: float = 0.05):
        super().__init__()
        self.ln = nn.LayerNorm(dim)
        self.fc1 = nn.Linear(dim, hidden)
        self.fc2 = nn.Linear(hidden, dim)
        self.drop = nn.Dropout(dropout)
        self.act = nn.GELU(approximate="tanh")

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        h = self.ln(x)
        h = self.fc1(h)
        h = self.act(h)
        h = self.fc2(h)
        h = self.drop(h)
        return x + h


class _MLPNet(nn.Module):
    def __init__(self, input_dim: int, num_classes: int, dim: int, hidden: int, blocks: int, dropout: float = 0.05):
        super().__init__()
        self.standardize = _Standardize(input_dim)
        self.stem = nn.Sequential(
            nn.Linear(input_dim, dim),
            nn.GELU(approximate="tanh"),
        )
        self.blocks = nn.Sequential(*[_ResidualMLPBlock(dim, hidden, dropout=dropout) for _ in range(blocks)])
        self.final_ln = nn.LayerNorm(dim)
        self.head = nn.Linear(dim, num_classes)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        if not torch.is_tensor(x):
            x = torch.as_tensor(x)
        x = x.to(dtype=torch.float32)
        if x.dim() > 2:
            x = x.view(x.size(0), -1)
        x = self.standardize(x)
        x = self.stem(x)
        x = self.blocks(x)
        x = self.final_ln(x)
        return self.head(x)


def _count_trainable_params(model: nn.Module) -> int:
    return sum(p.numel() for p in model.parameters() if p.requires_grad)


def _loader_to_tensors(loader, device: torch.device) -> Tuple[torch.Tensor, torch.Tensor]:
    xs = []
    ys = []
    for batch in loader:
        if isinstance(batch, (tuple, list)) and len(batch) >= 2:
            x, y = batch[0], batch[1]
        else:
            raise ValueError("DataLoader must yield (inputs, targets)")
        x = torch.as_tensor(x)
        y = torch.as_tensor(y)
        if x.dim() > 2:
            x = x.view(x.size(0), -1)
        xs.append(x.to(device=device, dtype=torch.float32))
        ys.append(y.to(device=device, dtype=torch.long))
    x_all = torch.cat(xs, dim=0) if len(xs) else torch.empty((0,), device=device)
    y_all = torch.cat(ys, dim=0) if len(ys) else torch.empty((0,), device=device, dtype=torch.long)
    return x_all, y_all


@torch.inference_mode()
def _accuracy(model: nn.Module, x: torch.Tensor, y: torch.Tensor, batch_size: int = 1024) -> float:
    model.eval()
    n = int(y.numel())
    if n == 0:
        return 0.0
    correct = 0
    for i in range(0, n, batch_size):
        xb = x[i:i + batch_size]
        yb = y[i:i + batch_size]
        logits = model(xb)
        pred = logits.argmax(dim=1)
        correct += int((pred == yb).sum().item())
    return correct / n


def _make_param_groups(model: nn.Module, weight_decay: float) -> List[Dict]:
    decay = []
    no_decay = []
    for name, p in model.named_parameters():
        if not p.requires_grad:
            continue
        if p.ndim == 1 or name.endswith(".bias") or ".ln." in name or "layernorm" in name.lower() or "final_ln" in name.lower():
            no_decay.append(p)
        else:
            decay.append(p)
    groups = []
    if decay:
        groups.append({"params": decay, "weight_decay": weight_decay})
    if no_decay:
        groups.append({"params": no_decay, "weight_decay": 0.0})
    return groups


class Solution:
    def solve(self, train_loader, val_loader, metadata: dict = None) -> torch.nn.Module:
        if metadata is None:
            metadata = {}
        input_dim = int(metadata.get("input_dim", 384))
        num_classes = int(metadata.get("num_classes", 128))
        param_limit = int(metadata.get("param_limit", 1_000_000))
        device_str = str(metadata.get("device", "cpu"))
        device = torch.device(device_str)

        try:
            torch.set_num_interop_threads(1)
        except Exception:
            pass
        try:
            torch.set_num_threads(min(8, os.cpu_count() or 1))
        except Exception:
            pass

        seed = 0
        random.seed(seed)
        np.random.seed(seed)
        torch.manual_seed(seed)

        x_train, y_train = _loader_to_tensors(train_loader, device)
        x_val, y_val = _loader_to_tensors(val_loader, device)

        if x_train.dim() != 2 or x_train.size(1) != input_dim:
            x_train = x_train.view(x_train.size(0), -1)
        if x_val.numel() and (x_val.dim() != 2 or x_val.size(1) != input_dim):
            x_val = x_val.view(x_val.size(0), -1)

        train_mean = x_train.mean(dim=0)
        train_std = x_train.std(dim=0, unbiased=False)

        candidates = [
            (576, 144, 4, 0.05),
            (640, 160, 3, 0.05),
            (560, 140, 4, 0.05),
            (512, 128, 5, 0.05),
            (512, 128, 4, 0.05),
            (448, 112, 5, 0.05),
            (384, 96, 6, 0.05),
            (384, 96, 4, 0.05),
        ]

        model = None
        for dim, hidden, blocks, dropout in candidates:
            m = _MLPNet(input_dim, num_classes, dim=dim, hidden=hidden, blocks=blocks, dropout=dropout).to(device)
            m.standardize.set_stats(train_mean, train_std)
            if _count_trainable_params(m) <= param_limit:
                model = m
                break
        if model is None:
            model = _MLPNet(input_dim, num_classes, dim=256, hidden=64, blocks=3, dropout=0.05).to(device)
            model.standardize.set_stats(train_mean, train_std)

        if _count_trainable_params(model) > param_limit:
            for p in model.parameters():
                p.requires_grad_(False)
            model.eval()
            return model

        batch_size = 256
        n_train = int(y_train.numel())
        steps_per_epoch = max(1, (n_train + batch_size - 1) // batch_size)

        max_epochs = 220
        min_epochs = 30
        eval_every = 1

        weight_decay = 2e-4
        base_lr = 2.8e-3
        label_smoothing = 0.06
        grad_clip = 1.0

        param_groups = _make_param_groups(model, weight_decay=weight_decay)
        optimizer = torch.optim.AdamW(param_groups, lr=base_lr, betas=(0.9, 0.95), eps=1e-8)

        total_steps = max_epochs * steps_per_epoch
        warmup_steps = max(20, int(0.08 * total_steps))

        def lr_for_step(t: int) -> float:
            if t < warmup_steps:
                return base_lr * (t + 1) / warmup_steps
            tt = (t - warmup_steps) / max(1, (total_steps - warmup_steps))
            return base_lr * (0.5 * (1.0 + math.cos(math.pi * tt)))

        global_step = 0

        use_ema = True
        ema_decay = 0.9985
        ema_state = None
        if use_ema:
            ema_state = {k: v.detach().clone() for k, v in model.state_dict().items()}

        def ema_update():
            if ema_state is None:
                return
            msd = model.state_dict()
            for k, v in msd.items():
                ev = ema_state[k]
                if ev.dtype.is_floating_point:
                    ev.mul_(ema_decay).add_(v.detach(), alpha=(1.0 - ema_decay))
                else:
                    ev.copy_(v)

        best_val_acc = -1.0
        best_state = None
        best_epoch = -1
        patience = 35
        bad = 0

        for epoch in range(max_epochs):
            model.train()
            perm = torch.randperm(n_train, device=device)
            for i in range(0, n_train, batch_size):
                idx = perm[i:i + batch_size]
                xb = x_train.index_select(0, idx)
                yb = y_train.index_select(0, idx)

                lr = lr_for_step(global_step)
                for pg in optimizer.param_groups:
                    pg["lr"] = lr

                optimizer.zero_grad(set_to_none=True)
                logits = model(xb)
                loss = F.cross_entropy(logits, yb, label_smoothing=label_smoothing)
                loss.backward()
                if grad_clip is not None and grad_clip > 0:
                    torch.nn.utils.clip_grad_norm_(model.parameters(), grad_clip)
                optimizer.step()
                if use_ema:
                    with torch.no_grad():
                        ema_update()
                global_step += 1

            if (epoch + 1) % eval_every == 0:
                val_acc = _accuracy(model, x_val, y_val) if y_val.numel() else _accuracy(model, x_train, y_train)
                if val_acc > best_val_acc + 1e-6:
                    best_val_acc = val_acc
                    best_state = {k: v.detach().clone() for k, v in model.state_dict().items()}
                    best_epoch = epoch
                    bad = 0
                else:
                    bad += 1

                if epoch + 1 >= min_epochs and bad >= patience:
                    break

        if best_state is not None:
            model.load_state_dict(best_state)

        if use_ema and ema_state is not None and y_val.numel():
            cur_acc = _accuracy(model, x_val, y_val)
            cur_state = {k: v.detach().clone() for k, v in model.state_dict().items()}
            model.load_state_dict(ema_state)
            ema_acc = _accuracy(model, x_val, y_val)
            if ema_acc + 1e-6 < cur_acc:
                model.load_state_dict(cur_state)

        model.eval()

        if _count_trainable_params(model) > param_limit:
            for p in model.parameters():
                p.requires_grad_(False)
            model.eval()

        return model
