import torch
import torch.nn as nn
import torch.optim as optim
from torch.optim.lr_scheduler import MultiStepLR
import random
import numpy as np
import copy


def set_seed(seed: int = 42):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def compute_param_count(input_dim: int, num_classes: int, h1: int, h2: int, h3: int) -> int:
    # First hidden layer + BN
    total = input_dim * h1 + h1  # Linear
    total += 2 * h1  # BatchNorm (weight + bias)

    # Second hidden layer + BN
    total += h1 * h2 + h2
    total += 2 * h2

    if h3 > 0:
        # Third hidden layer + BN
        total += h2 * h3 + h3
        total += 2 * h3
        # Output layer
        total += h3 * num_classes + num_classes
    else:
        # Output directly from second hidden
        total += h2 * num_classes + num_classes

    return total


class MLPClassifier(nn.Module):
    def __init__(self, input_dim: int, num_classes: int, h1: int, h2: int, h3: int, dropout: float = 0.3):
        super().__init__()
        layers = []
        # Layer 1
        layers.append(nn.Linear(input_dim, h1))
        layers.append(nn.BatchNorm1d(h1))
        layers.append(nn.ReLU(inplace=True))
        layers.append(nn.Dropout(p=dropout))
        # Layer 2
        layers.append(nn.Linear(h1, h2))
        layers.append(nn.BatchNorm1d(h2))
        layers.append(nn.ReLU(inplace=True))
        layers.append(nn.Dropout(p=dropout))
        # Optional Layer 3
        if h3 > 0:
            layers.append(nn.Linear(h2, h3))
            layers.append(nn.BatchNorm1d(h3))
            layers.append(nn.ReLU(inplace=True))
            layers.append(nn.Dropout(p=dropout))
            layers.append(nn.Linear(h3, num_classes))
        else:
            layers.append(nn.Linear(h2, num_classes))

        self.net = nn.Sequential(*layers)

    def forward(self, x):
        if x.ndim > 2:
            x = x.view(x.size(0), -1)
        return self.net(x)


class SimpleMLP(nn.Module):
    """Fallback simple 2-layer MLP without BN, guaranteed under param limit."""
    def __init__(self, input_dim: int, num_classes: int, hidden_dim: int):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.ReLU(inplace=True),
            nn.Linear(hidden_dim, num_classes)
        )

    def forward(self, x):
        if x.ndim > 2:
            x = x.view(x.size(0), -1)
        return self.net(x)


class Solution:
    def _build_model(self, input_dim: int, num_classes: int, param_limit: int, device: torch.device) -> nn.Module:
        # Search for best (h1, h2, h3) under parameter limit
        hidden_options = [1024, 960, 896, 832, 768, 704, 640, 576, 512, 448, 384, 320, 256, 192, 128]
        best_cfg = None
        best_params = -1

        for h1 in hidden_options:
            for h2 in hidden_options:
                if h2 > h1:
                    continue
                # include h3 = 0 (no third hidden) + other options
                for h3 in [0] + hidden_options:
                    if h3 > h2:
                        continue
                    param_count = compute_param_count(input_dim, num_classes, h1, h2, h3)
                    if param_count <= param_limit and param_count > best_params:
                        best_params = param_count
                        best_cfg = (h1, h2, h3)

        if best_cfg is not None:
            h1, h2, h3 = best_cfg
            model = MLPClassifier(input_dim, num_classes, h1, h2, h3, dropout=0.3)
            # Safety check
            real_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
            if real_params <= param_limit:
                return model.to(device)

        # Fallback: simple 2-layer MLP
        # Compute max hidden size to stay under param_limit
        # param_count ≈ input_dim*H + H + H*num_classes + num_classes
        denom = input_dim + num_classes + 1
        max_hidden = max(8, min(512, (param_limit - num_classes) // max(denom, 1)))
        model = SimpleMLP(input_dim, num_classes, hidden_dim=int(max_hidden))
        return model.to(device)

    def _evaluate_accuracy(self, model: nn.Module, data_loader, device: torch.device) -> float:
        model.eval()
        correct = 0
        total = 0
        with torch.no_grad():
            for inputs, targets in data_loader:
                inputs = inputs.to(device)
                if inputs.ndim > 2:
                    inputs = inputs.view(inputs.size(0), -1)
                targets = targets.to(device).long()
                outputs = model(inputs)
                preds = outputs.argmax(dim=1)
                correct += (preds == targets).sum().item()
                total += targets.numel()
        if total == 0:
            return 0.0
        return correct / total

    def solve(self, train_loader, val_loader, metadata: dict = None) -> torch.nn.Module:
        if metadata is None:
            metadata = {}

        set_seed(42)

        device_str = metadata.get("device", "cpu")
        if device_str.startswith("cuda") and not torch.cuda.is_available():
            device_str = "cpu"
        device = torch.device(device_str)

        input_dim = int(metadata.get("input_dim", 384))
        num_classes = int(metadata.get("num_classes", 128))
        param_limit = int(metadata.get("param_limit", 1_000_000))

        model = self._build_model(input_dim, num_classes, param_limit, device)

        optimizer = optim.AdamW(model.parameters(), lr=3e-3, weight_decay=5e-4)
        try:
            criterion = nn.CrossEntropyLoss(label_smoothing=0.1)
        except TypeError:
            criterion = nn.CrossEntropyLoss()

        scheduler = MultiStepLR(optimizer, milestones=[60, 120, 160], gamma=0.2)

        max_epochs = 200
        patience = 25
        best_val_acc = 0.0
        best_state = None
        epochs_no_improve = 0

        for epoch in range(max_epochs):
            model.train()
            for inputs, targets in train_loader:
                inputs = inputs.to(device)
                if inputs.ndim > 2:
                    inputs = inputs.view(inputs.size(0), -1)
                targets = targets.to(device).long()

                optimizer.zero_grad(set_to_none=True)
                outputs = model(inputs)
                loss = criterion(outputs, targets)
                loss.backward()
                optimizer.step()

            val_acc = self._evaluate_accuracy(model, val_loader, device)
            scheduler.step()

            if val_acc > best_val_acc + 1e-4:
                best_val_acc = val_acc
                best_state = copy.deepcopy(model.state_dict())
                epochs_no_improve = 0
            else:
                epochs_no_improve += 1
                if epochs_no_improve >= patience:
                    break

        if best_state is not None:
            model.load_state_dict(best_state)

        model.to(torch.device("cpu"))
        model.eval()
        return model