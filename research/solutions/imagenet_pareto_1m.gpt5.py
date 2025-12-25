import math
import copy
import random
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F


class InputNorm(nn.Module):
    def __init__(self, mean, std, eps=1e-6):
        super().__init__()
        self.register_buffer("mean", mean.clone().detach())
        self.register_buffer("std", std.clone().detach())
        self.eps = eps

    def forward(self, x):
        return (x - self.mean) / (self.std + self.eps)


class ResBlock1Linear(nn.Module):
    def __init__(self, dim, dropout=0.0, layerscale_init=1e-3):
        super().__init__()
        self.ln = nn.LayerNorm(dim)
        self.fc = nn.Linear(dim, dim)
        self.act = nn.GELU()
        self.drop = nn.Dropout(dropout) if dropout and dropout > 0.0 else nn.Identity()
        self.gamma = nn.Parameter(torch.ones(dim) * layerscale_init)

    def forward(self, x):
        y = self.ln(x)
        y = self.act(y)
        y = self.fc(y)
        y = y * self.gamma
        y = self.drop(y)
        return x + y


class ResidualMLP(nn.Module):
    def __init__(self, input_dim, num_classes, width, num_blocks, dropout=0.0, layerscale_init=1e-3, input_norm=None):
        super().__init__()
        self.use_input_proj = width != input_dim
        self.input_norm = input_norm
        if self.use_input_proj:
            self.in_proj = nn.Linear(input_dim, width)
        else:
            self.in_proj = nn.Identity()
        blocks = []
        for _ in range(num_blocks):
            blocks.append(ResBlock1Linear(width, dropout=dropout, layerscale_init=layerscale_init))
        self.blocks = nn.Sequential(*blocks)
        self.pre_head_ln = nn.LayerNorm(width)
        self.head = nn.Linear(width, num_classes)

    def forward(self, x):
        if self.input_norm is not None:
            x = self.input_norm(x)
        x = self.in_proj(x)
        x = self.blocks(x)
        x = self.pre_head_ln(x)
        x = self.head(x)
        return x


def count_params(model: nn.Module):
    return sum(p.numel() for p in model.parameters() if p.requires_grad)


def set_seed(seed: int = 1337):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)


def compute_dataset_mean_std(train_loader, device):
    # Compute per-feature mean and std
    total = 0
    mean = None
    m2 = None
    for x, _ in train_loader:
        x = x.to(device=device, dtype=torch.float32)
        if mean is None:
            mean = torch.zeros(x.shape[1], device=device, dtype=torch.float32)
            m2 = torch.zeros(x.shape[1], device=device, dtype=torch.float32)
        batch_n = x.shape[0]
        total_new = total + batch_n
        delta = x.mean(dim=0) - mean
        mean = mean + delta * (batch_n / max(total_new, 1))
        # For variance: accumulate second moment
        # We'll compute using sum of squares
        if total == 0:
            ss = (x - mean).pow(2).sum(dim=0)
        else:
            # recompute ss incrementally is a bit tricky; simpler to accumulate sums
            # So instead, compute sums and sums of squares directly in another pass.
            pass
        total += batch_n
    # Recompute more robustly via two-pass to avoid numerical issues on CPU small costs
    total = 0
    sum_x = None
    sum_x2 = None
    for x, _ in train_loader:
        x = x.to(device=device, dtype=torch.float32)
        if sum_x is None:
            sum_x = x.sum(dim=0)
            sum_x2 = (x.pow(2)).sum(dim=0)
        else:
            sum_x += x.sum(dim=0)
            sum_x2 += (x.pow(2)).sum(dim=0)
        total += x.shape[0]
    mean = sum_x / max(total, 1)
    var = sum_x2 / max(total, 1) - mean.pow(2)
    std = torch.sqrt(torch.clamp(var, min=1e-6))
    return mean.detach(), std.detach()


