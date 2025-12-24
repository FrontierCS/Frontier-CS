import math
import copy
import os
from typing import Optional, Dict, Tuple

import torch
import torch.nn as nn


class _InputNorm(nn.Module):
    def __init__(self, mean: torch.Tensor, std: torch.Tensor, eps: float = 1e-6):
        super().__init__()
        self.register_buffer("mean", mean.detach().clone())
        self.register_buffer("std", std.detach().clone())
        self.eps = eps

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return (x - self.mean) / (self.std + self.eps)


class _MLPRes(nn.Module):
    def __init__(self, input_dim: int, num_classes: int, hidden_dim: int, dropout: float = 0.10,
                 mean: Optional[torch.Tensor] = None, std: Optional[torch.Tensor] = None):
        super().__init__()
        self.input_dim = int(input_dim)
        self.num_classes = int(num_classes)
        self.hidden_dim = int(hidden_dim)

        if mean is None:
            mean = torch.zeros(self.input_dim, dtype=torch.float32)
        if std is None:
            std = torch.ones(self.input_dim, dtype=torch.float32)

        self.inorm = _InputNorm(mean.float(), std.float())

        self.drop_in = nn.Dropout(p=min(0.05, dropout))
        self.fc1 = nn.Linear(self.input_dim, self.hidden_dim, bias=True)
        self.ln1 = nn.LayerNorm(self.hidden_dim)

        self.drop1 = nn.Dropout(p=dropout)
        self.fc2 = nn.Linear(self.hidden_dim, self.hidden_dim, bias=True)
        self.ln2 = nn.LayerNorm(self.hidden_dim)
        self.drop2 = nn.Dropout(p=dropout)

        self.fc3 = nn.Linear(self.hidden_dim, self.num_classes, bias=True)

        self.act = nn.GELU()

        self._init_weights()

    def _init_weights(self):
        for m in self.modules():
            if isinstance(m, nn.Linear):
                nn.init.kaiming_normal_(m.weight, nonlinearity="relu")
                if m.bias is not None:
                    nn.init.zeros_(m.bias)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        if x.dim() > 2:
            x = x.view(x.size(0), -1)
        x = x.float()
        x = self.inorm(x)
        x = self.drop_in(x)

        h = self.fc1(x)
        h = self.ln1(h)
        h = self.act(h)

        r = self.drop1(h)
        r = self.fc2(r)
        r = self.ln2(r)
        r = self.drop2(r)

        h = self.act(h + r)
        logits = self.fc3(h)
        return logits


def _count_trainable_params(model: nn.Module) -> int:
    return sum(p.numel() for p in model.parameters() if p.requires_grad)


@torch.no_grad()
def _accuracy(model: nn.Module, loader, device: torch.device) -> float:
    model.eval()
    correct = 0
    total = 0
    for xb, yb in loader:
        xb = xb.to(device, non_blocking=False)
        yb = yb.to(device, non_blocking=False)
        logits = model(xb)
        pred = logits.argmax(dim=1)
        correct += (pred == yb).sum().item()
        total += yb.numel()
    return float(correct) / float(total if total > 0 else 1)


def _compute_mean_std(train_loader, input_dim: int, device: torch.device) -> Tuple[torch.Tensor, torch.Tensor]:
    n = 0
    sum_x = torch.zeros(input_dim, dtype=torch.float64, device=device)
    sum_x2 = torch.zeros(input_dim, dtype=torch.float64, device=device)
    for xb, _ in train_loader:
        xb = xb.to(device, non_blocking=False)
        if xb.dim() > 2:
            xb = xb.view(xb.size(0), -1)
        xb = xb.double()
        if xb.size(1) != input_dim:
            xb = xb[:, :input_dim] if xb.size(1) > input_dim else torch.nn.functional.pad(xb, (0, input_dim - xb.size(1)))
        bs = xb.size(0)
        n += bs
        sum_x += xb.sum(dim=0)
        sum_x2 += (xb * xb).sum(dim=0)
    if n <= 0:
        mean = torch.zeros(input_dim, dtype=torch.float32, device=device)
        std = torch.ones(input_dim, dtype=torch.float32, device=device)
        return mean, std
    mean = sum_x / float(n)
    var = (sum_x2 / float(n)) - mean * mean
    var = torch.clamp(var, min=1e-12)
    std = torch.sqrt(var)
    return mean.float(), std.float()


