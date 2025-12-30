import torch
import torch.nn as nn
import torch.optim as optim
from copy import deepcopy
import random
import numpy as np


class MLPNet(nn.Module):
    def __init__(self, input_dim: int, hidden_dim: int, num_classes: int, dropout: float = 0.1):
        super().__init__()
        self.fc1 = nn.Linear(input_dim, hidden_dim)
        self.bn1 = nn.BatchNorm1d(hidden_dim)
        self.fc2 = nn.Linear(hidden_dim, hidden_dim)
        self.bn2 = nn.BatchNorm1d(hidden_dim)
        self.fc3 = nn.Linear(hidden_dim, num_classes)
        self.act = nn.GELU()
        if dropout > 0.0:
            self.drop1 = nn.Dropout(dropout)
            self.drop2 = nn.Dropout(dropout)
        else:
            self.drop1 = nn.Identity()
            self.drop2 = nn.Identity()

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self.fc1(x)
        x = self.bn1(x)
        x = self.act(x)
        x = self.drop1(x)
        residual = x
        x = self.fc2(x)
        x = self.bn2(x)
        x = self.act(x)
        x = x + residual
        x = self.drop2(x)
        x = self.fc3(x)
        return x


class Solution:
    def solve(self, train_loader, val_loader, metadata: dict = None) -> torch.nn.Module:
        if metadata is None:
            metadata = {}

        # Reproducibility
        seed = 42
        random.seed(seed)
        np.random.seed(seed)
        torch.manual_seed(seed)

        device_str = metadata.get("device", "cpu")
        device = torch.device(device_str)

        # Get dataset metadata
        input_dim = metadata.get("input_dim", None)
        num_classes = metadata.get("num_classes", None)
        param_limit = int(metadata.get("param_limit", 200000))

        if input_dim is None or num_classes is None:
            try:
                batch = next(iter(train_loader))
                inputs, targets = batch
                if input_dim is None:
                    input_dim = inputs.shape[1]
                if num_classes is None:
                    num_classes = int(targets.max().item()) + 1
            except StopIteration:
                input_dim = input_dim or 384
                num_classes = num_classes or 128

        # Choose hidden size to respect parameter limit
        def choose_hidden_size(D: int, C: int, limit: int) -> int:
            # Parameter formula for this architecture:
            # params(h) = D*h + h*h + h*C + 6*h + C
            max_h = min(512, max(16, limit // max(1, (D + C + 6))))
            best_h = 16
            for h in range(max_h, 15, -1):
                params = D * h + h * h + h * C + 6 * h + C
                if params <= limit:
                    best_h = h
                    break
            return best_h

        hidden_dim = choose_hidden_size(input_dim, num_classes, param_limit)

        model = MLPNet(input_dim=input_dim, hidden_dim=hidden_dim, num_classes=num_classes, dropout=0.15)
        model.to(device)

        # Safety check: ensure under parameter limit; if not, shrink hidden_dim
        def count_params(m: nn.Module) -> int:
            return sum(p.numel() for p in m.parameters() if p.requires_grad)

        param_count = count_params(model)
        while param_count > param_limit and hidden_dim > 16:
            hidden_dim = max(16, hidden_dim // 2)
            model = MLPNet(input_dim=input_dim, hidden_dim=hidden_dim, num_classes=num_classes, dropout=0.15)
            model.to(device)
            param_count = count_params(model)

        # Training hyperparameters
        train_samples = metadata.get("train_samples", None)
        if train_samples is not None:
            if train_samples <= 4096:
                num_epochs = 180
            elif train_samples <= 16384:
                num_epochs = 120
            else:
                num_epochs = 80
        else:
            num_epochs = 160

        base_lr = 3e-3
        weight_decay = 1e-2

        optimizer = optim.AdamW(model.parameters(), lr=base_lr, weight_decay=weight_decay)
        scheduler = optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=num_epochs, eta_min=1e-4)

        # Label smoothing for better generalization
        criterion = nn.CrossEntropyLoss(label_smoothing=0.1)

        best_val_acc = 0.0
        best_state = deepcopy(model.state_dict())

        for epoch in range(num_epochs):
            model.train()
            for inputs, targets in train_loader:
                inputs = inputs.to(device).float()
                targets = targets.to(device)

                optimizer.zero_grad(set_to_none=True)
                outputs = model(inputs)
                loss = criterion(outputs, targets)
                loss.backward()
                torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=5.0)
                optimizer.step()

            # Validation
            model.eval()
            val_correct = 0
            val_total = 0
            with torch.no_grad():
                for inputs, targets in val_loader:
                    inputs = inputs.to(device).float()
                    targets = targets.to(device)
                    outputs = model(inputs)
                    preds = outputs.argmax(dim=1)
                    val_correct += (preds == targets).sum().item()
                    val_total += targets.numel()

            if val_total > 0:
                val_acc = val_correct / val_total
                if val_acc > best_val_acc:
                    best_val_acc = val_acc
                    best_state = deepcopy(model.state_dict())

            scheduler.step()

        model.load_state_dict(best_state)
        model.eval()
        model.to(device)

        return model