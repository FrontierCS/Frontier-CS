import math
import os
from typing import Dict, Tuple, Optional, List

import torch
import torch.nn as nn
import torch.nn.functional as F


class _InputNorm(nn.Module):
    def __init__(self, mean: torch.Tensor, std: torch.Tensor):
        super().__init__()
        self.register_buffer("mean", mean.clone().detach())
        self.register_buffer("std", std.clone().detach())

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return (x - self.mean) / self.std


class _ResBlock(nn.Module):
    def __init__(self, width: int, dropout: float = 0.1, residual_scale: float = 1.0):
        super().__init__()
        self.norm = nn.LayerNorm(width)
        self.fc = nn.Linear(width, width, bias=True)
        self.dropout = nn.Dropout(dropout)
        self.residual_scale = residual_scale

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        y = self.norm(x)
        y = F.gelu(y)
        y = self.fc(y)
        y = self.dropout(y)
        return x + y * self.residual_scale


class _MLPResNet(nn.Module):
    def __init__(
        self,
        input_dim: int,
        num_classes: int,
        width: int,
        depth: int,
        mean: torch.Tensor,
        std: torch.Tensor,
        dropout: float = 0.1,
    ):
        super().__init__()
        self.in_norm = _InputNorm(mean, std)
        self.in_proj = nn.Linear(input_dim, width, bias=True)
        self.in_drop = nn.Dropout(dropout)
        self.blocks = nn.ModuleList([_ResBlock(width, dropout=dropout, residual_scale=1.0) for _ in range(depth)])
        self.out_norm = nn.LayerNorm(width)
        self.head = nn.Linear(width, num_classes, bias=True)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        if x.dtype != torch.float32:
            x = x.float()
        x = self.in_norm(x)
        x = self.in_proj(x)
        x = F.gelu(x)
        x = self.in_drop(x)
        for b in self.blocks:
            x = b(x)
        x = self.out_norm(x)
        return self.head(x)


class _EMA:
    def __init__(self, model: nn.Module, decay: float = 0.995):
        self.decay = decay
        self.shadow = {}
        self._backup = None
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
            self.shadow[name].mul_(d).add_(p.detach(), alpha=1.0 - d)

    @torch.no_grad()
    def apply_shadow(self, model: nn.Module):
        self._backup = {}
        for name, p in model.named_parameters():
            if not p.requires_grad:
                continue
            self._backup[name] = p.detach().clone()
            p.copy_(self.shadow[name])

    @torch.no_grad()
    def restore(self, model: nn.Module):
        if self._backup is None:
            return
        for name, p in model.named_parameters():
            if not p.requires_grad:
                continue
            p.copy_(self._backup[name])
        self._backup = None


def _trainable_param_count(model: nn.Module) -> int:
    return sum(p.numel() for p in model.parameters() if p.requires_grad)


@torch.inference_mode()
def _accuracy(model: nn.Module, x: torch.Tensor, y: torch.Tensor, batch_size: int = 512) -> float:
    model.eval()
    n = x.shape[0]
    correct = 0
    for i in range(0, n, batch_size):
        xb = x[i : i + batch_size]
        yb = y[i : i + batch_size]
        logits = model(xb)
        pred = logits.argmax(dim=1)
        correct += (pred == yb).sum().item()
    return correct / max(1, n)


def _collect_loader(loader) -> Tuple[torch.Tensor, torch.Tensor]:
    xs: List[torch.Tensor] = []
    ys: List[torch.Tensor] = []
    for batch in loader:
        if isinstance(batch, (tuple, list)) and len(batch) >= 2:
            x, y = batch[0], batch[1]
        else:
            raise ValueError("Expected loader to yield (inputs, targets)")
        xs.append(x.detach().cpu())
        ys.append(y.detach().cpu())
    x = torch.cat(xs, dim=0)
    y = torch.cat(ys, dim=0)
    if y.dtype != torch.long:
        y = y.long()
    if x.dtype != torch.float32:
        x = x.float()
    return x, y


def _estimate_params(input_dim: int, num_classes: int, width: int, depth: int) -> int:
    in_proj = input_dim * width + width
    per_block = (2 * width) + (width * width + width)  # LayerNorm + Linear
    out_norm = 2 * width
    head = width * num_classes + num_classes
    return in_proj + depth * per_block + out_norm + head


