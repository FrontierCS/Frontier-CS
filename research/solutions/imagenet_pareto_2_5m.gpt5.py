import math
import copy
import random
from typing import Dict, Tuple

import torch
import torch.nn as nn
import torch.optim as optim


def set_seed(seed: int = 42):
    random.seed(seed)
    torch.manual_seed(seed)


def count_parameters(model: nn.Module) -> int:
    return sum(p.numel() for p in model.parameters() if p.requires_grad)


class ResidualBottleneckBlock(nn.Module):
    def __init__(self, width: int, hidden: int, dropout: float = 0.2):
        super().__init__()
        self.ln = nn.LayerNorm(width)
        self.fc1 = nn.Linear(width, hidden)
        self.act = nn.SiLU()
        self.drop1 = nn.Dropout(dropout)
        self.fc2 = nn.Linear(hidden, width)
        self.drop2 = nn.Dropout(dropout)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        y = self.ln(x)
        y = self.fc1(y)
        y = self.act(y)
        y = self.drop1(y)
        y = self.fc2(y)
        y = self.drop2(y)
        return x + y


class MLPResNet(nn.Module):
    def __init__(self, input_dim: int, num_classes: int, width: int, n_blocks: int, bottleneck_ratio: float, dropout: float = 0.2):
        super().__init__()
        hidden = max(8, int(round(width * bottleneck_ratio)))
        self.ln_in = nn.LayerNorm(input_dim)
        self.fc_in = nn.Linear(input_dim, width)
        self.blocks = nn.ModuleList([ResidualBottleneckBlock(width, hidden, dropout=dropout) for _ in range(n_blocks)])
        self.ln_out = nn.LayerNorm(width)
        self.drop_out = nn.Dropout(dropout * 0.5)
        self.fc_out = nn.Linear(width, num_classes)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self.ln_in(x)
        x = self.fc_in(x)
        for blk in self.blocks:
            x = blk(x)
        x = self.ln_out(x)
        x = self.drop_out(x)
        x = self.fc_out(x)
        return x


def estimate_params(input_dim: int, num_classes: int, width: int, n_blocks: int, bottleneck_ratio: float) -> int:
    hidden = max(8, int(round(width * bottleneck_ratio)))
    p_in = input_dim * width + width
    p_out = width * num_classes + num_classes
    p_ln_in = 2 * input_dim
    p_ln_out = 2 * width
    p_blocks = 0
    for _ in range(n_blocks):
        p_fc = width * hidden + hidden + hidden * width + width
        p_ln = 2 * width
        p_blocks += p_fc + p_ln
    return p_in + p_out + p_ln_in + p_ln_out + p_blocks


def choose_architecture(input_dim: int, num_classes: int, param_limit: int) -> Tuple[int, int, float]:
    # Search for the heaviest architecture under the parameter limit
    best = None
    best_params = -1
    # Candidate search space
    width_candidates = list(range(1408, 480, -64))
    block_candidates = [4, 3, 2]
    ratio_candidates = [0.50, 0.45, 0.40, 0.375, 0.333, 0.30, 0.27, 0.25]

    for n_blocks in block_candidates:
        for width in width_candidates:
            for ratio in ratio_candidates:
                total = estimate_params(input_dim, num_classes, width, n_blocks, ratio)
                if total <= param_limit and total > best_params:
                    best_params = total
                    best = (width, n_blocks, ratio)
    # Fallback: simple model if nothing found
    if best is None:
        # Default to a compact but capable configuration
        width, n_blocks, ratio = 768, 2, 0.5
        return width, n_blocks, ratio
    return best


class WarmupCosineScheduler(optim.lr_scheduler.LambdaLR):
    def __init__(self, optimizer, total_steps: int, warmup_steps: int, min_lr_scale: float = 0.05, last_epoch: int = -1):
        self.total_steps = max(1, total_steps)
        self.warmup_steps = max(1, warmup_steps)
        self.min_lr_scale = min_lr_scale

        def lr_lambda(current_step: int):
            if current_step < self.warmup_steps:
                return float(current_step) / float(max(1, self.warmup_steps))
            progress = float(current_step - self.warmup_steps) / float(max(1, self.total_steps - self.warmup_steps))
            cosine = 0.5 * (1.0 + math.cos(math.pi * progress))
            return self.min_lr_scale + (1.0 - self.min_lr_scale) * cosine

        super().__init__(optimizer, lr_lambda, last_epoch=last_epoch)


