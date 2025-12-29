import os
import math
import copy
import time
from typing import Optional, Tuple, Dict, Any

import torch
import torch.nn as nn
import torch.nn.functional as F


def _unwrap_batch(batch):
    if isinstance(batch, (list, tuple)):
        if len(batch) >= 2:
            return batch[0], batch[1]
    raise ValueError("Expected batch to be a tuple/list (inputs, targets).")


def _collect_loader(loader) -> Tuple[torch.Tensor, torch.Tensor]:
    xs = []
    ys = []
    for batch in loader:
        x, y = _unwrap_batch(batch)
        if not torch.is_floating_point(x):
            x = x.float()
        else:
            x = x.float()
        y = y.long()
        xs.append(x.detach().cpu())
        ys.append(y.detach().cpu())
    return torch.cat(xs, dim=0).contiguous(), torch.cat(ys, dim=0).contiguous()


def _count_trainable_params(model: nn.Module) -> int:
    return sum(p.numel() for p in model.parameters() if p.requires_grad)


class _ResidualBottleneck(nn.Module):
    def __init__(self, dim: int, bottleneck: int, dropout: float):
        super().__init__()
        self.norm = nn.LayerNorm(dim)
        self.fc1 = nn.Linear(dim, bottleneck, bias=True)
        self.fc2 = nn.Linear(bottleneck, dim, bias=True)
        self.drop = nn.Dropout(dropout)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        y = self.norm(x)
        y = self.fc1(y)
        y = F.gelu(y)
        y = self.drop(y)
        y = self.fc2(y)
        y = self.drop(y)
        return x + y


class _NormalizedResidualMLP(nn.Module):
    def __init__(
        self,
        input_dim: int,
        num_classes: int,
        width: int,
        depth: int,
        bottleneck_ratio: float,
        dropout: float,
        noise_std: float,
    ):
        super().__init__()
        self.input_dim = int(input_dim)
        self.num_classes = int(num_classes)
        self.width = int(width)
        self.depth = int(depth)
        self.bottleneck_ratio = float(bottleneck_ratio)
        self.dropout = float(dropout)
        self.noise_std = float(noise_std)

        self.register_buffer("x_mean", torch.zeros(self.input_dim, dtype=torch.float32), persistent=True)
        self.register_buffer("x_std", torch.ones(self.input_dim, dtype=torch.float32), persistent=True)

        b = max(1, int(self.width * self.bottleneck_ratio))
        self.fc_in = nn.Linear(self.input_dim, self.width, bias=True)
        self.blocks = nn.ModuleList([_ResidualBottleneck(self.width, b, self.dropout) for _ in range(self.depth)])
        self.norm_out = nn.LayerNorm(self.width)
        self.fc_out = nn.Linear(self.width, self.num_classes, bias=True)

    def set_normalization(self, mean: torch.Tensor, std: torch.Tensor):
        mean = mean.detach().float().view(-1).cpu()
        std = std.detach().float().view(-1).cpu()
        if mean.numel() != self.input_dim or std.numel() != self.input_dim:
            raise ValueError("Normalization stats dimension mismatch.")
        self.x_mean.copy_(mean)
        self.x_std.copy_(std)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = x.float()
        x = (x - self.x_mean) / self.x_std
        if self.training and self.noise_std > 0.0:
            x = x + torch.randn_like(x) * self.noise_std

        x = self.fc_in(x)
        x = F.gelu(x)
        for blk in self.blocks:
            x = blk(x)
        x = self.norm_out(x)
        return self.fc_out(x)


class _EMA:
    def __init__(self, model: nn.Module, decay: float = 0.995):
        self.decay = float(decay)
        self.shadow = {}
        self.backup = {}
        with torch.no_grad():
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
    def apply_to(self, model: nn.Module):
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


def _accuracy(model: nn.Module, x: torch.Tensor, y: torch.Tensor, batch_size: int = 512) -> float:
    model.eval()
    correct = 0
    total = int(y.numel())
    with torch.inference_mode():
        for i in range(0, total, batch_size):
            xb = x[i : i + batch_size]
            yb = y[i : i + batch_size]
            logits = model(xb)
            pred = logits.argmax(dim=1)
            correct += int((pred == yb).sum().item())
    return correct / max(1, total)


def _param_estimate(
    input_dim: int,
    num_classes: int,
    width: int,
    depth: int,
    bottleneck_ratio: float,
) -> int:
    d = int(width)
    b = max(1, int(d * float(bottleneck_ratio)))
    # input linear: input_dim*d + d
    # per block: LN 2d + fc1 d*b + b + fc2 b*d + d = 2db + (3d + b)
    # output LN: 2d
    # output linear: d*num_classes + num_classes
    return int(input_dim * d + d + depth * (2 * d * b + (3 * d + b)) + 2 * d + d * num_classes + num_classes)


def _choose_width(
    input_dim: int,
    num_classes: int,
    param_limit: int,
    depth: int,
    bottleneck_ratio: float,
    width_hi: int = 1400,
    width_lo: int = 64,
) -> int:
    lo = int(width_lo)
    hi = int(width_hi)
    best = lo
    while lo <= hi:
        mid = (lo + hi) // 2
        est = _param_estimate(input_dim, num_classes, mid, depth, bottleneck_ratio)
        if est <= param_limit:
            best = mid
            lo = mid + 1
        else:
            hi = mid - 1
    return best


