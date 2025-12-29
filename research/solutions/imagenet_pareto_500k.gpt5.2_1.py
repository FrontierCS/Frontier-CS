import os
import math
import copy
from typing import Optional, Dict, Tuple

import torch
import torch.nn as nn


def _count_trainable_params(model: nn.Module) -> int:
    return sum(p.numel() for p in model.parameters() if p.requires_grad)


class _BottleneckResidualBlock(nn.Module):
    def __init__(self, dim: int, bottleneck_dim: int, dropout: float = 0.0, layerscale_init: float = 0.1):
        super().__init__()
        self.ln = nn.LayerNorm(dim)
        self.fc1 = nn.Linear(dim, bottleneck_dim)
        self.act = nn.GELU()
        self.drop1 = nn.Dropout(dropout)
        self.fc2 = nn.Linear(bottleneck_dim, dim)
        self.drop2 = nn.Dropout(dropout)
        self.gamma = nn.Parameter(torch.full((dim,), float(layerscale_init), dtype=torch.float32))

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        y = self.ln(x)
        y = self.fc1(y)
        y = self.act(y)
        y = self.drop1(y)
        y = self.fc2(y)
        y = self.drop2(y)
        return x + y * self.gamma


class _ResidualMLPNet(nn.Module):
    def __init__(
        self,
        input_dim: int,
        num_classes: int,
        depth: int,
        bottleneck_dim: int,
        dropout: float = 0.05,
        layerscale_init: float = 0.1,
    ):
        super().__init__()
        self.input_dim = int(input_dim)
        self.num_classes = int(num_classes)

        self.in_ln = nn.LayerNorm(self.input_dim)
        self.blocks = nn.ModuleList(
            [
                _BottleneckResidualBlock(
                    dim=self.input_dim,
                    bottleneck_dim=bottleneck_dim,
                    dropout=dropout,
                    layerscale_init=layerscale_init,
                )
                for _ in range(int(depth))
            ]
        )
        self.out_ln = nn.LayerNorm(self.input_dim)
        self.head = nn.Linear(self.input_dim, self.num_classes)

        self.register_buffer("x_mean", torch.zeros(self.input_dim, dtype=torch.float32), persistent=True)
        self.register_buffer("x_invstd", torch.ones(self.input_dim, dtype=torch.float32), persistent=True)

    def set_normalization(self, mean: torch.Tensor, std: torch.Tensor):
        mean = mean.detach().to(dtype=torch.float32, device=self.x_mean.device)
        std = std.detach().to(dtype=torch.float32, device=self.x_mean.device)
        std = torch.clamp(std, min=1e-6)
        self.x_mean.copy_(mean)
        self.x_invstd.copy_(1.0 / std)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        if x.dtype != torch.float32:
            x = x.float()
        x = (x - self.x_mean) * self.x_invstd
        x = self.in_ln(x)
        for b in self.blocks:
            x = b(x)
        x = self.out_ln(x)
        return self.head(x)


def _compute_mean_std_from_loader(loader, input_dim: int, device: str) -> Tuple[torch.Tensor, torch.Tensor]:
    s1 = torch.zeros(input_dim, dtype=torch.float64)
    s2 = torch.zeros(input_dim, dtype=torch.float64)
    n = 0
    with torch.no_grad():
        for xb, _ in loader:
            xb = xb.detach().to("cpu")
            if xb.ndim != 2 or xb.shape[1] != input_dim:
                xb = xb.view(xb.shape[0], -1)
            xb = xb.to(dtype=torch.float64)
            s1 += xb.sum(dim=0)
            s2 += (xb * xb).sum(dim=0)
            n += xb.shape[0]
    if n <= 0:
        mean = torch.zeros(input_dim, dtype=torch.float32, device=device)
        std = torch.ones(input_dim, dtype=torch.float32, device=device)
        return mean, std
    mean64 = s1 / float(n)
    var64 = s2 / float(n) - mean64 * mean64
    var64 = torch.clamp(var64, min=1e-8)
    std64 = torch.sqrt(var64)
    mean = mean64.to(dtype=torch.float32, device=device)
    std = std64.to(dtype=torch.float32, device=device)
    return mean, std


def _accuracy(model: nn.Module, loader, device: str) -> float:
    model.eval()
    correct = 0
    total = 0
    with torch.inference_mode():
        for xb, yb in loader:
            xb = xb.to(device=device)
            yb = yb.to(device=device)
            logits = model(xb)
            pred = logits.argmax(dim=1)
            correct += (pred == yb).sum().item()
            total += int(yb.numel())
    return float(correct) / float(total) if total > 0 else 0.0


