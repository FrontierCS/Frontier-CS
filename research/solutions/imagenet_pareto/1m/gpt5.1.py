import torch
import torch.nn as nn
import torch.optim as optim
import random
import numpy as np


class MLPNet(nn.Module):
    def __init__(self, input_dim: int, num_classes: int, width: int, dropout: float = 0.2, use_bn: bool = True):
        super().__init__()
        layers = []
        layers.append(nn.Linear(input_dim, width))
        if use_bn:
            layers.append(nn.BatchNorm1d(width))
        layers.append(nn.ReLU(inplace=True))
        if dropout and dropout > 0.0:
            layers.append(nn.Dropout(dropout))
        layers.append(nn.Linear(width, width))
        if use_bn:
            layers.append(nn.BatchNorm1d(width))
        layers.append(nn.ReLU(inplace=True))
        if dropout and dropout > 0.0:
            layers.append(nn.Dropout(dropout))
        layers.append(nn.Linear(width, num_classes))
        self.net = nn.Sequential(*layers)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = x.view(x.size(0), -1)
        return self.net(x)


class Solution:
    def _count_params_arch(self, width: int, input_dim: int, num_classes: int, use_bn: bool) -> int:
        # Linear(input_dim, width)
        p = input_dim * width + width
        if use_bn:
            p += 2 * width  # BatchNorm1d(width)
        # Linear(width, width)
        p += width * width + width
        if use_bn:
            p += 2 * width  # BatchNorm1d(width)
        # Linear(width, num_classes)
        p += width * num_classes + num_classes
        return p

    def _select_width(self, input_dim: int, num_classes: int, param_limit: int):
        max_width = 1024
        min_width = 32

        # Try with batch normalization first
        best_width = None
        best_use_bn = True
        for width in range(max_width, min_width - 1, -1):
            p = self._count_params_arch(width, input_dim, num_classes, use_bn=True)
            if p <= param_limit:
                best_width = width
                best_use_bn = True
                break

        # If no width fits with BN, try without BN
        if best_width is None:
            for width in range(max_width, min_width - 1, -1):
                p = self._count_params_arch(width, input_dim, num_classes, use_bn=False)
                if p <= param_limit:
                    best_width = width
                    best_use_bn = False
                    break

        # Fallback very small model if param_limit is extremely low (should not happen here)
        if best_width is None:
            best_width = min(64, max(4, param_limit // max(input_dim + num_classes, 1)))
            best_use_bn = False

        return best_width, best_use_bn

    def _evaluate(self, model: nn.Module, data_loader, device, criterion=None):
        model.eval()
        total_loss = 0.0
        total_samples = 0
        correct = 0
        with torch.no_grad():
            for inputs, targets in data_loader:
                inputs = inputs.to(device)
                targets = targets.to(device)
                outputs = model(inputs)
                if criterion is not None:
                    loss = criterion(outputs, targets)
                    total_loss += loss.item() * targets.size(0)
                preds = outputs.argmax(dim=1)
                correct += (preds == targets).sum().item()
                total_samples += targets.size(0)
        if total_samples == 0:
            return float("inf"), 0.0
        avg_loss = total_loss / total_samples if criterion is not None else 0.0
        accuracy = correct / total_samples
        return avg_loss, accuracy

    def _train_model(self, model: nn.Module, train_loader, val_loader, device, metadata):
        criterion = nn.CrossEntropyLoss(label_smoothing=0.05)
        lr = 0.0015
        weight_decay = 3e-4
        max_epochs = 200
        patience = 25

        optimizer = optim.AdamW(model.parameters(), lr=lr, weight_decay=weight_decay)
        scheduler = optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=max_epochs, eta_min=1e-5)

        best_state = None
        best_val_acc = 0.0
        epochs_no_improve = 0

        for _ in range(max_epochs):
            model.train()
            for inputs, targets in train_loader:
                inputs = inputs.to(device)
                targets = targets.to(device)

                optimizer.zero_grad()
                outputs = model(inputs)
                loss = criterion(outputs, targets)
                loss.backward()
                optimizer.step()

            _, val_acc = self._evaluate(model, val_loader, device, criterion)

            if val_acc > best_val_acc + 1e-4:
                best_val_acc = val_acc
                best_state = {k: v.cpu().clone() for k, v in model.state_dict().items()}
                epochs_no_improve = 0
            else:
                epochs_no_improve += 1
                if epochs_no_improve >= patience:
                    break

            scheduler.step()

        if best_state is not None:
            model.load_state_dict(best_state)

        return model

    def solve(self, train_loader, val_loader, metadata: dict = None) -> torch.nn.Module:
        if metadata is None:
            metadata = {}

        # Set seeds for reproducibility
        random.seed(42)
        np.random.seed(42)
        torch.manual_seed(42)

        device_str = metadata.get("device", "cpu")
        device = torch.device(device_str)

        input_dim = int(metadata.get("input_dim", 384))
        num_classes = int(metadata.get("num_classes", 128))
        param_limit = int(metadata.get("param_limit", 1_000_000))

        width, use_bn = self._select_width(input_dim, num_classes, param_limit)

        dropout = 0.2
        model = MLPNet(input_dim=input_dim, num_classes=num_classes, width=width, dropout=dropout, use_bn=use_bn)

        # Safety check to strictly enforce parameter limit
        def count_params(m):
            return sum(p.numel() for p in m.parameters() if p.requires_grad)

        current_params = count_params(model)
        while current_params > param_limit and width > 8:
            width -= 1
            model = MLPNet(input_dim=input_dim, num_classes=num_classes, width=width, dropout=dropout, use_bn=use_bn)
            current_params = count_params(model)

        model.to(device)

        self._train_model(model, train_loader, val_loader, device, metadata)

        model.eval()
        return model