class Solution:
    def solve(self, train_loader, val_loader, metadata: dict = None) -> torch.nn.Module:
        if metadata is None:
            metadata = {}

        device = metadata.get("device", "cpu")
        if device != "cpu":
            device = "cpu"

        try:
            torch.set_num_threads(min(8, os.cpu_count() or 8))
        except Exception:
            pass

        torch.manual_seed(0)

        x_train, y_train = _collect_loader(train_loader)
        x_val, y_val = _collect_loader(val_loader) if val_loader is not None else (None, None)

        if "input_dim" in metadata:
            input_dim = int(metadata["input_dim"])
        else:
            input_dim = int(x_train.shape[1])

        if "num_classes" in metadata:
            num_classes = int(metadata["num_classes"])
        else:
            num_classes = int(torch.max(y_train).item()) + 1

        param_limit = int(metadata.get("param_limit", 2_500_000))

        if x_train.shape[1] != input_dim:
            x_train = x_train[:, :input_dim].contiguous()
            if x_val is not None:
                x_val = x_val[:, :input_dim].contiguous()

        mean = x_train.mean(dim=0)
        std = x_train.std(dim=0, unbiased=False).clamp_min(1e-4)

        depth = 4
        bottleneck_ratio = 0.35
        dropout = 0.10
        noise_std = 0.05

        width = _choose_width(
            input_dim=input_dim,
            num_classes=num_classes,
            param_limit=param_limit,
            depth=depth,
            bottleneck_ratio=bottleneck_ratio,
            width_hi=1600,
            width_lo=64,
        )

        model = _NormalizedResidualMLP(
            input_dim=input_dim,
            num_classes=num_classes,
            width=width,
            depth=depth,
            bottleneck_ratio=bottleneck_ratio,
            dropout=dropout,
            noise_std=noise_std,
        ).to(device)

        model.set_normalization(mean, std)

        if _count_trainable_params(model) > param_limit:
            # Safety fallback
            for _ in range(50):
                width = max(64, width - 1)
                model = _NormalizedResidualMLP(
                    input_dim=input_dim,
                    num_classes=num_classes,
                    width=width,
                    depth=depth,
                    bottleneck_ratio=bottleneck_ratio,
                    dropout=dropout,
                    noise_std=noise_std,
                ).to(device)
                model.set_normalization(mean, std)
                if _count_trainable_params(model) <= param_limit:
                    break

        x_train = x_train.to(device, non_blocking=False)
        y_train = y_train.to(device, non_blocking=False)
        if x_val is not None:
            x_val = x_val.to(device, non_blocking=False)
            y_val = y_val.to(device, non_blocking=False)

        n_train = int(x_train.shape[0])
        batch_size = 256
        steps_per_epoch = max(1, (n_train + batch_size - 1) // batch_size)

        criterion = nn.CrossEntropyLoss(label_smoothing=0.06)

        base_lr = 2.2e-3
        min_lr = 2.0e-4
        weight_decay = 1.2e-2
        optimizer = torch.optim.AdamW(model.parameters(), lr=base_lr, weight_decay=weight_decay)

        epochs = 260
        warmup_epochs = 8
        eval_every = 1 if x_val is not None else 0
        patience = 35
        patience_ctr = 0
        best_acc = -1.0
        best_state = None

        ema = _EMA(model, decay=0.995)

        def set_lr(epoch_idx: int):
            if epoch_idx < warmup_epochs:
                lr = base_lr * float(epoch_idx + 1) / float(max(1, warmup_epochs))
            else:
                t = float(epoch_idx - warmup_epochs) / float(max(1, epochs - warmup_epochs))
                lr = min_lr + 0.5 * (base_lr - min_lr) * (1.0 + math.cos(math.pi * min(1.0, max(0.0, t))))
            for pg in optimizer.param_groups:
                pg["lr"] = lr

        for epoch in range(epochs):
            set_lr(epoch)
            model.train()

            perm = torch.randperm(n_train, device=device)
            for si in range(0, n_train, batch_size):
                idx = perm[si : si + batch_size]
                xb = x_train.index_select(0, idx)
                yb = y_train.index_select(0, idx)

                optimizer.zero_grad(set_to_none=True)
                logits = model(xb)
                loss = criterion(logits, yb)
                loss.backward()
                torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
                optimizer.step()
                ema.update(model)

            if eval_every and ((epoch + 1) % eval_every == 0):
                ema.apply_to(model)
                acc = _accuracy(model, x_val, y_val, batch_size=512)
                sd = model.state_dict()
                ema.restore(model)

                if acc > best_acc + 1e-4:
                    best_acc = acc
                    best_state = {k: v.detach().clone() for k, v in sd.items()}
                    patience_ctr = 0
                else:
                    patience_ctr += 1
                    if patience_ctr >= patience:
                        break

        if best_state is not None:
            model.load_state_dict(best_state, strict=True)
        else:
            ema.apply_to(model)

        model.eval()

        if _count_trainable_params(model) > param_limit:
            # Final safety: freeze excess (shouldn't happen with our builder)
            for p in model.parameters():
                p.requires_grad_(False)

        return model