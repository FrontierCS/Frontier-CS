import torch
import torch.nn as nn
import torch.optim as optim
from copy import deepcopy
import random
import numpy as np


class MLPNet(nn.Module):
    def __init__(self, input_dim: int, num_classes: int):
        super().__init__()
        hidden1 = 400
        hidden2 = 400
        hidden3 = 320

        self.fc1 = nn.Linear(input_dim, hidden1)
        self.bn1 = nn.BatchNorm1d(hidden1)
        self.fc2 = nn.Linear(hidden1, hidden2)
        self.bn2 = nn.BatchNorm1d(hidden2)
        self.fc3 = nn.Linear(hidden2, hidden3)
        self.bn3 = nn.BatchNorm1d(hidden3)
        self.fc4 = nn.Linear(hidden3, num_classes)

        self.act = nn.GELU()
        self.dropout = nn.Dropout(0.2)

        for m in self.modules():
            if isinstance(m, nn.Linear):
                nn.init.kaiming_normal_(m.weight, nonlinearity="relu")
                if m.bias is not None:
                    nn.init.zeros_(m.bias)
            elif isinstance(m, nn.BatchNorm1d):
                nn.init.ones_(m.weight)
                nn.init.zeros_(m.bias)

    def forward(self, x):
        x = self.fc1(x)
        x = self.bn1(x)
        x = self.act(x)
        x = self.dropout(x)

        residual = x
        x = self.fc2(x)
        x = self.bn2(x)
        x = self.act(x)
        x = self.dropout(x)
        x = x + residual

        x = self.fc3(x)
        x = self.bn3(x)
        x = self.act(x)
        x = self.dropout(x)

        x = self.fc4(x)
        return x


class BaselineNet(nn.Module):
    def __init__(self, input_dim: int, num_classes: int):
        super().__init__()
        hidden = 384
        self.fc1 = nn.Linear(input_dim, hidden)
        self.fc2 = nn.Linear(hidden, num_classes)
        self.act = nn.ReLU()

        for m in self.modules():
            if isinstance(m, nn.Linear):
                nn.init.kaiming_normal_(m.weight, nonlinearity="relu")
                if m.bias is not None:
                    nn.init.zeros_(m.bias)

    def forward(self, x):
        x = self.fc1(x)
        x = self.act(x)
        x = self.fc2(x)
        return x


class Solution:
    def solve(self, train_loader, val_loader, metadata: dict = None) -> torch.nn.Module:
        if metadata is None:
            metadata = {}

        seed = 42
        random.seed(seed)
        np.random.seed(seed)
        torch.manual_seed(seed)

        device_str = metadata.get("device", "cpu")
        device = torch.device(device_str)

        input_dim = int(metadata.get("input_dim", 384))
        num_classes = int(metadata.get("num_classes", 128))
        param_limit = int(metadata.get("param_limit", 500000))

        model = MLPNet(input_dim, num_classes)

        def count_params(m):
            return sum(p.numel() for p in m.parameters() if p.requires_grad)

        if count_params(model) > param_limit:
            model = BaselineNet(input_dim, num_classes)

        if count_params(model) > param_limit:
            # As an extra safety, fall back to a very small network
            small_hidden = max(64, min(256, input_dim // 2))
            model = nn.Sequential(
                nn.Linear(input_dim, small_hidden),
                nn.ReLU(),
                nn.Linear(small_hidden, num_classes),
            )

        model.to(device)

        try:
            criterion = nn.CrossEntropyLoss(label_smoothing=0.05)
        except TypeError:
            criterion = nn.CrossEntropyLoss()

        train_samples = metadata.get("train_samples", None)
        if train_samples is None:
            try:
                train_samples = len(train_loader.dataset)
            except Exception:
                train_samples = None

        if train_samples is not None and train_samples > 5000:
            max_epochs = 120
            patience = 20
            min_epochs = 40
        else:
            max_epochs = 260
            patience = 40
            min_epochs = 60

        optimizer = optim.AdamW(model.parameters(), lr=3e-3, weight_decay=1e-3)
        scheduler = optim.lr_scheduler.CosineAnnealingLR(
            optimizer, T_max=max_epochs, eta_min=1e-4
        )

        def evaluate(m, data_loader):
            m.eval()
            total_loss = 0.0
            total_correct = 0
            total_samples = 0
            num_batches = 0
            with torch.no_grad():
                for inputs, targets in data_loader:
                    inputs = inputs.to(device).float()
                    targets = targets.to(device).long()
                    outputs = m(inputs)
                    loss = criterion(outputs, targets)
                    total_loss += loss.item()
                    num_batches += 1
                    preds = outputs.argmax(dim=1)
                    total_correct += (preds == targets).sum().item()
                    total_samples += targets.size(0)
            avg_loss = total_loss / max(1, num_batches)
            acc = total_correct / total_samples if total_samples > 0 else 0.0
            return avg_loss, acc

        best_state = None
        best_val_acc = -float("inf")
        epochs_no_improve = 0

        for epoch in range(max_epochs):
            model.train()
            running_loss = 0.0
            num_batches = 0

            for inputs, targets in train_loader:
                inputs = inputs.to(device).float()
                targets = targets.to(device).long()

                optimizer.zero_grad(set_to_none=True)
                outputs = model(inputs)
                loss = criterion(outputs, targets)
                loss.backward()
                torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=5.0)
                optimizer.step()

                running_loss += loss.item()
                num_batches += 1

            if val_loader is not None:
                val_loss, val_acc = evaluate(model, val_loader)
            else:
                val_loss, val_acc = None, None

            scheduler.step()

            if val_acc is not None:
                improved = val_acc > best_val_acc + 1e-4
                if best_state is None or improved or (epoch + 1) <= min_epochs:
                    best_val_acc = max(best_val_acc, val_acc)
                    best_state = deepcopy(model.state_dict())
                    epochs_no_improve = 0
                else:
                    epochs_no_improve += 1

                if (epoch + 1) >= min_epochs and epochs_no_improve >= patience:
                    break

        if best_state is not None:
            model.load_state_dict(best_state)
        model.to(device)
        model.eval()
        return model