def evaluate(model, loader, device):
    model.eval()
    correct = 0
    total = 0
    with torch.no_grad():
        for x, y in loader:
            x = x.to(device=device, dtype=torch.float32)
            y = y.to(device=device)
            logits = model(x)
            pred = logits.argmax(dim=1)
            correct += (pred == y).sum().item()
            total += y.numel()
    acc = correct / max(total, 1)
    return acc


class Solution:
    def solve(self, train_loader, val_loader, metadata: dict = None) -> torch.nn.Module:
        set_seed(1337)
        if metadata is None:
            metadata = {}
        input_dim = int(metadata.get("input_dim", 384))
        num_classes = int(metadata.get("num_classes", 128))
        param_limit = int(metadata.get("param_limit", 1_000_000))
        device = metadata.get("device", "cpu")

        # Prepare normalization
        # Compute mean/std on device to avoid extra transfers
        mean, std = compute_dataset_mean_std(train_loader, device=device)
        input_norm = InputNorm(mean, std)

        # Model configuration
        width = input_dim  # keep width equal to input dim for parameter efficiency
        num_blocks = 6
        dropout = 0.0
        layerscale_init = 1e-3

        # Build model under parameter constraint; adjust if necessary
        def build_model(w, nb):
            return ResidualMLP(
                input_dim=input_dim,
                num_classes=num_classes,
                width=w,
                num_blocks=nb,
                dropout=dropout,
                layerscale_init=layerscale_init,
                input_norm=input_norm,
            )

        model = build_model(width, num_blocks)
        model.to(device)
        pcount = count_params(model)
        # Reduce blocks if exceeding limit
        while pcount > param_limit and num_blocks > 1:
            num_blocks -= 1
            model = build_model(width, num_blocks)
            model.to(device)
            pcount = count_params(model)
        # If still exceeding, reduce width (with input projection)
        if pcount > param_limit:
            # Try progressively smaller widths
            for w in [320, 288, 256, 224, 192, 160]:
                model = build_model(w, num_blocks)
                model.to(device)
                pcount = count_params(model)
                if pcount <= param_limit:
                    width = w
                    break
        # Final safety check: ensure under param_limit
        if pcount > param_limit:
            # As a last resort, minimal small MLP
            width = min(192, input_dim)
            num_blocks = max(1, num_blocks // 2)
            model = build_model(width, num_blocks)
            model.to(device)
            pcount = count_params(model)

        # Training setup
        # Loss with label smoothing for better generalization
        criterion = nn.CrossEntropyLoss(label_smoothing=0.05)
        base_lr = 2e-3
        weight_decay = 0.01
        optimizer = torch.optim.AdamW(model.parameters(), lr=base_lr, weight_decay=weight_decay)
        # Scheduler: OneCycle with cosine annealing
        max_epochs = 160
        steps_per_epoch = max(1, len(train_loader))
        scheduler = torch.optim.lr_scheduler.OneCycleLR(
            optimizer,
            max_lr=base_lr,
            epochs=max_epochs,
            steps_per_epoch=steps_per_epoch,
            pct_start=0.2,
            anneal_strategy="cos",
            div_factor=25.0,
            final_div_factor=1000.0,
            cycle_momentum=False,
        )

        # Early stopping
        patience = 30
        best_val_acc = -1.0
        best_state = None
        epochs_no_improve = 0

        # Training loop
        for epoch in range(max_epochs):
            model.train()
            for xb, yb in train_loader:
                xb = xb.to(device=device, dtype=torch.float32)
                yb = yb.to(device=device)
                optimizer.zero_grad(set_to_none=True)
                logits = model(xb)
                loss = criterion(logits, yb)
                loss.backward()
                torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
                optimizer.step()
                scheduler.step()

            # Validation
            if val_loader is not None:
                val_acc = evaluate(model, val_loader, device)
                if val_acc > best_val_acc:
                    best_val_acc = val_acc
                    best_state = copy.deepcopy(model.state_dict())
                    epochs_no_improve = 0
                else:
                    epochs_no_improve += 1
                if epochs_no_improve >= patience:
                    break

        # Load best
        if best_state is not None:
            model.load_state_dict(best_state)
        model.eval()
        return model