def evaluate(model: nn.Module, loader, device: str) -> Tuple[float, float]:
    model.eval()
    correct = 0
    total = 0
    loss_sum = 0.0
    criterion = nn.CrossEntropyLoss()
    with torch.no_grad():
        for inputs, targets in loader:
            inputs = inputs.to(device=device, dtype=torch.float32, non_blocking=False)
            targets = targets.to(device=device, non_blocking=False)
            outputs = model(inputs)
            loss = criterion(outputs, targets)
            loss_sum += loss.item() * targets.numel()
            preds = outputs.argmax(dim=1)
            correct += (preds == targets).sum().item()
            total += targets.numel()
    acc = correct / max(1, total)
    avg_loss = loss_sum / max(1, total)
    return acc, avg_loss


class Solution:
    def solve(self, train_loader, val_loader, metadata: dict = None) -> torch.nn.Module:
        set_seed(42)

        if metadata is None:
            metadata = {}
        input_dim = int(metadata.get("input_dim", 384))
        num_classes = int(metadata.get("num_classes", 128))
        param_limit = int(metadata.get("param_limit", 2_500_000))
        device = str(metadata.get("device", "cpu"))

        width, n_blocks, ratio = choose_architecture(input_dim, num_classes, param_limit)
        # Build model
        model = MLPResNet(input_dim, num_classes, width=width, n_blocks=n_blocks, bottleneck_ratio=ratio, dropout=0.2)
        current_params = count_parameters(model)
        if current_params > param_limit:
            # Safe fallback if anything went wrong
            width, n_blocks, ratio = 768, 2, 0.5
            model = MLPResNet(input_dim, num_classes, width=width, n_blocks=n_blocks, bottleneck_ratio=ratio, dropout=0.2)

        model.to(device)
        ema_model = copy.deepcopy(model)
        for p in ema_model.parameters():
            p.requires_grad_(False)
        ema_model.to(device)
        ema_decay = 0.995

        # Optimizer and scheduler
        base_lr = 0.0025
        weight_decay = 0.02
        optimizer = optim.AdamW(model.parameters(), lr=base_lr, weight_decay=weight_decay)

        # Training config
        try:
            steps_per_epoch = len(train_loader)
        except TypeError:
            steps_per_epoch = 100
        epochs = 200
        warmup_ratio = 0.08
        total_steps = max(1, steps_per_epoch * epochs)
        warmup_steps = max(1, int(total_steps * warmup_ratio))
        scheduler = WarmupCosineScheduler(optimizer, total_steps=total_steps, warmup_steps=warmup_steps, min_lr_scale=0.05)

        # Loss
        smoothing = 0.05
        try:
            criterion = nn.CrossEntropyLoss(label_smoothing=smoothing)
        except TypeError:
            # Fallback if label_smoothing unsupported
            criterion = nn.CrossEntropyLoss()

        # Early stopping and best model tracking using EMA model
        if val_loader is None:
            val_loader = train_loader
        best_val_acc = -1.0
        patience = 30
        no_improve = 0
        best_state = None

        global_step = 0
        clip_grad = 1.0

        for epoch in range(epochs):
            model.train()
            for inputs, targets in train_loader:
                inputs = inputs.to(device=device, dtype=torch.float32, non_blocking=False)
                targets = targets.to(device=device, non_blocking=False)

                optimizer.zero_grad(set_to_none=True)
                outputs = model(inputs)
                loss = criterion(outputs, targets)
                loss.backward()
                if clip_grad is not None and clip_grad > 0:
                    torch.nn.utils.clip_grad_norm_(model.parameters(), clip_grad)
                optimizer.step()

                # EMA update
                with torch.no_grad():
                    ms = model.state_dict()
                    for k, v in ema_model.state_dict().items():
                        if k in ms:
                            v.copy_(v * ema_decay + ms[k] * (1.0 - ema_decay))
                scheduler.step()
                global_step += 1

            # Validation with EMA model
            val_acc, _ = evaluate(ema_model, val_loader, device)
            if val_acc > best_val_acc:
                best_val_acc = val_acc
                best_state = copy.deepcopy(ema_model.state_dict())
                no_improve = 0
            else:
                no_improve += 1
            if no_improve >= patience:
                break

        if best_state is not None:
            ema_model.load_state_dict(best_state)
        ema_model.eval()
        # Ensure parameter limit
        if count_parameters(ema_model) > param_limit:
            # As a last guard, shrink to a safe baseline minimal model
            safe_model = nn.Sequential(
                nn.LayerNorm(input_dim),
                nn.Linear(input_dim, 768),
                nn.SiLU(),
                nn.Dropout(0.2),
                nn.Linear(768, 384),
                nn.SiLU(),
                nn.Dropout(0.2),
                nn.Linear(384, num_classes),
            )
            return safe_model.cpu()
        return ema_model.cpu()
