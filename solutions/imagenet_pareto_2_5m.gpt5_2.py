import math
import random
import time
from typing import Optional

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F


def set_seed(seed: int = 1337):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)


class ResidualLinear(nn.Module):
    def __init__(self, dim: int, dropout: float = 0.05):
        super().__init__()
        self.ln = nn.LayerNorm(dim)
        self.fc = nn.Linear(dim, dim)
        self.act = nn.SiLU()
        self.dropout = nn.Dropout(dropout)
        # Initialize residual branch to small values for stability
        nn.init.trunc_normal_(self.fc.weight, std=0.02)
        nn.init.zeros_(self.fc.bias)

    def forward(self, x):
        y = self.ln(x)
        y = self.act(y)
        y = self.fc(y)
        y = self.dropout(y)
        return x + y


class ResidualMLP(nn.Module):
    def __init__(self, input_dim: int, num_classes: int, hidden_dim: int = 992, depth: int = 2, dropout: float = 0.05):
        super().__init__()
        self.input_ln = nn.LayerNorm(input_dim)
        self.fc_in = nn.Linear(input_dim, hidden_dim)
        self.blocks = nn.ModuleList([ResidualLinear(hidden_dim, dropout=dropout) for _ in range(depth)])
        self.out_ln = nn.LayerNorm(hidden_dim)
        self.act = nn.SiLU()
        self.dropout = nn.Dropout(dropout)
        self.fc_out = nn.Linear(hidden_dim, num_classes)

        nn.init.kaiming_uniform_(self.fc_in.weight, a=math.sqrt(5))
        nn.init.zeros_(self.fc_in.bias)
        nn.init.kaiming_uniform_(self.fc_out.weight, a=math.sqrt(5))
        nn.init.zeros_(self.fc_out.bias)

    def forward(self, x):
        x = self.input_ln(x)
        x = self.fc_in(x)
        for blk in self.blocks:
            x = blk(x)
        x = self.out_ln(x)
        x = self.act(x)
        x = self.dropout(x)
        x = self.fc_out(x)
        return x


class EMA:
    def __init__(self, model: nn.Module, decay: float = 0.999):
        self.decay = decay
        self.shadow = {}
        self.backup = {}
        for name, param in model.named_parameters():
            if param.requires_grad:
                self.shadow[name] = param.data.clone()

    @torch.no_grad()
    def update(self, model: nn.Module):
        for name, param in model.named_parameters():
            if param.requires_grad:
                assert name in self.shadow
                new_average = self.decay * self.shadow[name] + (1.0 - self.decay) * param.data
                self.shadow[name] = new_average.clone()

    def store(self, model: nn.Module):
        self.backup = {}
        for name, param in model.named_parameters():
            if param.requires_grad:
                self.backup[name] = param.data.clone()

    @torch.no_grad()
    def copy_to(self, model: nn.Module):
        for name, param in model.named_parameters():
            if param.requires_grad and name in self.shadow:
                param.data.copy_(self.shadow[name])

    @torch.no_grad()
    def restore(self, model: nn.Module):
        for name, param in model.named_parameters():
            if param.requires_grad and name in self.backup:
                param.data.copy_(self.backup[name])
        self.backup = {}


def count_trainable_params(model: nn.Module) -> int:
    return sum(p.numel() for p in model.parameters() if p.requires_grad)


def cosine_lr(step: int, total_steps: int, base_lr: float, warmup_steps: int = 0, min_lr_ratio: float = 0.1) -> float:
    if step < warmup_steps:
        return base_lr * step / max(1, warmup_steps)
    t = (step - warmup_steps) / max(1, total_steps - warmup_steps)
    cosine = 0.5 * (1 + math.cos(math.pi * t))
    return min_lr_ratio * base_lr + cosine * (base_lr - min_lr_ratio * base_lr)


@torch.no_grad()
def evaluate(model: nn.Module, loader, device: str) -> (float, float):
    model.eval()
    total = 0
    correct = 0
    total_loss = 0.0
    criterion = nn.CrossEntropyLoss()
    for inputs, targets in loader:
        inputs = inputs.to(device, non_blocking=False)
        targets = targets.to(device, non_blocking=False)
        outputs = model(inputs)
        loss = criterion(outputs, targets)
        total_loss += loss.item() * targets.numel()
        preds = outputs.argmax(dim=1)
        correct += (preds == targets).sum().item()
        total += targets.numel()
    acc = correct / max(1, total)
    avg_loss = total_loss / max(1, total)
    return acc, avg_loss


