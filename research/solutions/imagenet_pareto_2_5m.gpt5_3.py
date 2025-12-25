import math
import copy
import random
import time
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F


def set_seed(seed: int = 42):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)


def count_parameters(model: nn.Module) -> int:
    return sum(p.numel() for p in model.parameters() if p.requires_grad)


def drop_path(x, drop_prob: float = 0.0, training: bool = False):
    if drop_prob == 0.0 or not training:
        return x
    keep_prob = 1 - drop_prob
    shape = (x.shape[0],) + (1,) * (x.dim() - 1)
    random_tensor = keep_prob + torch.rand(shape, dtype=x.dtype, device=x.device)
    random_tensor.floor_()
    return x.div(keep_prob) * random_tensor


class DropPath(nn.Module):
    def __init__(self, drop_prob: float = 0.0):
        super().__init__()
        self.drop_prob = drop_prob

    def forward(self, x):
        return drop_path(x, self.drop_prob, self.training)


class BottleneckBlock(nn.Module):
    def __init__(self, dim: int, hidden_dim: int, drop: float = 0.1, drop_path_prob: float = 0.0):
        super().__init__()
        self.norm = nn.LayerNorm(dim)
        self.fc1 = nn.Linear(dim, hidden_dim)
        self.act = nn.GELU()
        self.drop1 = nn.Dropout(drop)
        self.fc2 = nn.Linear(hidden_dim, dim)
        self.drop2 = nn.Dropout(drop)
        self.stoch = DropPath(drop_path_prob)

    def forward(self, x):
        y = self.norm(x)
        y = self.fc1(y)
        y = self.act(y)
        y = self.drop1(y)
        y = self.fc2(y)
        y = self.drop2(y)
        return x + self.stoch(y)


class MLPNet(nn.Module):
    def __init__(self, input_dim: int, num_classes: int, width: int, bottleneck: int, num_blocks: int,
                 dropout: float = 0.2, drop_path_rate: float = 0.05):
        super().__init__()
        self.in_norm = nn.LayerNorm(input_dim)
        self.in_proj = nn.Linear(input_dim, width)
        self.in_drop = nn.Dropout(dropout)
        dpr = [x.item() for x in torch.linspace(0, drop_path_rate, steps=num_blocks)]
        self.blocks = nn.ModuleList([
            BottleneckBlock(width, bottleneck, drop=dropout, drop_path_prob=dpr[i]) for i in range(num_blocks)
        ])
        self.out_norm = nn.LayerNorm(width)
        self.head = nn.Linear(width, num_classes)

    def forward(self, x):
        x = self.in_norm(x)
        x = self.in_proj(x)
        x = F.gelu(x)
        x = self.in_drop(x)
        for blk in self.blocks:
            x = blk(x)
        x = self.out_norm(x)
        x = self.head(x)
        return x


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
            if ema_p.data.dtype != p.data.dtype:
                ema_p.data = ema_p.data.to(p.data.dtype)
            ema_p.data.mul_(d).add_(p.data, alpha=1 - d)

    @torch.no_grad()
    def set(self, model: nn.Module):
        for ema_p, p in zip(self.ema.parameters(), model.parameters()):
            ema_p.data.copy_(p.data)


class WarmupCosineLR:
    def __init__(self, optimizer, base_lr, final_lr, total_steps, warmup_steps=0):
        self.optimizer = optimizer
        self.base_lr = base_lr
        self.final_lr = final_lr
        self.total_steps = max(1, total_steps)
        self.warmup_steps = warmup_steps
        self.step_num = 0
        self._set_lr(self.final_lr if self.total_steps == 0 else 0.0)

    def _set_lr(self, lr):
        for param_group in self.optimizer.param_groups:
            param_group['lr'] = lr

    def step(self):
        self.step_num += 1
        if self.step_num <= self.warmup_steps and self.warmup_steps > 0:
            lr = self.base_lr * float(self.step_num) / float(self.warmup_steps)
        else:
            progress = (self.step_num - self.warmup_steps) / max(1, self.total_steps - self.warmup_steps)
            lr = self.final_lr + 0.5 * (self.base_lr - self.final_lr) * (1.0 + math.cos(math.pi * progress))
        self._set_lr(lr)


