import math
import copy
from typing import Optional

import torch
import torch.nn as nn
import torch.nn.functional as F


class Standardize(nn.Module):
    def __init__(self, dim: int, mean: Optional[torch.Tensor] = None, std: Optional[torch.Tensor] = None):
        super().__init__()
        if mean is None:
            mean = torch.zeros(dim, dtype=torch.float32)
        if std is None:
            std = torch.ones(dim, dtype=torch.float32)
        self.register_buffer("mean", mean.view(1, -1))
        self.register_buffer("std", std.view(1, -1))

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return (x - self.mean) / (self.std + 1e-5)


class PreNormResidualBlock(nn.Module):
    def __init__(self, dim: int, dropout: float = 0.05):
        super().__init__()
        self.norm1 = nn.LayerNorm(dim)
        self.fc1 = nn.Linear(dim, dim, bias=True)
        self.act = nn.GELU()
        self.drop1 = nn.Dropout(dropout)
        self.norm2 = nn.LayerNorm(dim)
        self.fc2 = nn.Linear(dim, dim, bias=True)
        self.drop2 = nn.Dropout(dropout)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        residual = x
        x = self.norm1(x)
        x = self.fc1(x)
        x = self.act(x)
        x = self.drop1(x)
        x = self.norm2(x)
        x = self.fc2(x)
        x = self.drop2(x)
        return x + residual


class MLPNet(nn.Module):
    def __init__(
        self,
        input_dim: int,
        num_classes: int,
        width: int,
        num_blocks: int = 2,
        dropout: float = 0.05,
        mean: Optional[torch.Tensor] = None,
        std: Optional[torch.Tensor] = None,
    ):
        super().__init__()
        self.standardize = Standardize(input_dim, mean, std)
        self.in_proj = nn.Linear(input_dim, width, bias=True)
        blocks = []
        for _ in range(num_blocks):
            blocks.append(PreNormResidualBlock(width, dropout=dropout))
        self.blocks = nn.Sequential(*blocks)
        self.head_norm = nn.LayerNorm(width)
        self.head = nn.Linear(width, num_classes, bias=True)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self.standardize(x)
        x = self.in_proj(x)
        x = self.blocks(x)
        x = self.head_norm(x)
        x = self.head(x)
        return x


def count_trainable_params(model: nn.Module) -> int:
    return sum(p.numel() for p in model.parameters() if p.requires_grad)


def compute_dataset_stats(loader, device: torch.device, dim: int):
    total = 0
    mean = torch.zeros(dim, dtype=torch.float64, device=device)
    m2 = torch.zeros(dim, dtype=torch.float64, device=device)
    for inputs, _ in loader:
        inputs = inputs.to(device, dtype=torch.float32)
        batch = inputs.shape[0]
        total_new = total + batch
        delta = inputs - mean
        mean = mean + delta.sum(dim=0, dtype=torch.float64) / total_new
        delta2 = inputs - mean
        m2 = m2 + (delta * delta2).sum(dim=0, dtype=torch.float64)
        total = total_new
    if total < 2:
        std = torch.ones(dim, dtype=torch.float64, device=device)
    else:
        var = m2 / max(total - 1, 1)
        std = torch.sqrt(torch.clamp(var, min=1e-8))
    return mean.float().cpu(), std.float().cpu()


class ModelEMA:
    def __init__(self, model: nn.Module, decay: float = 0.995):
        self.ema = copy.deepcopy(model).eval()
        for p in self.ema.parameters():
            p.requires_grad_(False)
        self.decay = decay

    @torch.no_grad()
    def update(self, model: nn.Module):
        d = self.decay
        for ema_p, p in zip(self.ema.parameters(), model.parameters()):
            ema_p.mul_(d).add_(p.data, alpha=1.0 - d)
        for (ema_name, ema_buf), (name, buf) in zip(self.ema.named_buffers(), model.named_buffers()):
            if buf.dtype.is_floating_point:
                ema_buf.mul_(d).add_(buf, alpha=1.0 - d)
            else:
                ema_buf.copy_(buf)


