import math
import random
import copy
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim


def set_seed(seed: int = 42):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)


def count_trainable_params(model: nn.Module) -> int:
    return sum(p.numel() for p in model.parameters() if p.requires_grad)


class PreNormResidualBlock(nn.Module):
    def __init__(self, dim: int, dropout: float = 0.15):
        super().__init__()
        self.ln1 = nn.LayerNorm(dim)
        self.fc1 = nn.Linear(dim, dim)
        self.ln2 = nn.LayerNorm(dim)
        self.fc2 = nn.Linear(dim, dim)
        self.act = nn.GELU()
        self.drop = nn.Dropout(dropout)

    def forward(self, x):
        y = self.act(self.ln1(x))
        y = self.fc1(y)
        y = self.drop(y)
        y = self.act(self.ln2(y))
        y = self.fc2(y)
        y = self.drop(y)
        return x + y


class ResMLP(nn.Module):
    def __init__(self, input_dim: int, num_classes: int, width: int, num_blocks: int, dropout: float = 0.15):
        super().__init__()
        self.ln_in = nn.LayerNorm(input_dim)
        self.fc_in = nn.Linear(input_dim, width)
        self.act = nn.GELU()
        self.drop = nn.Dropout(dropout)
        self.blocks = nn.ModuleList([PreNormResidualBlock(width, dropout) for _ in range(num_blocks)])
        self.ln_out = nn.LayerNorm(width)
        self.fc_out = nn.Linear(width, num_classes)

    def forward(self, x):
        x = self.ln_in(x)
        x = self.fc_in(x)
        x = self.act(x)
        x = self.drop(x)
        for blk in self.blocks:
            x = blk(x)
        x = self.act(self.ln_out(x))
        x = self.fc_out(x)
        return x


def estimate_params(input_dim: int, num_classes: int, width: int, num_blocks: int) -> int:
    # Linear layers
    head = input_dim * width + width
    blocks = 2 * num_blocks * (width * width + width)
    out = width * num_classes + num_classes
    # LayerNorms: ln_in (2*input_dim), per block 2*width each, ln_out (2*width)
    ln_params = 2 * input_dim + (2 * num_blocks + 1) * (2 * width)
    return head + blocks + out + ln_params


def select_architecture(input_dim: int, num_classes: int, param_limit: int):
    # Prefer deeper (num_blocks=2) if possible, otherwise fallback to 1 block.
    preferred_blocks = [2, 1]
    max_width_start = input_dim  # start from input size
    for nb in preferred_blocks:
        for w in range(max_width_start, 64, -1):
            if estimate_params(input_dim, num_classes, w, nb) <= param_limit:
                return w, nb
    # Fallback: simplest model with minimal width if somehow not found
    return max(64, min(256, input_dim)), 1


def evaluate_accuracy(model: nn.Module, data_loader, device: torch.device) -> float:
    model.eval()
    correct = 0
    total = 0
    with torch.no_grad():
        for inputs, targets in data_loader:
            inputs = inputs.to(device=device, non_blocking=False).float()
            targets = targets.to(device=device, non_blocking=False).long()
            outputs = model(inputs)
            preds = outputs.argmax(dim=1)
            correct += (preds == targets).sum().item()
            total += targets.numel()
    return (correct / total) if total > 0 else 0.0


class Solution:
    def solve(self, train_loader, val_loader, metadata: dict = None) -> torch.nn.Module:
        set_seed(1337)
        device = torch.device(metadata.get("device", "cpu") if metadata is not None else "cpu")
        input_dim = int(metadata.get("input_dim", 384)) if metadata is not None else 384
        num_classes = int(metadata.get("num_classes", 128)) if metadata is not None else 128
        param_limit = int(metadata.get("param_limit", 500_000)) if metadata is not None else 500_000

        width, num_blocks = select_architecture(input_dim, num_classes, param_limit)
        model = ResMLP(input_dim=input_dim, num_classes=num_classes, width=width, num_blocks=num_blocks, dropout=0.15)
        model.to(device)

        # Ensure parameter constraint
        if count_trainable_params(model) > param_limit:
            # Fallback to a smaller width
            width = max(64, width - 8)
            while width >= 64 and estimate_params(input_dim, num_classes, width, num_blocks) > param_limit:
                width -= 8
            if width < 64:
                # Absolute minimal fallback: single hidden layer
                hidden = 256
                model = nn.Sequential(
                    nn.LayerNorm(input_dim),
                    nn.Linear(input_dim, hidden),
                    nn.GELU(),
                    nn.Dropout(0.1),
                    nn.LayerNorm(hidden),
                    nn.Linear(hidden, num_classes),
                )
            else:
                model = ResMLP(input_dim=input_dim, num_classes=num_classes, width=width, num_blocks=num_blocks, dropout=0.15)
            model.to(device)

        # Optimizer and training setup
        base_lr = 0.003
        weight_decay = 5e-4
        optimizer = optim.AdamW(model.parameters(), lr=base_lr, weight_decay=weight_decay)
        scheduler = optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=180, eta_min=base_lr * 0.05)

        try:
            criterion = nn.CrossEntropyLoss(label_smoothing=0.1)
        except TypeError:
            criterion = nn.CrossEntropyLoss()

        max_epochs = 180
        patience = 30
        best_val_acc = -1.0
        best_state = None
        epochs_no_improve = 0

        for epoch in range(max_epochs):
            model.train()
            for inputs, targets in train_loader:
                inputs = inputs.to(device=device, non_blocking=False).float()
                targets = targets.to(device=device, non_blocking=False).long()

                optimizer.zero_grad()
                outputs = model(inputs)
                loss = criterion(outputs, targets)
                loss.backward()
                torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
                optimizer.step()

            scheduler.step()

            # Validation
            val_acc = evaluate_accuracy(model, val_loader, device)
            if val_acc > best_val_acc + 1e-5:
                best_val_acc = val_acc
                best_state = copy.deepcopy(model.state_dict())
                epochs_no_improve = 0
            else:
                epochs_no_improve += 1

            if epochs_no_improve >= patience:
                break

        if best_state is not None:
            model.load_state_dict(best_state)

        model.to(device)
        model.eval()
        return model