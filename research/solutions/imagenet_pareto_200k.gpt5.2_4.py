import math
import os
from copy import deepcopy
from typing import Dict, Iterable, Tuple, Optional

import torch
import torch.nn as nn
import torch.nn.functional as F


def _count_trainable_params(model: nn.Module) -> int:
    return sum(p.numel() for p in model.parameters() if p.requires_grad)


def _iter_batches(loader: Iterable):
    for batch in loader:
        if isinstance(batch, (list, tuple)) and len(batch) >= 2:
            x, y = batch[0], batch[1]
        elif isinstance(batch, dict):
            x, y = batch.get("inputs", None), batch.get("targets", None)
            if x is None or y is None:
                keys = list(batch.keys())
                x, y = batch[keys[0]], batch[keys[1]]
        else:
            raise TypeError("Unsupported batch format")
        yield x, y


@torch.no_grad()
def _compute_mean_std(train_loader, input_dim: int, device: torch.device) -> Tuple[torch.Tensor, torch.Tensor]:
    s1 = torch.zeros(input_dim, dtype=torch.float64, device=device)
    s2 = torch.zeros(input_dim, dtype=torch.float64, device=device)
    n = 0
    for x, _ in _iter_batches(train_loader):
        x = x.to(device=device)
        if x.dtype != torch.float32 and x.dtype != torch.float64:
            x = x.float()
        if x.dim() == 1:
            x = x.unsqueeze(0)
        x64 = x.to(torch.float64)
        s1 += x64.sum(dim=0)
        s2 += (x64 * x64).sum(dim=0)
        n += x64.shape[0]
    if n == 0:
        mean = torch.zeros(input_dim, dtype=torch.float32, device=device)
        inv_std = torch.ones(input_dim, dtype=torch.float32, device=device)
        return mean, inv_std
    mean = s1 / float(n)
    var = (s2 / float(n)) - mean * mean
    var = torch.clamp(var, min=1e-8)
    inv_std = torch.rsqrt(var)
    return mean.to(torch.float32), inv_std.to(torch.float32)


class _EMA:
    def __init__(self, model: nn.Module, decay: float = 0.995):
        self.decay = float(decay)
        self.shadow: Dict[str, torch.Tensor] = {}
        self.backup: Dict[str, torch.Tensor] = {}
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
    def apply(self, model: nn.Module):
        self.backup = {}
        for name, p in model.named_parameters():
            if not p.requires_grad:
                continue
            self.backup[name] = p.detach().clone()
            p.copy_(self.shadow[name])

    @torch.no_grad()
    def restore(self, model: nn.Module):
        for name, p in model.named_parameters():
            if not p.requires_grad:
                continue
            if name in self.backup:
                p.copy_(self.backup[name])
        self.backup = {}


class _ResMLP(nn.Module):
    def __init__(self, input_dim: int, num_classes: int, width: int, dropout: float, x_mean: torch.Tensor, x_inv_std: torch.Tensor):
        super().__init__()
        self.register_buffer("x_mean", x_mean.detach().clone(), persistent=True)
        self.register_buffer("x_inv_std", x_inv_std.detach().clone(), persistent=True)

        self.fc1 = nn.Linear(input_dim, width, bias=False)
        self.ln1 = nn.LayerNorm(width)
        self.fc2 = nn.Linear(width, width, bias=False)
        self.ln2 = nn.LayerNorm(width)
        self.fc3 = nn.Linear(width, num_classes, bias=True)

        self.dropout = nn.Dropout(dropout)
        self.dropout2 = nn.Dropout(dropout * 0.5)

        self.logit_scale = nn.Parameter(torch.tensor(1.0, dtype=torch.float32))

        self._init_weights()

    def _init_weights(self):
        nn.init.kaiming_normal_(self.fc1.weight, nonlinearity="linear")
        nn.init.kaiming_normal_(self.fc2.weight, nonlinearity="linear")
        nn.init.zeros_(self.fc3.bias)
        nn.init.kaiming_normal_(self.fc3.weight, nonlinearity="linear")

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        if x.dtype != torch.float32:
            x = x.float()
        if x.dim() == 1:
            x = x.unsqueeze(0)
        x = (x - self.x_mean) * self.x_inv_std

        h1 = self.fc1(x)
        h1 = self.ln1(h1)
        h1 = F.gelu(h1)
        h1 = self.dropout(h1)

        h2 = self.fc2(h1)
        h2 = self.ln2(h2)
        h2 = F.gelu(h2)
        h2 = self.dropout(h2)

        h = F.gelu(h1 + h2)
        h = self.dropout2(h)

        logits = self.fc3(h)
        scale = torch.clamp(self.logit_scale, 0.25, 4.0)
        return logits * scale


@torch.no_grad()
def _accuracy(model: nn.Module, loader, device: torch.device) -> float:
    model.eval()
    correct = 0
    total = 0
    for x, y in _iter_batches(loader):
        x = x.to(device=device)
        y = y.to(device=device)
        out = model(x)
        pred = out.argmax(dim=1)
        correct += (pred == y).sum().item()
        total += y.numel()
    return float(correct) / float(max(1, total))