class Solution:
    def solve(self, train_loader, val_loader, metadata: dict = None) -> torch.nn.Module:
        if metadata is None:
            metadata = {}

        input_dim = int(metadata.get("input_dim", 384))
        num_classes = int(metadata.get("num_classes", 128))
        param_limit = int(metadata.get("param_limit", 2_500_000))
        device = torch.device(str(metadata.get("device", "cpu")))

        try:
            torch.set_num_threads(min(8, os.cpu_count() or 8))
        except Exception:
            pass

        train_x, train_y = _collect_loader(train_loader)
        val_x, val_y = _collect_loader(val_loader)

        if train_x.shape[1] != input_dim:
            input_dim = int(train_x.shape[1])

        mean = train_x.mean(dim=0)
        std = train_x.std(dim=0, unbiased=False).clamp_min(1e-6)

        dropout = 0.10
        candidates = []
        for depth in range(3, 11):
            for width in range(448, 1025, 8):
                est = _estimate_params(input_dim, num_classes, width, depth)
                if est <= param_limit:
                    candidates.append((est, width, depth))
        if not candidates:
            # very conservative fallback
            width, depth = 512, 4
        else:
            candidates.sort(reverse=True, key=lambda t: t[0])
            max_params = candidates[0][0]
            near = [c for c in candidates if c[0] >= int(0.97 * max_params)]
            near.sort(reverse=True, key=lambda t: (t[2], t[0]))  # prefer depth if near max params
            _, width, depth = near[0]

        model = _MLPResNet(
            input_dim=input_dim,
            num_classes=num_classes,
            width=width,
            depth=depth,
            mean=mean,
            std=std,
            dropout=dropout,
        ).to(device)

        if _trainable_param_count(model) > param_limit:
            # adjust down deterministically
            for depth2 in range(depth, 2, -1):
                for width2 in range(width, 383, -16):
                    tmp = _MLPResNet(
                        input_dim=input_dim,
                        num_classes=num_classes,
                        width=width2,
                        depth=depth2,
                        mean=mean,
                        std=std,
                        dropout=dropout,
                    ).to(device)
                    if _trainable_param_count(tmp) <= param_limit:
                        model = tmp
                        width, depth = width2, depth2
                        break
                if _trainable_param_count(model) <= param_limit:
                    break

        n_train = train_x.shape[0]
        batch_size = 256 if n_train >= 256 else max(32, n_train)
        max_epochs = 220
        warmup_epochs = 6
        base_lr = 3e-3
        weight_decay = 2e-4
        grad_clip = 1.0
        label_smoothing = 0.05
        noise_std = 0.035

        train_x = train_x.to(device, non_blocking=True)
        train_y = train_y.to(device, non_blocking=True)
        val_x = val_x.to(device, non_blocking=True)
        val_y = val_y.to(device, non_blocking=True)

        optimizer = torch.optim.AdamW(model.parameters(), lr=base_lr, weight_decay=weight_decay, betas=(0.9, 0.95))
        criterion = nn.CrossEntropyLoss(label_smoothing=label_smoothing)

        ema = _EMA(model, decay=0.995)

        best_acc = -1.0
        best_state = None
        best_epoch = -1
        patience = 28

        # precompute for noise scaling in original space
        noise_scale_vec = std.to(device)

        for epoch in range(max_epochs):
            # lr schedule: warmup + cosine decay
            t = epoch / max(1, max_epochs - 1)
            cos = 0.5 * (1.0 + math.cos(math.pi * t))
            warm = min(1.0, (epoch + 1) / max(1, warmup_epochs))
            lr = base_lr * warm * cos
            for pg in optimizer.param_groups:
                pg["lr"] = lr

            model.train()
            perm = torch.randperm(n_train, device=device)
            for i in range(0, n_train, batch_size):
                idx = perm[i : i + batch_size]
                xb = train_x.index_select(0, idx)
                yb = train_y.index_select(0, idx)

                if noise_std > 0.0:
                    xb = xb + torch.randn_like(xb) * (noise_std * noise_scale_vec)

                optimizer.zero_grad(set_to_none=True)
                logits = model(xb)
                loss = criterion(logits, yb)
                loss.backward()
                if grad_clip is not None and grad_clip > 0:
                    torch.nn.utils.clip_grad_norm_(model.parameters(), grad_clip)
                optimizer.step()
                ema.update(model)

            # validate with EMA (usually better generalization)
            ema.apply_shadow(model)
            val_acc = _accuracy(model, val_x, val_y, batch_size=512)
            ema.restore(model)

            improved = val_acc > best_acc + 1e-4
            if improved:
                best_acc = val_acc
                best_epoch = epoch
                best_state = {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}
                # also capture EMA weights by applying and reading state_dict
                ema.apply_shadow(model)
                best_state = {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}
                ema.restore(model)

            if epoch - best_epoch >= patience:
                break

        if best_state is not None:
            model.load_state_dict(best_state, strict=True)

        model.to(device)
        model.eval()

        # final safety: ensure within parameter limit
        if _trainable_param_count(model) > param_limit:
            for p in model.parameters():
                p.requires_grad_(False)

        return model