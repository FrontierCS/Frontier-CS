import math
import copy
import torch
import torch.nn as nn
import torch.nn.functional as F


def set_seed(seed: int = 42):
    torch.manual_seed(seed)
    import random
    random.seed(seed)
    import numpy as np
    np.random.seed(seed)


def count_params_model(model: nn.Module) -> int:
    return sum(p.numel() for p in model.parameters() if p.requires_grad)


def compute_param_count(in_dim: int, h1: int, h2: int, num_classes: int, bn_in: bool) -> int:
    # Linear layers
    p = 0
    p += in_dim * h1 + h1
    p += h1 * h2 + h2
    p += h2 * num_classes + num_classes
    # BatchNorm parameters (weight + bias only; running stats are buffers)
    p += 2 * h1
    p += 2 * h2
    if bn_in:
        p += 2 * in_dim
    return p


class InputStandardizer(nn.Module):
    def __init__(self, mean: torch.Tensor, std: torch.Tensor):
        super().__init__()
        self.register_buffer("mean", mean.float())
        self.register_buffer("std", std.float())

    def forward(self, x):
        return (x - self.mean) / (self.std + 1e-6)


class ResidualMLP(nn.Module):
    def __init__(self, in_dim: int, h1: int, h2: int, num_classes: int, bn_in: bool = False, dropout: float = 0.15):
        super().__init__()
        self.bn_in = nn.BatchNorm1d(in_dim) if bn_in else nn.Identity()
        self.fc1 = nn.Linear(in_dim, h1)
        self.bn1 = nn.BatchNorm1d(h1)

        self.fc2 = nn.Linear(h1, h2)
        self.bn2 = nn.BatchNorm1d(h2)

        self.act = nn.GELU()
        self.drop = nn.Dropout(dropout)
        self.out = nn.Linear(h2, num_classes)
        self.residual_same_dim = (h1 == h2)

        # Initialize weights
        for m in self.modules():
            if isinstance(m, nn.Linear):
                nn.init.kaiming_normal_(m.weight, nonlinearity='relu')
                if m.bias is not None:
                    nn.init.zeros_(m.bias)
            elif isinstance(m, nn.BatchNorm1d):
                nn.init.ones_(m.weight)
                nn.init.zeros_(m.bias)

    def forward(self, x):
        x = self.bn_in(x)
        x = self.fc1(x)
        x = self.bn1(x)
        x = self.act(x)
        x = self.drop(x)

        y = self.fc2(x)
        y = self.bn2(y)
        y = self.act(y)
        y = self.drop(y)

        if self.residual_same_dim:
            x = x + y
            x = self.act(x)
            x = self.drop(x)
        else:
            x = y

        logits = self.out(x)
        return logits


def evaluate_accuracy(model: nn.Module, data_loader, device: torch.device) -> float:
    model.eval()
    correct = 0
    total = 0
    with torch.no_grad():
        for inputs, targets in data_loader:
            inputs = inputs.to(device, non_blocking=False).float()
            targets = targets.to(device, non_blocking=False).long()
            outputs = model(inputs)
            preds = outputs.argmax(dim=1)
            correct += (preds == targets).sum().item()
            total += targets.numel()
    return correct / total if total > 0 else 0.0


def compute_dataset_stats(loader, input_dim: int, device: torch.device):
    total = 0
    sum_ = torch.zeros(input_dim, dtype=torch.float64)
    sum_sq = torch.zeros(input_dim, dtype=torch.float64)
    with torch.no_grad():
        for inputs, _ in loader:
            x = inputs.to(device).double()
            sum_ += x.sum(dim=0).cpu()
            sum_sq += (x * x).sum(dim=0).cpu()
            total += x.shape[0]
    if total == 0:
        mean = torch.zeros(input_dim)
        std = torch.ones(input_dim)
    else:
        mean = (sum_ / total).float()
        var = (sum_sq / total).float() - mean.pow(2)
        var = torch.clamp(var, min=1e-6)
        std = var.sqrt()
    return mean, std