def evaluate(model: nn.Module, loader, device: torch.device, criterion: Optional[nn.Module] = None):
    model.eval()
    total = 0
    correct = 0
    loss_sum = 0.0
    with torch.no_grad():
        for inputs, targets in loader:
            inputs = inputs.to(device, dtype=torch.float32)
            targets = targets.to(device, dtype=torch.long)
            outputs = model(inputs)
            if criterion is not None:
                loss = criterion(outputs, targets)
                loss_sum += loss.item() * targets.numel()
            preds = outputs.argmax(dim=1)
            correct += (preds == targets).sum().item()
            total += targets.numel()
    acc = correct / max(total, 1)
    avg_loss = loss_sum / max(total, 1) if criterion is not None else 0.0
    return avg_loss, acc


class Solution:
    def solve(self, train_loader, val_loader, metadata: dict = None) -> torch.nn.Module:
        if metadata is None:
            metadata = {}
        input_dim = int(metadata.get("input_dim", 384))
        num_classes = int(metadata.get("num_classes", 128))
        param_limit = int(metadata.get("param_limit", 5_000_000))
        device_str = metadata.get("device", "cpu")
        device = torch.device(device_str)

        torch.manual_seed(42)

        mean, std = compute_dataset_stats(train_loader, device, input_dim)
        width_candidates = list(range(1216, 703, -32))  # from 1216 down to 704 in steps of 32
        best_width = 1024
        num_blocks = 2
        dropout = 0.05

        selected_model = None
        for w in width_candidates:
            model_try = MLPNet(input_dim, num_classes, width=w, num_blocks=num_blocks, dropout=dropout, mean=mean, std=std)
            params = count_trainable_params(model_try)
            if params <= param_limit:
                selected_model = model_try
                best_width = w
                break
        if selected_model is None:
            # fallback minimal model
            best_width = 512
            selected_model = MLPNet(input_dim, num_classes, width=best_width, num_blocks=num_blocks, dropout=dropout, mean=mean, std=std)
            # Ensure under limit by decreasing blocks if needed
            if count_trainable_params(selected_model) > param_limit:
                selected_model = MLPNet(input_dim, num_classes, width=best_width, num_blocks=1, dropout=dropout, mean=mean, std=std)

        model = selected_model.to(device)

        # Training setup
        label_smoothing = 0.1
        criterion = nn.CrossEntropyLoss(label_smoothing=label_smoothing)
        base_lr = 2e-3
        weight_decay = 1e-4
        optimizer = torch.optim.AdamW(model.parameters(), lr=base_lr, weight_decay=weight_decay, betas=(0.9, 0.999))
        steps_per_epoch = max(len(train_loader), 1)
        epochs = 160
        scheduler = torch.optim.lr_scheduler.OneCycleLR(
            optimizer,
            max_lr=base_lr * 3.0,
            epochs=epochs,
            steps_per_epoch=steps_per_epoch,
            pct_start=0.15,
            div_factor=5.0,
            final_div_factor=10.0,
        )

        ema = ModelEMA(model, decay=0.995)

        best_acc = -1.0
        best_state = None
        patience = 30
        patience_counter = 0
        clip_grad = 1.0

        for epoch in range(epochs):
            model.train()
            for inputs, targets in train_loader:
                inputs = inputs.to(device, dtype=torch.float32)
                targets = targets.to(device, dtype=torch.long)

                optimizer.zero_grad(set_to_none=True)
                outputs = model(inputs)
                loss = criterion(outputs, targets)
                loss.backward()
                if clip_grad is not None:
                    torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=clip_grad)
                optimizer.step()
                ema.update(model)
                scheduler.step()

            # Evaluate with EMA model
            val_loss, val_acc = evaluate(ema.ema, val_loader, device, criterion)

            if val_acc > best_acc + 1e-5:
                best_acc = val_acc
                best_state = copy.deepcopy(ema.ema.state_dict())
                patience_counter = 0
            else:
                patience_counter += 1
                if patience_counter >= patience:
                    break

        if best_state is not None:
            ema.ema.load_state_dict(best_state)
        ema.ema.eval()
        return ema.ema