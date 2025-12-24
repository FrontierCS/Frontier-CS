import torch
import torch.nn as nn
import torch.optim as optim
import numpy as np
import random
import copy


class MLPNet(nn.Module):
    def __init__(self, input_dim: int, num_classes: int, hidden_dims=(1280, 1024, 512), dropout: float = 0.15):
        super().__init__()
        self.input_bn = nn.BatchNorm1d(input_dim)

        layers = []
        in_dim = input_dim
        for h in hidden_dims:
            layers.append(nn.Linear(in_dim, h))
            layers.append(nn.BatchNorm1d(h))
            layers.append(nn.GELU())
            if dropout > 0.0:
                layers.append(nn.Dropout(dropout))
            in_dim = h
        layers.append(nn.Linear(in_dim, num_classes))

        self.features = nn.Sequential(*layers)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        if x.dim() > 2:
            x = x.view(x.size(0), -1)
        x = self.input_bn(x)
        x = self.features(x)
        return x


def count_parameters(model: nn.Module) -> int:
    return sum(p.numel() for p in model.parameters() if p.requires_grad)


def evaluate(model: nn.Module, data_loader, device: torch.device, criterion=None):
    model.eval()
    total_loss = 0.0
    correct = 0
    total = 0
    if data_loader is None:
        return 0.0, 0.0

    with torch.no_grad():
        for batch in data_loader:
            if isinstance(batch, (list, tuple)) and len(batch) >= 2:
                inputs, targets = batch[0], batch[1]
            else:
                continue

            inputs = inputs.to(device)
            targets = targets.to(device)

            outputs = model(inputs)
            if criterion is not None:
                loss = criterion(outputs, targets)
                total_loss += loss.item() * targets.size(0)

            preds = outputs.argmax(dim=1)
            correct += (preds == targets).sum().item()
            total += targets.size(0)

    avg_loss = total_loss / total if (criterion is not None and total > 0) else 0.0
    acc = correct / total if total > 0 else 0.0
    return avg_loss, acc


class Solution:
    def solve(self, train_loader, val_loader, metadata: dict = None) -> torch.nn.Module:
        if metadata is None:
            input_dim = 384
            num_classes = 128
            param_limit = 2_500_000
            device_str = "cpu"
        else:
            input_dim = int(metadata.get("input_dim", 384))
            num_classes = int(metadata.get("num_classes", 128))
            param_limit = int(metadata.get("param_limit", 2_500_000))
            device_str = metadata.get("device", "cpu")

        device = torch.device(device_str)

        seed = 42
        torch.manual_seed(seed)
        np.random.seed(seed)
        random.seed(seed)

        hidden_options = [
            (1280, 1024, 512),
            (1152, 1024, 512),
            (1024, 1024, 512),
            (1024, 768, 512),
            (1024, 768, 384),
            (1024, 512, 256),
            (768, 512, 256),
            (512, 512, 256),
            (512, 256, 256),
            (512, 256),
            (384, 256),
            (384, 128),
        ]

        model = None
        for hidden_dims in hidden_options:
            candidate = MLPNet(input_dim, num_classes, hidden_dims=hidden_dims, dropout=0.15)
            if count_parameters(candidate) <= param_limit:
                model = candidate
                break

        if model is None:
            model = MLPNet(input_dim, num_classes, hidden_dims=(256,), dropout=0.1)

        model.to(device)

        train_samples = None
        if metadata is not None:
            train_samples = metadata.get("train_samples", None)

        if train_samples is not None and train_samples < 5000:
            max_epochs = 160
        else:
            max_epochs = 120

        patience = 25

        try:
            criterion = nn.CrossEntropyLoss(label_smoothing=0.1)
            val_criterion = nn.CrossEntropyLoss()
        except TypeError:
            criterion = nn.CrossEntropyLoss()
            val_criterion = criterion

        optimizer = optim.AdamW(model.parameters(), lr=3e-3, weight_decay=1e-2)
        scheduler = optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=max_epochs)

        best_val_acc = 0.0
        best_state = None
        epochs_since_improve = 0

        for epoch in range(max_epochs):
            model.train()
            for batch in train_loader:
                if isinstance(batch, (list, tuple)) and len(batch) >= 2:
                    inputs, targets = batch[0], batch[1]
                else:
                    continue

                inputs = inputs.to(device)
                targets = targets.to(device)

                optimizer.zero_grad()
                outputs = model(inputs)
                loss = criterion(outputs, targets)
                loss.backward()
                torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
                optimizer.step()

            if val_loader is not None:
                _, val_acc = evaluate(model, val_loader, device, criterion=val_criterion)
                if val_acc > best_val_acc + 1e-4:
                    best_val_acc = val_acc
                    best_state = copy.deepcopy(model.state_dict())
                    epochs_since_improve = 0
                else:
                    epochs_since_improve += 1

                if epochs_since_improve >= patience:
                    scheduler.step()
                    break

            scheduler.step()

        if best_state is not None:
            model.load_state_dict(best_state)

        model.to("cpu")
        return model
