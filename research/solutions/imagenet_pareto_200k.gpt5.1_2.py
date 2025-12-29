import math
import random
from copy import deepcopy

import torch
import torch.nn as nn
import torch.nn.functional as F


class MLPNet(nn.Module):
    def __init__(self, input_dim: int, num_classes: int, hidden_dims):
        super().__init__()
        hidden_dims = list(hidden_dims)
        self.hidden_dims = hidden_dims

        layers = []
        bns = []

        prev_dim = input_dim
        for h in hidden_dims:
            layers.append(nn.Linear(prev_dim, h))
            bns.append(nn.BatchNorm1d(h))
            prev_dim = h

        self.layers = nn.ModuleList(layers)
        self.bns = nn.ModuleList(bns)
        self.dropout = nn.Dropout(0.2)
        self.output = nn.Linear(prev_dim, num_classes)

    def forward(self, x):
        out = x
        for i, (layer, bn) in enumerate(zip(self.layers, self.bns)):
            z = layer(out)
            z = bn(z)
            # Residual connection if dimensions match with previous hidden
            if i > 0 and z.shape[1] == out.shape[1]:
                z = z + out
            z = F.relu(z, inplace=True)
            # Apply dropout after each hidden layer except just before output
            if i < len(self.layers) - 1:
                z = self.dropout(z)
            out = z
        out = self.output(out)
        return out


class Solution:
    def _set_seed(self, seed: int = 42):
        random.seed(seed)
        torch.manual_seed(seed)
        try:
            import numpy as np

            np.random.seed(seed)
        except Exception:
            pass

    def _build_model(self, input_dim: int, num_classes: int, param_limit: int) -> nn.Module:
        # Candidate architectures ordered from largest to smallest (within ~200k params with BN)
        candidate_hidden_configs = [
            (256, 256),
            (256, 192),
            (256,),
            (192, 192),
            (192,),
            (160, 160),
            (160,),
            (128, 128),
            (128,),
            (96, 96),
            (96,),
            (64, 64),
            (64,),
        ]

        chosen_model = None
        for hidden in candidate_hidden_configs:
            model = MLPNet(input_dim, num_classes, hidden)
            param_count = sum(p.numel() for p in model.parameters() if p.requires_grad)
            if param_count <= param_limit:
                chosen_model = model
                break

        # Fallback to simplest if somehow none fit
        if chosen_model is None:
            chosen_model = MLPNet(input_dim, num_classes, (64,))

        return chosen_model

    def _evaluate(self, model, loader, criterion, device):
        model.eval()
        total_loss = 0.0
        total = 0
        correct = 0
        with torch.no_grad():
            for inputs, targets in loader:
                inputs = inputs.to(device)
                targets = targets.to(device)

                outputs = model(inputs)
                loss = criterion(outputs, targets)

                batch_size = targets.size(0)
                total_loss += loss.item() * batch_size
                total += batch_size
                preds = outputs.argmax(dim=1)
                correct += (preds == targets).sum().item()

        if total == 0:
            return 0.0, 0.0
        avg_loss = total_loss / total
        acc = correct / total
        return avg_loss, acc

    def solve(self, train_loader, val_loader, metadata: dict = None) -> torch.nn.Module:
        self._set_seed(42)

        if metadata is None:
            raise ValueError("metadata must be provided")

        input_dim = int(metadata.get("input_dim", 384))
        num_classes = int(metadata.get("num_classes", 128))
        param_limit = int(metadata.get("param_limit", 200000))
        device_str = metadata.get("device", "cpu")
        device = torch.device(device_str)

        model = self._build_model(input_dim, num_classes, param_limit)
        model.to(device)

        # Ensure parameter constraint is respected
        param_count = sum(p.numel() for p in model.parameters() if p.requires_grad)
        if param_count > param_limit:
            raise RuntimeError(f"Model exceeds parameter limit: {param_count} > {param_limit}")

        # Training configuration
        num_epochs = 220
        patience = 25

        # Use label smoothing for better generalization
        criterion = nn.CrossEntropyLoss(label_smoothing=0.1)
        optimizer = torch.optim.AdamW(model.parameters(), lr=1e-3, weight_decay=1e-4)
        scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(
            optimizer, T_max=num_epochs, eta_min=1e-5
        )

        best_val_acc = -1.0
        best_state = deepcopy(model.state_dict())
        epochs_no_improve = 0

        for epoch in range(num_epochs):
            model.train()
            total_train = 0
            for inputs, targets in train_loader:
                inputs = inputs.to(device)
                targets = targets.to(device)

                optimizer.zero_grad()
                outputs = model(inputs)
                loss = criterion(outputs, targets)
                loss.backward()
                torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=5.0)
                optimizer.step()

                total_train += targets.size(0)

            # Validation
            val_loss, val_acc = self._evaluate(model, val_loader, criterion, device)
            scheduler.step()

            if val_acc > best_val_acc + 1e-4:
                best_val_acc = val_acc
                best_state = deepcopy(model.state_dict())
                epochs_no_improve = 0
            else:
                epochs_no_improve += 1
                if epochs_no_improve >= patience:
                    break

        model.load_state_dict(best_state)
        model.to(device)
        model.eval()
        return model