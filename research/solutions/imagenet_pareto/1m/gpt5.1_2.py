import torch
import torch.nn as nn
import torch.nn.functional as F
import random
import numpy as np
import math
import copy
from typing import Dict, Optional


def set_seed(seed: int = 42):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)


def count_parameters(model: nn.Module) -> int:
    return sum(p.numel() for p in model.parameters() if p.requires_grad)


def evaluate(model: nn.Module, data_loader, criterion, device: torch.device):
    model.eval()
    total_loss = 0.0
    total_samples = 0
    correct = 0
    with torch.no_grad():
        for inputs, targets in data_loader:
            inputs = inputs.to(device)
            targets = targets.to(device)

            outputs = model(inputs)
            loss = criterion(outputs, targets)

            batch_size = targets.size(0)
            total_loss += loss.item() * batch_size
            total_samples += batch_size

            preds = outputs.argmax(dim=1)
            correct += (preds == targets).sum().item()

    if total_samples == 0:
        return 0.0, 0.0
    avg_loss = total_loss / total_samples
    accuracy = correct / total_samples
    return avg_loss, accuracy


class MLPBlock(nn.Module):
    def __init__(self, in_dim: int, out_dim: int, dropout: float = 0.1, residual: bool = False):
        super().__init__()
        self.fc = nn.Linear(in_dim, out_dim)
        self.bn = nn.BatchNorm1d(out_dim)
        self.act = nn.GELU()
        self.dropout = nn.Dropout(dropout)
        self.residual = residual and (in_dim == out_dim)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        out = self.fc(x)
        out = self.bn(out)
        out = self.act(out)
        out = self.dropout(out)
        if self.residual:
            out = out + x
        return out


class MLPNet(nn.Module):
    def __init__(self, input_dim: int, num_classes: int, hidden_dim: int = 576, num_blocks: int = 3,
                 dropout: float = 0.1):
        super().__init__()
        self.input_bn = nn.BatchNorm1d(input_dim)
        blocks = []
        in_dim = input_dim
        for i in range(num_blocks):
            use_residual = i > 0 and in_dim == hidden_dim
            blocks.append(MLPBlock(in_dim, hidden_dim, dropout=dropout, residual=use_residual))
            in_dim = hidden_dim
        self.blocks = nn.Sequential(*blocks)
        self.classifier = nn.Linear(hidden_dim, num_classes)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self.input_bn(x)
        x = self.blocks(x)
        x = self.classifier(x)
        return x


class Solution:
    def _build_model(self, input_dim: int, num_classes: int, param_limit: int) -> nn.Module:
        # Try larger hidden sizes first while respecting the parameter limit
        candidate_hidden_dims = [1024, 896, 768, 640, 576, 512, 448, 384, 320, 256, 192, 128, 64, 32]
        num_blocks = 3
        dropout = 0.1

        for h in candidate_hidden_dims:
            model = MLPNet(input_dim=input_dim,
                           num_classes=num_classes,
                           hidden_dim=h,
                           num_blocks=num_blocks,
                           dropout=dropout)
            params = count_parameters(model)
            if params <= param_limit:
                return model

        # Fallback very small model if param_limit is extremely tiny
        return nn.Linear(input_dim, num_classes)

    def solve(self, train_loader, val_loader, metadata: dict = None) -> torch.nn.Module:
        if metadata is None:
            metadata = {}

        set_seed(42)

        input_dim = int(metadata.get("input_dim", 384))
        num_classes = int(metadata.get("num_classes", 128))
        param_limit = int(metadata.get("param_limit", 1_000_000))
        device_str = metadata.get("device", "cpu")
        device = torch.device(device_str)

        model = self._build_model(input_dim, num_classes, param_limit)
        model.to(device)

        # Ensure we are under the parameter limit
        assert count_parameters(model) <= param_limit

        criterion = nn.CrossEntropyLoss()
        optimizer = torch.optim.AdamW(model.parameters(), lr=1e-3, weight_decay=1e-4)

        max_epochs = 200
        patience = 25
        use_validation = val_loader is not None

        scheduler = None
        if use_validation:
            scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
                optimizer,
                mode="max",
                factor=0.5,
                patience=5,
                verbose=False,
                min_lr=1e-5,
            )

        best_state = copy.deepcopy(model.state_dict())
        best_val_acc = -float("inf")
        epochs_no_improve = 0

        for epoch in range(max_epochs):
            model.train()
            for inputs, targets in train_loader:
                inputs = inputs.to(device)
                targets = targets.to(device)

                optimizer.zero_grad()
                outputs = model(inputs)
                loss = criterion(outputs, targets)
                loss.backward()
                optimizer.step()

            if use_validation:
                val_loss, val_acc = evaluate(model, val_loader, criterion, device)
                if scheduler is not None:
                    scheduler.step(val_acc)

                if val_acc > best_val_acc:
                    best_val_acc = val_acc
                    best_state = copy.deepcopy(model.state_dict())
                    epochs_no_improve = 0
                else:
                    epochs_no_improve += 1

                if epochs_no_improve >= patience:
                    break

        if use_validation:
            model.load_state_dict(best_state)

        model.to(device)
        model.eval()
        return model