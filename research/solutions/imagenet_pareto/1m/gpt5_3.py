import math
import os
import random
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F


def set_seed(seed: int = 42):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)


def count_trainable_params(model: nn.Module) -> int:
    return sum(p.numel() for p in model.parameters() if p.requires_grad)


class MLPNet(nn.Module):
    def __init__(self, input_dim: int, hidden_dim: int, num_classes: int, dropout: float = 0.2):
        super().__init__()
        self.in_ln = nn.LayerNorm(input_dim)
        self.fc1 = nn.Linear(input_dim, hidden_dim)
        self.bn1 = nn.BatchNorm1d(hidden_dim)
        self.fc2 = nn.Linear(hidden_dim, hidden_dim)
        self.bn2 = nn.BatchNorm1d(hidden_dim)
        self.act = nn.GELU()
        self.drop = nn.Dropout(dropout)
        self.fc_out = nn.Linear(hidden_dim, num_classes)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = x.view(x.size(0), -1)
        x = self.in_ln(x)
        x = self.fc1(x)
        x = self.bn1(x)
        x = self.act(x)
        x = self.drop(x)
        x = self.fc2(x)
        x = self.bn2(x)
        x = self.act(x)
        x = self.drop(x)
        x = self.fc_out(x)
        return x


def build_model_within_limit(input_dim: int, num_classes: int, param_limit: int, base_dropout: float = 0.2) -> nn.Module:
    # Analytical width estimate for architecture with:
    # LayerNorm(in_dim): 2*in_dim params, two hidden layers with BN, dropout, GELU
    # Params ~= W^2 + W*(input_dim + num_classes + 6) + num_classes + 2*input_dim
    a = 1.0
    b = float(input_dim + num_classes + 6)
    c = float(num_classes + 2 * input_dim - param_limit)

    disc = b * b - 4 * a * c
    w_est = int(max(2, math.floor((-b + math.sqrt(max(0.0, disc))) / (2 * a))))
    # Clamp to reasonable range
    w = max(64, min(1024, w_est))

    # Adjust to fit within the limit by constructing models
    while w > 0:
        model = MLPNet(input_dim, w, num_classes, dropout=base_dropout)
        params = count_trainable_params(model)
        if params <= param_limit:
            return model
        w -= 1

    # Fallback minimal model if needed
    return MLPNet(input_dim, 128, num_classes, dropout=base_dropout)


def evaluate_accuracy(model: nn.Module, loader, device: torch.device) -> float:
    model.eval()
    correct = 0
    total = 0
    with torch.no_grad():
        for inputs, targets in loader:
            inputs = inputs.to(device, non_blocking=True)
            targets = targets.to(device, non_blocking=True)
            outputs = model(inputs)
            preds = outputs.argmax(dim=1)
            correct += (preds == targets).sum().item()
            total += targets.numel()
    return (correct / total) if total > 0 else 0.0


class Solution:
    def solve(self, train_loader, val_loader, metadata: dict = None) -> torch.nn.Module:
        set_seed(42)

        # Metadata defaults
        if metadata is None:
            metadata = {}
        input_dim = int(metadata.get("input_dim", 384))
        num_classes = int(metadata.get("num_classes", 128))
        param_limit = int(metadata.get("param_limit", 1_000_000))
        device_str = metadata.get("device", "cpu")
        device = torch.device(device_str)

        # Build model maximally within the parameter budget
        model = build_model_within_limit(input_dim, num_classes, param_limit, base_dropout=0.2)
        model.to(device)

        # Safety check: ensure parameter budget is not exceeded
        if count_trainable_params(model) > param_limit:
            # Reduce hidden dim aggressively until under budget
            if isinstance(model, MLPNet):
                hidden = model.fc1.out_features
                while hidden > 32:
                    hidden -= 1
                    reduced = MLPNet(input_dim, hidden, num_classes, dropout=0.2).to(device)
                    if count_trainable_params(reduced) <= param_limit:
                        model = reduced
                        break

        # Training setup
        # AdamW works well for MLPs; weight decay for regularization; label smoothing to reduce overfit
        base_lr = 3e-3
        weight_decay = 1e-2
        max_epochs = 120
        patience = 25
        grad_clip = 1.0
        label_smoothing = 0.1

        optimizer = torch.optim.AdamW(model.parameters(), lr=base_lr, weight_decay=weight_decay)

        # Warmup + Cosine decay scheduler per-epoch
        def lr_lambda(epoch):
            warmup_epochs = max(2, int(0.08 * max_epochs))
            if epoch < warmup_epochs:
                return float(epoch + 1) / float(warmup_epochs)
            # Cosine decay from 1.0 to 0.05
            progress = (epoch - warmup_epochs) / max(1, (max_epochs - warmup_epochs))
            cos_decay = 0.5 * (1.0 + math.cos(math.pi * progress))
            min_factor = 0.05
            return min_factor + (1.0 - min_factor) * cos_decay

        scheduler = torch.optim.lr_scheduler.LambdaLR(optimizer, lr_lambda=lr_lambda)

        best_acc = -1.0
        best_state = None
        epochs_no_improve = 0

        # Training loop
        for epoch in range(max_epochs):
            model.train()
            for inputs, targets in train_loader:
                inputs = inputs.to(device, non_blocking=True)
                targets = targets.to(device, non_blocking=True)

                optimizer.zero_grad(set_to_none=True)
                outputs = model(inputs)
                loss = F.cross_entropy(outputs, targets, label_smoothing=label_smoothing)
                loss.backward()
                if grad_clip is not None and grad_clip > 0:
                    nn.utils.clip_grad_norm_(model.parameters(), grad_clip)
                optimizer.step()

            scheduler.step()

            # Validation
            val_acc = evaluate_accuracy(model, val_loader, device)

            if val_acc > best_acc:
                best_acc = val_acc
                best_state = {k: v.cpu().clone() for k, v in model.state_dict().items()}
                epochs_no_improve = 0
            else:
                epochs_no_improve += 1
                if epochs_no_improve >= patience:
                    break

        # Load best state dict
        if best_state is not None:
            model.load_state_dict(best_state, strict=True)
        model.to("cpu")
        model.eval()
        return model