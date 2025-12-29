import torch
import torch.nn as nn
import torch.nn.functional as F
import random
import numpy as np
import math


class ResidualBlock(nn.Module):
    def __init__(self, dim, dropout=0.1):
        super().__init__()
        self.fc1 = nn.Linear(dim, dim)
        self.bn1 = nn.BatchNorm1d(dim)
        self.fc2 = nn.Linear(dim, dim)
        self.bn2 = nn.BatchNorm1d(dim)
        self.dropout = nn.Dropout(dropout) if dropout > 0.0 else nn.Identity()
        self.act = nn.ReLU(inplace=True)

    def forward(self, x):
        residual = x
        out = self.fc1(x)
        out = self.bn1(out)
        out = self.act(out)
        out = self.dropout(out)
        out = self.fc2(out)
        out = self.bn2(out)
        out = self.dropout(out)
        out = out + residual
        out = self.act(out)
        return out


class ResidualMLP(nn.Module):
    def __init__(self, input_dim, num_classes, width=1024, num_blocks=2, dropout=0.1):
        super().__init__()
        self.fc_in = nn.Linear(input_dim, width)
        self.bn_in = nn.BatchNorm1d(width)
        blocks = []
        for _ in range(num_blocks):
            blocks.append(ResidualBlock(width, dropout=dropout))
        self.blocks = nn.Sequential(*blocks)
        self.fc_out = nn.Linear(width, num_classes)
        self.act = nn.ReLU(inplace=True)

    def forward(self, x):
        x = self.fc_in(x)
        x = self.bn_in(x)
        x = self.act(x)
        x = self.blocks(x)
        x = self.fc_out(x)
        return x


class Solution:
    def solve(self, train_loader, val_loader, metadata: dict = None) -> torch.nn.Module:
        if metadata is None:
            metadata = {}
        device = torch.device(metadata.get("device", "cpu"))

        # Reproducibility
        seed = 42
        random.seed(seed)
        np.random.seed(seed)
        torch.manual_seed(seed)

        input_dim = metadata.get("input_dim", 384)
        num_classes = metadata.get("num_classes", 128)
        param_limit = metadata.get("param_limit", 5_000_000)

        # Build model within parameter budget
        target_width = 1024
        num_blocks = 2
        dropout = 0.1

        def build_model(width):
            return ResidualMLP(input_dim, num_classes, width=width, num_blocks=num_blocks, dropout=dropout)

        width = target_width
        model = build_model(width).to(device)
        param_count = sum(p.numel() for p in model.parameters() if p.requires_grad)

        # In case metadata changes param_limit in future, adapt width downward if needed
        while param_count > param_limit and width > 64:
            width = max(64, (int(width * 0.9) // 16) * 16)
            model = build_model(width).to(device)
            param_count = sum(p.numel() for p in model.parameters() if p.requires_grad)

        # Training setup
        max_epochs = 300
        patience = 60

        # Small label smoothing for regularization
        try:
            criterion = nn.CrossEntropyLoss(label_smoothing=0.05)
        except TypeError:
            criterion = nn.CrossEntropyLoss()

        optimizer = torch.optim.AdamW(model.parameters(), lr=1e-3, weight_decay=1e-4)
        scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=max_epochs, eta_min=1e-5)

        best_val_acc = 0.0
        best_state = None
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
                nn.utils.clip_grad_norm_(model.parameters(), max_norm=5.0)
                optimizer.step()

            if scheduler is not None:
                scheduler.step()

            # Validation
            model.eval()
            correct = 0
            total = 0
            with torch.no_grad():
                for inputs, targets in val_loader:
                    inputs = inputs.to(device)
                    targets = targets.to(device)
                    outputs = model(inputs)
                    preds = outputs.argmax(dim=1)
                    correct += (preds == targets).sum().item()
                    total += targets.size(0)

            val_acc = correct / total if total > 0 else 0.0

            if val_acc > best_val_acc + 1e-4:
                best_val_acc = val_acc
                best_state = {k: v.cpu().clone() for k, v in model.state_dict().items()}
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