def evaluate_accuracy(model: nn.Module, data_loader, device: torch.device) -> float:
    model.eval()
    correct = 0
    total = 0
    with torch.no_grad():
        for inputs, targets in data_loader:
            inputs = inputs.to(device, non_blocking=False)
            targets = targets.to(device, non_blocking=False)
            outputs = model(inputs)
            preds = outputs.argmax(dim=1)
            correct += (preds == targets).sum().item()
            total += targets.numel()
    return correct / max(1, total)


class Solution:
    def solve(self, train_loader, val_loader, metadata: dict = None) -> torch.nn.Module:
        set_seed(42)
        device_str = 'cpu'
        if metadata is not None and "device" in metadata:
            device_str = metadata["device"] or 'cpu'
        device = torch.device(device_str)

        input_dim = 384 if metadata is None else int(metadata.get("input_dim", 384))
        num_classes = 128 if metadata is None else int(metadata.get("num_classes", 128))
        param_limit = 2500000 if metadata is None else int(metadata.get("param_limit", 2500000))

        # Candidate architecture configurations (width, bottleneck, blocks)
        candidates = [
            (1152, 272, 3, 0.2, 0.05),
            (1200, 256, 3, 0.2, 0.05),
            (1024, 256, 3, 0.2, 0.05),
            (992, 240, 3, 0.2, 0.05),
            (896, 256, 3, 0.2, 0.05),
        ]

        model = None
        for width, bottleneck, blocks, dropout, drop_path_rate in candidates:
            tmp_model = MLPNet(input_dim, num_classes, width, bottleneck, blocks, dropout=dropout, drop_path_rate=drop_path_rate)
            n_params = count_parameters(tmp_model)
            if n_params <= param_limit:
                model = tmp_model
                break
        if model is None:
            # Fallback minimal model
            width = 768
            bottleneck = 192
            blocks = 2
            model = MLPNet(input_dim, num_classes, width, bottleneck, blocks, dropout=0.1, drop_path_rate=0.0)
            # ensure under limit
            if count_parameters(model) > param_limit:
                model = nn.Sequential(
                    nn.LayerNorm(input_dim),
                    nn.Linear(input_dim, 512),
                    nn.GELU(),
                    nn.Linear(512, num_classes)
                )

        model.to(device)

        # Training hyperparameters
        epochs = 180
        base_lr = 2.5e-3
        final_lr = 5e-5
        weight_decay = 5e-4
        label_smoothing = 0.05
        grad_clip_norm = 1.0
        patience = 30

        optimizer = torch.optim.AdamW(model.parameters(), lr=base_lr, weight_decay=weight_decay)
        criterion = nn.CrossEntropyLoss(label_smoothing=label_smoothing)

        total_steps = epochs * max(1, len(train_loader))
        warmup_steps = int(0.1 * total_steps)
        scheduler = WarmupCosineLR(optimizer, base_lr=base_lr, final_lr=final_lr, total_steps=total_steps, warmup_steps=warmup_steps)

        ema = ModelEMA(model, decay=0.995)

        best_val_acc = -1.0
        best_state = None
        best_ema_state = None
        no_improve = 0

        start_time = time.time()
        max_time_seconds = 3600 * 0.9  # use 90% of the allowed time as a safety margin

        for epoch in range(epochs):
            model.train()
            for inputs, targets in train_loader:
                inputs = inputs.to(device, non_blocking=False)
                targets = targets.to(device, non_blocking=False)

                optimizer.zero_grad(set_to_none=True)
                outputs = model(inputs)
                loss = criterion(outputs, targets)
                loss.backward()
                if grad_clip_norm is not None and grad_clip_norm > 0:
                    nn.utils.clip_grad_norm_(model.parameters(), grad_clip_norm)
                optimizer.step()
                ema.update(model)
                scheduler.step()

            # Evaluate using EMA model for stability
            val_acc = evaluate_accuracy(ema.ema, val_loader, device)
            if val_acc > best_val_acc:
                best_val_acc = val_acc
                no_improve = 0
                best_state = copy.deepcopy(model.state_dict())
                best_ema_state = copy.deepcopy(ema.ema.state_dict())
            else:
                no_improve += 1

            # Early stopping
            if no_improve >= patience:
                break

            # Time safety check
            if (time.time() - start_time) > max_time_seconds:
                break

        # Load best EMA state into EMA model and return
        if best_ema_state is not None:
            ema.ema.load_state_dict(best_ema_state)
        else:
            ema.set(model)

        ema.ema.to(device)
        ema.ema.eval()
        return ema.ema