class Solution:
    def solve(self, train_loader, val_loader, metadata: dict = None) -> torch.nn.Module:
        set_seed(42 + int(time.time()) % 1000)

        if metadata is None:
            metadata = {}
        input_dim = int(metadata.get("input_dim", 384))
        num_classes = int(metadata.get("num_classes", 128))
        param_limit = int(metadata.get("param_limit", 2_500_000))
        device = str(metadata.get("device", "cpu"))

        # Hyperparameters
        base_hidden = 992  # near-max within budget for depth=2 residual single-linear blocks
        depth = 2
        dropout = 0.05
        lr = 3e-3
        weight_decay = 1e-4
        label_smoothing = 0.05
        max_epochs = 180
        warmup_epochs = 5
        ema_decay = 0.999
        grad_clip = 1.0
        patience = 30

        # Build model within parameter budget
        hidden_dim = base_hidden
        model = ResidualMLP(input_dim, num_classes, hidden_dim=hidden_dim, depth=depth, dropout=dropout)
        params = count_trainable_params(model)
        while params > param_limit and hidden_dim > 128:
            hidden_dim -= 8
            model = ResidualMLP(input_dim, num_classes, hidden_dim=hidden_dim, depth=depth, dropout=dropout)
            params = count_trainable_params(model)

        # Final safety check: if still exceeding, reduce depth as last resort
        if params > param_limit and depth > 1:
            depth = 1
            model = ResidualMLP(input_dim, num_classes, hidden_dim=hidden_dim, depth=depth, dropout=dropout)
            params = count_trainable_params(model)
            while params > param_limit and hidden_dim > 128:
                hidden_dim -= 8
                model = ResidualMLP(input_dim, num_classes, hidden_dim=hidden_dim, depth=depth, dropout=dropout)
                params = count_trainable_params(model)

        model.to(device)

        optimizer = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=weight_decay, betas=(0.9, 0.95))
        criterion = nn.CrossEntropyLoss(label_smoothing=label_smoothing)
        train_steps_per_epoch = max(1, len(train_loader))
        total_steps = max_epochs * train_steps_per_epoch
        warmup_steps = warmup_epochs * train_steps_per_epoch

        ema = EMA(model, decay=ema_decay)

        best_val_acc = -1.0
        best_state: Optional[dict] = None
        best_ema_state: Optional[dict] = None
        epochs_no_improve = 0

        global_step = 0
        for epoch in range(max_epochs):
            model.train()
            running_loss = 0.0
            running_count = 0
            for inputs, targets in train_loader:
                inputs = inputs.to(device, non_blocking=False)
                targets = targets.to(device, non_blocking=False)

                # Adjust LR
                lr_now = cosine_lr(global_step, total_steps, base_lr=lr, warmup_steps=warmup_steps, min_lr_ratio=0.08)
                for pg in optimizer.param_groups:
                    pg["lr"] = lr_now

                optimizer.zero_grad(set_to_none=True)
                outputs = model(inputs)
                loss = criterion(outputs, targets)
                loss.backward()
                if grad_clip is not None:
                    nn.utils.clip_grad_norm_(model.parameters(), grad_clip)
                optimizer.step()
                ema.update(model)

                running_loss += loss.item() * targets.numel()
                running_count += targets.numel()
                global_step += 1

            # Validation with EMA weights
            ema.store(model)
            ema.copy_to(model)
            val_acc, val_loss = evaluate(model, val_loader, device)
            ema.restore(model)

            if val_acc > best_val_acc:
                best_val_acc = val_acc
                best_state = {k: v.cpu().clone() for k, v in model.state_dict().items()}
                best_ema_state = {k: v.clone() for k, v in ema.shadow.items()}
                epochs_no_improve = 0
            else:
                epochs_no_improve += 1

            if epochs_no_improve >= patience:
                break

        # Load best EMA weights into model before returning
        if best_state is not None and best_ema_state is not None:
            model.load_state_dict(best_state)
            for name, param in model.named_parameters():
                if param.requires_grad and name in best_ema_state:
                    param.data.copy_(best_ema_state[name])

        model.eval()
        return model