class Solution:
    def solve(self, train_loader, val_loader, metadata: dict = None) -> torch.nn.Module:
        if metadata is None:
            metadata = {}
        input_dim = int(metadata.get("input_dim", 384))
        num_classes = int(metadata.get("num_classes", 128))
        param_limit = int(metadata.get("param_limit", 500000))
        device = str(metadata.get("device", "cpu"))

        try:
            torch.set_num_threads(min(8, os.cpu_count() or 8))
        except Exception:
            pass

        torch.manual_seed(0)

        # Build model close to the limit but safe
        # Primary candidate: depth=4, bottleneck=144, with layerscale.
        candidates = [
            (4, 144, 0.05, 0.1),
            (3, 192, 0.05, 0.1),
            (4, 128, 0.05, 0.1),
            (3, 160, 0.05, 0.1),
            (2, 192, 0.05, 0.1),
        ]

        model = None
        for depth, bottleneck, dropout, ls_init in candidates:
            m = _ResidualMLPNet(
                input_dim=input_dim,
                num_classes=num_classes,
                depth=depth,
                bottleneck_dim=bottleneck,
                dropout=dropout,
                layerscale_init=ls_init,
            )
            if _count_trainable_params(m) <= param_limit:
                model = m
                break

        if model is None:
            # Minimal fallback
            hidden = min(input_dim, 256)
            model = nn.Sequential(
                nn.Linear(input_dim, hidden),
                nn.GELU(),
                nn.Linear(hidden, num_classes),
            )

        model.to(device)

        # Set normalization from training data
        mean, std = _compute_mean_std_from_loader(train_loader, input_dim=input_dim, device=device)
        if isinstance(model, _ResidualMLPNet):
            model.set_normalization(mean, std)

        # Training
        train_steps_per_epoch = max(1, len(train_loader))
        train_samples = int(metadata.get("train_samples", 2048))
        base_epochs = 160
        if train_samples <= 1024:
            epochs = 220
        elif train_samples <= 2048:
            epochs = base_epochs
        else:
            epochs = 120

        max_lr = 4e-3
        if _count_trainable_params(model) < 250000:
            max_lr = 5e-3

        wd = 0.02
        optimizer = torch.optim.AdamW(model.parameters(), lr=max_lr, weight_decay=wd, betas=(0.9, 0.99), eps=1e-8)

        total_steps = epochs * train_steps_per_epoch
        if total_steps < 10:
            total_steps = 10
        scheduler = torch.optim.lr_scheduler.OneCycleLR(
            optimizer,
            max_lr=max_lr,
            total_steps=total_steps,
            pct_start=0.12,
            anneal_strategy="cos",
            div_factor=15.0,
            final_div_factor=30.0,
        )

        try:
            criterion = nn.CrossEntropyLoss(label_smoothing=0.05)
        except TypeError:
            criterion = nn.CrossEntropyLoss()

        best_state = copy.deepcopy(model.state_dict())
        best_val = -1.0
        patience = 30
        bad_epochs = 0

        use_val = val_loader is not None
        ema_state = {k: v.detach().clone() for k, v in model.state_dict().items()}
        ema_decay = 0.995

        noise_std = 0.02 if isinstance(model, _ResidualMLPNet) else 0.0

        step_idx = 0
        for epoch in range(epochs):
            model.train()
            for xb, yb in train_loader:
                xb = xb.to(device=device)
                yb = yb.to(device=device)

                if noise_std > 0.0:
                    xb = xb + torch.randn_like(xb) * noise_std

                optimizer.zero_grad(set_to_none=True)
                logits = model(xb)
                loss = criterion(logits, yb)
                loss.backward()
                torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
                optimizer.step()

                step_idx += 1
                if step_idx <= total_steps:
                    scheduler.step()

                with torch.no_grad():
                    sd = model.state_dict()
                    for k, v in sd.items():
                        ema_state[k].mul_(ema_decay).add_(v, alpha=1.0 - ema_decay)

            if use_val:
                # Evaluate current
                val_acc = _accuracy(model, val_loader, device)
                if val_acc > best_val + 1e-4:
                    best_val = val_acc
                    best_state = copy.deepcopy(model.state_dict())
                    bad_epochs = 0
                else:
                    bad_epochs += 1
                    if bad_epochs >= patience and epoch >= 40:
                        break

        # Load best or EMA if it looks better
        if use_val:
            model.load_state_dict(best_state)
            acc_best = _accuracy(model, val_loader, device)

            # Try EMA
            model_ema = copy.deepcopy(model)
            model_ema.load_state_dict(ema_state)
            acc_ema = _accuracy(model_ema, val_loader, device)
            if acc_ema >= acc_best - 1e-4:
                model = model_ema
        else:
            model.load_state_dict(ema_state)

        model.to(device)
        model.eval()

        # Safety check
        if _count_trainable_params(model) > param_limit:
            # Fallback to a safe small model if something went wrong.
            safe_hidden = min(256, input_dim)
            safe_model = nn.Sequential(
                nn.Linear(input_dim, safe_hidden),
                nn.ReLU(),
                nn.Linear(safe_hidden, num_classes),
            ).to(device)
            safe_model.eval()
            return safe_model

        return model