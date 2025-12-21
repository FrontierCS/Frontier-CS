import math
import random
import copy
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim


class ResidualBlock(nn.Module):
    def __init__(self, dim: int, dropout: float = 0.1):
        super().__init__()
        self.norm1 = nn.LayerNorm(dim)
        self.fc1 = nn.Linear(dim, dim)
        self.act = nn.GELU()
        self.dropout1 = nn.Dropout(dropout)
        self.fc2 = nn.Linear(dim, dim)
        self.dropout2 = nn.Dropout(dropout)

    def forward(self, x):
        residual = x
        out = self.norm1(x)
        out = self.fc1(out)
        out = self.act(out)
        out = self.dropout1(out)
        out = self.fc2(out)
        out = self.dropout2(out)
        return out + residual


class ResidualMLP(nn.Module):
    def __init__(self, input_dim: int, num_classes: int, hidden_dim: int = 1450, dropout: float = 0.1):
        super().__init__()
        self.in_norm = nn.LayerNorm(input_dim)
        self.input = nn.Linear(input_dim, hidden_dim)
        self.act = nn.GELU()
        self.block = ResidualBlock(hidden_dim, dropout=dropout)
        self.out_norm = nn.LayerNorm(hidden_dim)
        self.out_dropout = nn.Dropout(dropout)
        self.fc_out = nn.Linear(hidden_dim, num_classes)

    def forward(self, x):
        x = self.in_norm(x)
        x = self.input(x)
        x = self.act(x)
        x = self.block(x)
        x = self.out_norm(x)
        x = self.out_dropout(x)
        x = self.fc_out(x)
        return x


class Solution:
    def _count_params(self, model: nn.Module) -> int:
        return sum(p.numel() for p in model.parameters() if p.requires_grad)

    def _build_model(self, input_dim: int, num_classes: int, param_limit: int) -> nn.Module:
        # Try a range of hidden dimensions, from large to smaller, until under the param limit
        hidden_candidates = [1450, 1400, 1280, 1152, 1024, 896, 768, 640, 512, 384, 256]
        for h in hidden_candidates:
            model = ResidualMLP(input_dim, num_classes, hidden_dim=h, dropout=0.1)
            if self._count_params(model) <= param_limit:
                return model
        # Fallback very small model (logistic regression) if limit extremely tight
        return nn.Sequential(
            nn.LayerNorm(input_dim),
            nn.Linear(input_dim, num_classes)
        )

    def _evaluate_accuracy(self, model: nn.Module, data_loader, device: torch.device) -> float:
        model.eval()
        correct = 0
        total = 0
        with torch.no_grad():
            for inputs, targets in data_loader:
                inputs = inputs.to(device)
                targets = targets.to(device)
                outputs = model(inputs)
                preds = outputs.argmax(dim=1)
                correct += (preds == targets).sum().item()
                total += targets.numel()
        if total == 0:
            return 0.0
        return correct / total

    def solve(self, train_loader, val_loader, metadata: dict = None) -> torch.nn.Module:
        if metadata is None:
            input_dim = 384
            num_classes = 128
            param_limit = 5_000_000
            device_str = "cpu"
            train_samples = None
        else:
            input_dim = int(metadata.get("input_dim", 384))
            num_classes = int(metadata.get("num_classes", 128))
            param_limit = int(metadata.get("param_limit", 5_000_000))
            device_str = metadata.get("device", "cpu")
            train_samples = metadata.get("train_samples", None)

        device = torch.device(device_str if torch.cuda.is_available() or device_str == "cpu" else "cpu")

        # Reproducibility
        seed = 42
        random.seed(seed)
        np.random.seed(seed)
        torch.manual_seed(seed)

        model = self._build_model(input_dim, num_classes, param_limit)
        model.to(device)

        # Double-check param limit
        assert self._count_params(model) <= param_limit, "Model exceeds parameter limit"

        # Training hyperparameters
        if train_samples is None:
            # Fallback: estimate from loader
            try:
                batch_size = next(iter(train_loader))[0].size(0)
                train_samples = len(train_loader) * batch_size
            except Exception:
                train_samples = 2048

        if train_samples <= 5000:
            max_epochs = 220
        else:
            max_epochs = 120

        patience = 35
        base_lr = 3e-3
        min_lr = 3e-5
        weight_decay = 1e-4

        criterion = nn.CrossEntropyLoss(label_smoothing=0.05)
        optimizer = optim.AdamW(model.parameters(), lr=base_lr, weight_decay=weight_decay, betas=(0.9, 0.98))
        scheduler = optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=max_epochs, eta_min=min_lr)

        best_val_acc = -math.inf
        best_state = None
        epochs_no_improve = 0

        for epoch in range(max_epochs):
            model.train()
            for inputs, targets in train_loader:
                inputs = inputs.to(device)
                targets = targets.to(device)

                optimizer.zero_grad(set_to_none=True)
                outputs = model(inputs)
                loss = criterion(outputs, targets)
                loss.backward()
                torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=5.0)
                optimizer.step()

            if val_loader is not None:
                val_acc = self._evaluate_accuracy(model, val_loader, device)
                if val_acc > best_val_acc + 1e-4:
                    best_val_acc = val_acc
                    best_state = copy.deepcopy(model.state_dict())
                    epochs_no_improve = 0
                else:
                    epochs_no_improve += 1
                    if epochs_no_improve >= patience:
                        break
            scheduler.step()

        if best_state is not None:
            model.load_state_dict(best_state)

        model.to(device)
        model.eval()
        return model