class Solution:
    def solve(self, train_loader, val_loader, metadata: dict = None) -> torch.nn.Module:
        if metadata is None:
            metadata = {}

        try:
            torch.set_num_threads(min(8, os.cpu_count() or 8))
        except Exception:
            pass

        device_str = metadata.get("device", "cpu")
        device = torch.device(device_str)

        num_classes = int(metadata.get("num_classes", 128))
        input_dim = int(metadata.get("input_dim", 384))
        param_limit = int(metadata.get("param_limit", 200000))

        # Compute normalization from training data
        mean, std = _compute_mean_std(train_loader, input_dim=input_dim, device=device)

        # Pick largest hidden_dim satisfying hard param limit (with 2 LayerNorms + 3 Linear)
        # params = input_dim*h + h*h + h*num_classes + (biases: 2h + num_classes) + (LayerNorm: 4h)
        # total = input_dim*h + h*h + h*num_classes + (6h + num_classes)
        def param_estimate(h: int) -> int:
            return int(input_dim * h + h * h + h * num_classes + (6 * h + num_classes))

        hidden_dim = 256
        if param_estimate(hidden_dim) > param_limit:
            best = None
            for h in range(512, 31, -8):
                if param_estimate(h) <= param_limit:
                    best = h
                    break
            hidden_dim = best if best is not None else 64

        model = _MLPRes(
            input_dim=input_dim,
            num_classes=num_classes,
            hidden_dim=hidden_dim,
            dropout=0.10,
            mean=mean.cpu(),
            std=std.cpu(),
        ).to(device)

        # Hard constraint check
        if _count_trainable_params(model) > param_limit:
            # Fallback to smaller hidden
            for h in range(hidden_dim - 8, 31, -8):
                model = _MLPRes(
                    input_dim=input_dim,
                    num_classes=num_classes,
                    hidden_dim=h,
                    dropout=0.10,
                    mean=mean.cpu(),
                    std=std.cpu(),
                ).to(device)
                if _count_trainable_params(model) <= param_limit:
                    hidden_dim = h
                    break

        # If still over (shouldn't happen), return a tiny linear model
        if _count_trainable_params(model) > param_limit:
            lin = nn.Linear(input_dim, num_classes).to(device)
            return lin

        # Training hyperparams
        max_epochs = int(metadata.get("max_epochs", 90))
        patience = int(metadata.get("patience", 12))
        min_epochs = int(metadata.get("min_epochs", 20))

        lr = float(metadata.get("lr", 5e-3))
        weight_decay = float(metadata.get("weight_decay", 2e-2))
        label_smoothing = float(metadata.get("label_smoothing", 0.10))
        noise_std = float(metadata.get("noise_std", 0.01))

        criterion = nn.CrossEntropyLoss(label_smoothing=label_smoothing)

        optimizer = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=weight_decay, betas=(0.9, 0.99))

        steps_per_epoch = None
        try:
            steps_per_epoch = len(train_loader)
        except Exception:
            steps_per_epoch = None

        per_batch_scheduler = False
        if steps_per_epoch is not None and steps_per_epoch > 0:
            scheduler = torch.optim.lr_scheduler.OneCycleLR(
                optimizer,
                max_lr=lr,
                epochs=max_epochs,
                steps_per_epoch=steps_per_epoch,
                pct_start=0.12,
                div_factor=15.0,
                final_div_factor=200.0,
                anneal_strategy="cos",
                cycle_momentum=False,
            )
            per_batch_scheduler = True
        else:
            scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=max_epochs, eta_min=lr * 0.05)

        best_state = copy.deepcopy(model.state_dict())
        best_acc = -1.0
        best_epoch = -1
        bad_epochs = 0

        for epoch in range(max_epochs):
            model.train()
            for xb, yb in train_loader:
                xb = xb.to(device, non_blocking=False)
                yb = yb.to(device, non_blocking=False)

                if xb.dim() > 2:
                    xb = xb.view(xb.size(0), -1)
                xb = xb.float()

                if noise_std > 0.0:
                    xb = xb + (noise_std * torch.randn_like(xb))

                optimizer.zero_grad(set_to_none=True)
                logits = model(xb)
                loss = criterion(logits, yb)
                loss.backward()
                torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
                optimizer.step()
                if per_batch_scheduler:
                    scheduler.step()

            if not per_batch_scheduler:
                scheduler.step()

            val_acc = _accuracy(model, val_loader, device=device)

            improved = val_acc > (best_acc + 1e-4)
            if improved:
                best_acc = val_acc
                best_epoch = epoch
                best_state = copy.deepcopy(model.state_dict())
                bad_epochs = 0
            else:
                bad_epochs += 1

            if epoch + 1 >= min_epochs and bad_epochs >= patience:
                break

        model.load_state_dict(best_state)
        model.to("cpu")
        model.eval()
        return model
