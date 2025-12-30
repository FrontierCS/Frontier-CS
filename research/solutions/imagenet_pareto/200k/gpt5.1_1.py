import math
import copy
import random
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F


class ResidualMLP(nn.Module):
    def __init__(self, input_dim: int, hidden_dim: int, num_classes: int, dropout: float = 0.2):
        super().__init__()
        self.fc1 = nn.Linear(input_dim, hidden_dim)
        self.act1 = nn.GELU()
        self.norm1 = nn.LayerNorm(hidden_dim)
        self.dropout1 = nn.Dropout(dropout)

        self.fc2 = nn.Linear(hidden_dim, hidden_dim)
        self.act2 = nn.GELU()
        self.norm2 = nn.LayerNorm(hidden_dim)
        self.dropout2 = nn.Dropout(dropout)

        self.fc_out = nn.Linear(hidden_dim, num_classes)

    def forward(self, x):
        x = self.fc1(x)
        x = self.act1(x)
        x = self.norm1(x)
        x = self.dropout1(x)

        residual = x

        y = self.fc2(x)
        y = self.act2(y)
        y = self.norm2(y)
        y = self.dropout2(y)

        x = residual + y
        logits = self.fc_out(x)
        return logits


class Solution:
    def _count_params_mlp(self, input_dim, num_classes, hidden_dim, use_norm=True):
        # Two-hidden-layer MLP with LayerNorm after each hidden (no params for dropout)
        # Linear1: (input_dim + 1) * hidden_dim
        # Linear2: (hidden_dim + 1) * hidden_dim
        # Linear_out: (hidden_dim + 1) * num_classes
        # LayerNorm: 2 * hidden_dim per layer
        total = (input_dim + 1) * hidden_dim
        total += (hidden_dim + 1) * hidden_dim
        total += (hidden_dim + 1) * num_classes
        if use_norm:
            total += 4 * hidden_dim
        return total

    def _select_hidden_dim(self, input_dim, num_classes, param_limit):
        # Start from a reasonably large hidden dim and decrease until within limit
        max_hidden = 512
        min_hidden = 32
        hidden = max_hidden
        while hidden >= min_hidden:
            params = self._count_params_mlp(input_dim, num_classes, hidden, use_norm=True)
            if params <= param_limit:
                return hidden
            hidden -= 16
        # Fallback to indicate we should use a simple linear model
        return 0

    def _evaluate(self, model, loader, device, criterion):
        if loader is None:
            return 0.0, 0.0
        model.eval()
        total_loss = 0.0
        total_correct = 0
        total_samples = 0
        with torch.no_grad():
            for inputs, targets in loader:
                inputs = inputs.to(device, dtype=torch.float32)
                targets = targets.to(device)
                outputs = model(inputs)
                loss = criterion(outputs, targets)
                batch_size = targets.size(0)
                total_loss += loss.item() * batch_size
                preds = outputs.argmax(dim=1)
                total_correct += (preds == targets).sum().item()
                total_samples += batch_size
        if total_samples == 0:
            return 0.0, 0.0
        avg_loss = total_loss / total_samples
        acc = total_correct / total_samples
        return acc, avg_loss

    def solve(self, train_loader, val_loader, metadata: dict = None) -> torch.nn.Module:
        # Set seeds for reproducibility
        torch.manual_seed(42)
        random.seed(42)
        np.random.seed(42)

        if metadata is None:
            metadata = {}

        input_dim = int(metadata.get("input_dim", 384))
        num_classes = int(metadata.get("num_classes", 128))
        param_limit = int(metadata.get("param_limit", 200000))

        device_str = metadata.get("device", "cpu")
        if device_str.startswith("cuda") and not torch.cuda.is_available():
            device_str = "cpu"
        device = torch.device(device_str)

        hidden_dim = self._select_hidden_dim(input_dim, num_classes, param_limit)

        if hidden_dim >= 32:
            model = ResidualMLP(input_dim=input_dim, hidden_dim=hidden_dim, num_classes=num_classes, dropout=0.2)
        else:
            # Fallback: simple linear classifier if param limit is very small
            model = nn.Linear(input_dim, num_classes)

        model.to(device)

        # Ensure we obey parameter limit; if not, fallback to linear model
        param_count = sum(p.numel() for p in model.parameters() if p.requires_grad)
        if param_count > param_limit:
            model = nn.Linear(input_dim, num_classes).to(device)

        # Training configuration
        max_epochs = 200
        patience = 25
        lr = 3e-3
        weight_decay = 1e-4

        # Loss with mild label smoothing
        try:
            criterion = nn.CrossEntropyLoss(label_smoothing=0.05)
        except TypeError:
            # Older PyTorch without label_smoothing
            criterion = nn.CrossEntropyLoss()

        optimizer = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=weight_decay)
        scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
            optimizer,
            mode="max",
            factor=0.5,
            patience=5,
            verbose=False,
            min_lr=1e-5,
        )

        best_val_acc = 0.0
        best_state = copy.deepcopy(model.state_dict())
        epochs_no_improve = 0

        for epoch in range(max_epochs):
            model.train()
            for inputs, targets in train_loader:
                inputs = inputs.to(device, dtype=torch.float32)
                targets = targets.to(device)

                optimizer.zero_grad()
                outputs = model(inputs)
                loss = criterion(outputs, targets)
                loss.backward()
                torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=5.0)
                optimizer.step()

            val_acc, val_loss = self._evaluate(model, val_loader, device, criterion)
            scheduler.step(val_acc)

            if val_acc > best_val_acc + 1e-4:
                best_val_acc = val_acc
                best_state = copy.deepcopy(model.state_dict())
                epochs_no_improve = 0
            else:
                epochs_no_improve += 1
                if epochs_no_improve >= patience:
                    break

        model.load_state_dict(best_state)
        model.to(torch.device("cpu"))
        model.eval()
        return model