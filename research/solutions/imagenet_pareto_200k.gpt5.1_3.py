import torch
import torch.nn as nn
import torch.optim as optim
import copy
from typing import Sequence, Optional


class MLPNet(nn.Module):
    def __init__(self, input_dim: int, num_classes: int, hidden_dims: Sequence[int], dropout: float = 0.2):
        super().__init__()
        layers = []
        in_dim = input_dim
        for h in hidden_dims:
            layers.append(nn.Linear(in_dim, h))
            layers.append(nn.BatchNorm1d(h))
            layers.append(nn.ReLU(inplace=True))
            if dropout > 0.0:
                layers.append(nn.Dropout(p=dropout))
            in_dim = h
        layers.append(nn.Linear(in_dim, num_classes))
        self.net = nn.Sequential(*layers)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x)


class Solution:
    def _build_model(self, input_dim: int, num_classes: int, param_limit: int) -> nn.Module:
        # Candidate hidden configurations (largest first, will pick first under param_limit)
        candidates = [
            (272, 192, 128),
            (256, 192, 128),
            (256, 176, 128),
            (256, 160, 128),
            (224, 192, 128),
            (224, 176, 128),
            (224, 160, 128),
            (256, 192),
            (256, 176),
            (256, 160),
            (224, 192),
            (224, 176),
            (224, 160),
            (192, 160, 128),
            (192, 160),
            (192,),
        ]

        for hidden_dims in candidates:
            model = MLPNet(input_dim, num_classes, hidden_dims=hidden_dims, dropout=0.2)
            param_count = sum(p.numel() for p in model.parameters() if p.requires_grad)
            if param_count <= param_limit:
                return model
        # Fallback minimal model if nothing fits (very unlikely with given limits)
        return nn.Sequential(nn.Linear(input_dim, num_classes))

    def _evaluate(self, model: nn.Module, data_loader, device: torch.device) -> float:
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
        model.train()
        return correct / total if total > 0 else 0.0

    def solve(self, train_loader, val_loader, metadata: Optional[dict] = None) -> torch.nn.Module:
        if metadata is None:
            metadata = {}
        torch.manual_seed(42)

        input_dim = int(metadata.get("input_dim", 384))
        num_classes = int(metadata.get("num_classes", 128))
        param_limit = int(metadata.get("param_limit", 200000))
        device_str = metadata.get("device", "cpu")
        device = torch.device(device_str if torch.cuda.is_available() or device_str == "cpu" else "cpu")

        model = self._build_model(input_dim, num_classes, param_limit)
        model.to(device)

        # Training hyperparameters
        train_samples = metadata.get("train_samples", None)
        if train_samples is not None and train_samples <= 2048:
            max_epochs = 200
        else:
            max_epochs = 160
        patience = 30

        optimizer = optim.AdamW(model.parameters(), lr=1e-3, weight_decay=5e-4)
        try:
            criterion = nn.CrossEntropyLoss(label_smoothing=0.05)
        except TypeError:
            criterion = nn.CrossEntropyLoss()

        scheduler = optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=max_epochs, eta_min=1e-5)

        best_state = copy.deepcopy(model.state_dict())
        best_val_acc = 0.0
        best_epoch = 0

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

            scheduler.step()

            val_acc = self._evaluate(model, val_loader, device)
            if val_acc > best_val_acc + 1e-4:
                best_val_acc = val_acc
                best_state = copy.deepcopy(model.state_dict())
                best_epoch = epoch

            if epoch - best_epoch >= patience:
                break

        model.load_state_dict(best_state)
        model.to(device)
        model.eval()
        return model