class Solution:
    def solve(self, train_loader, val_loader, metadata: dict = None) -> torch.nn.Module:
        set_seed(42)
        device = torch.device(metadata.get("device", "cpu") if metadata is not None else "cpu")
        input_dim = int(metadata.get("input_dim", 384))
        num_classes = int(metadata.get("num_classes", 128))
        param_limit = int(metadata.get("param_limit", 200_000))

        # Compute input normalization from training data
        mean, std = compute_dataset_stats(train_loader, input_dim, device=torch.device("cpu"))
        preproc = InputStandardizer(mean, std)

        # Search best architecture within parameter limit
        best_cfg = None
        best_params = -1
        for h1 in range(320, 63, -8):
            for h2 in range(320, 63, -8):
                # Prefer with input BN if fits
                for bn_in in (True, False):
                    pcount = compute_param_count(input_dim, h1, h2, num_classes, bn_in)
                    if pcount <= param_limit:
                        key = (pcount, int(h1 == h2), h1 + h2)  # tie-breakers: more params, residual, larger dims
                        if pcount > best_params or (best_cfg is not None and key > (best_params, int(best_cfg[2]==best_cfg[1]), best_cfg[1]+best_cfg[2])):
                            best_params = pcount
                            best_cfg = (bn_in, h1, h2)
                # Early exit if can't improve beyond limit (quick heuristic)
                if best_params == param_limit:
                    break
            if best_params == param_limit:
                break

        if best_cfg is None:
            # Fallback safe small model
            h1, h2, bn_in_flag = 192, 192, False
        else:
            bn_in_flag, h1, h2 = best_cfg

        model = nn.Sequential(preproc, ResidualMLP(input_dim, h1, h2, num_classes, bn_in=bn_in_flag, dropout=0.15))
        model.to(device)

        # Verify parameter limit
        param_count = count_params_model(model)
        if param_count > param_limit:
            # Safety fallback: reduce dims
            h1, h2, bn_in_flag = 192, 192, False
            model = nn.Sequential(preproc, ResidualMLP(input_dim, h1, h2, num_classes, bn_in=bn_in_flag, dropout=0.15))
            model.to(device)
            param_count = count_params_model(model)

        # Training setup
        epochs = 0
        try:
            steps_per_epoch = max(1, len(train_loader))
        except TypeError:
            steps_per_epoch = 64
        target_total_steps = 7000
        epochs = int(min(320, max(150, math.ceil(target_total_steps / steps_per_epoch))))
        # Fit within time constraints on CPU
        epochs = max(epochs, 150)
        epochs = min(epochs, 300)

        optimizer = torch.optim.AdamW(model.parameters(), lr=0.0045, weight_decay=0.01)
        scheduler = torch.optim.lr_scheduler.OneCycleLR(
            optimizer,
            max_lr=0.0045,
            steps_per_epoch=steps_per_epoch,
            epochs=epochs,
            pct_start=0.15,
            anneal_strategy='cos',
            div_factor=10.0,
            final_div_factor=100.0,
            three_phase=False
        )
        criterion = nn.CrossEntropyLoss(label_smoothing=0.1)

        # Early stopping parameters
        best_state = copy.deepcopy(model.state_dict())
        best_val_acc = -1.0
        patience = 30
        no_improve = 0

        for epoch in range(epochs):
            model.train()
            for inputs, targets in train_loader:
                inputs = inputs.to(device, non_blocking=False).float()
                targets = targets.to(device, non_blocking=False).long()

                optimizer.zero_grad(set_to_none=True)
                outputs = model(inputs)
                loss = criterion(outputs, targets)
                loss.backward()
                nn.utils.clip_grad_norm_(model.parameters(), 5.0)
                optimizer.step()
                scheduler.step()

            # Validation
            current_val_acc = evaluate_accuracy(model, val_loader, device) if val_loader is not None else 0.0

            if current_val_acc > best_val_acc + 1e-6:
                best_val_acc = current_val_acc
                best_state = copy.deepcopy(model.state_dict())
                no_improve = 0
            else:
                no_improve += 1

            if no_improve >= patience:
                break

        model.load_state_dict(best_state)
        model.eval()
        return model