def _build_param_groups(model: nn.Module, weight_decay: float):
    decay = []
    no_decay = []
    for name, p in model.named_parameters():
        if not p.requires_grad:
            continue
        if p.ndim == 1 or name.endswith(".bias") or "ln" in name.lower() or "norm" in name.lower():
            no_decay.append(p)
        else:
            decay.append(p)
    return [
        {"params": decay, "weight_decay": float(weight_decay)},
        {"params": no_decay, "weight_decay": 0.0},
    ]


class Solution:
    def solve(self, train_loader, val_loader, metadata: dict = None) -> torch.nn.Module:
        if metadata is None:
            metadata = {}
        device_str = metadata.get("device", "cpu")
        device = torch.device(device_str)

        try:
            cpu_threads = int(os.environ.get("OMP_NUM_THREADS", "0"))
        except Exception:
            cpu_threads = 0
        if cpu_threads <= 0:
            cpu_threads = min(8, os.cpu_count() or 1)
        torch.set_num_threads(cpu_threads)

        torch.manual_seed(0)

        input_dim = int(metadata.get("input_dim", 384))
        num_classes = int(metadata.get("num_classes", 128))
        param_limit = int(metadata.get("param_limit", 200000))

        x_mean, x_inv_std = _compute_mean_std(train_loader, input_dim=input_dim, device=device)

        width = 258
        dropout = 0.15

        model = _ResMLP(input_dim=input_dim, num_classes=num_classes, width=width, dropout=dropout, x_mean=x_mean, x_inv_std=x_inv_std).to(device)
        if _count_trainable_params(model) > param_limit:
            width = 256
            model = _ResMLP(input_dim=input_dim, num_classes=num_classes, width=width, dropout=dropout, x_mean=x_mean, x_inv_std=x_inv_std).to(device)

        if _count_trainable_params(model) > param_limit:
            width = 240
            model = _ResMLP(input_dim=input_dim, num_classes=num_classes, width=width, dropout=dropout, x_mean=x_mean, x_inv_std=x_inv_std).to(device)

        if _count_trainable_params(model) > param_limit:
            width = 192
            model = _ResMLP(input_dim=input_dim, num_classes=num_classes, width=width, dropout=dropout, x_mean=x_mean, x_inv_std=x_inv_std).to(device)

        if _count_trainable_params(model) > param_limit:
            for p in model.parameters():
                p.requires_grad_(False)
            return model.cpu().eval()

        weight_decay = 1.5e-2
        param_groups = _build_param_groups(model, weight_decay=weight_decay)
        optimizer = torch.optim.AdamW(param_groups, lr=4e-3, betas=(0.9, 0.99), eps=1e-8)
        criterion = nn.CrossEntropyLoss(label_smoothing=0.10)

        try:
            steps_per_epoch = len(train_loader)
        except Exception:
            steps_per_epoch = None

        max_epochs = 220
        min_epochs = 40
        patience = 28
        best_val = -1.0
        best_state = None

        ema = _EMA(model, decay=0.995)

        total_steps = (steps_per_epoch * max_epochs) if steps_per_epoch is not None else None
        warmup_steps = int(0.10 * total_steps) if total_steps is not None else 0
        min_lr = 2.0e-4
        max_lr = 4.0e-3
        global_step = 0

        def set_lr(step: int):
            if total_steps is None:
                return
            if warmup_steps > 0 and step < warmup_steps:
                lr = max_lr * float(step + 1) / float(warmup_steps)
            else:
                if total_steps <= warmup_steps + 1:
                    lr = min_lr
                else:
                    t = float(step - warmup_steps) / float(max(1, total_steps - warmup_steps - 1))
                    t = min(1.0, max(0.0, t))
                    lr = min_lr + 0.5 * (max_lr - min_lr) * (1.0 + math.cos(math.pi * t))
            for pg in optimizer.param_groups:
                pg["lr"] = lr

        no_improve = 0
        for epoch in range(max_epochs):
            model.train()
            for x, y in _iter_batches(train_loader):
                x = x.to(device=device)
                y = y.to(device=device)

                set_lr(global_step)

                optimizer.zero_grad(set_to_none=True)
                out = model(x)
                loss = criterion(out, y)
                loss.backward()
                torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
                optimizer.step()
                ema.update(model)

                global_step += 1

            ema.apply(model)
            val_acc = _accuracy(model, val_loader, device=device)
            ema.restore(model)

            if val_acc > best_val + 1e-4:
                best_val = val_acc
                ema.apply(model)
                best_state = deepcopy(model.state_dict())
                ema.restore(model)
                no_improve = 0
            else:
                no_improve += 1

            if epoch + 1 >= min_epochs and no_improve >= patience:
                break

        if best_state is not None:
            model.load_state_dict(best_state, strict=True)
        else:
            ema.apply(model)

        model = model.to("cpu").eval()
        return model
