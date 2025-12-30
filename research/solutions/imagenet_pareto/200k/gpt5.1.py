import torch
import torch.nn as nn
import torch.nn.functional as F
from copy import deepcopy


class MLPNet(nn.Module):
    def __init__(self, input_dim: int, num_classes: int, hidden_dim: int = 256, dropout: float = 0.25):
        super().__init__()
        self.fc1 = nn.Linear(input_dim, hidden_dim)
        self.bn1 = nn.BatchNorm1d(hidden_dim)
        self.fc2 = nn.Linear(hidden_dim, hidden_dim)
        self.bn2 = nn.BatchNorm1d(hidden_dim)
        self.fc3 = nn.Linear(hidden_dim, num_classes)
        self.dropout = nn.Dropout(dropout)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self.fc1(x)
        x = self.bn1(x)
        x = F.relu(x, inplace=True)
        x = self.dropout(x)
        x = self.fc2(x)
        x = self.bn2(x)
        x = F.relu(x, inplace=True)
        x = self.dropout(x)
        x = self.fc3(x)
        return x


def count_trainable_params(model: nn.Module) -> int:
    return sum(p.numel() for p in model.parameters() if p.requires_grad)


def evaluate(model: nn.Module, data_loader, device: torch.device, criterion=None):
    model.eval()
    total_loss = 0.0
    total_correct = 0
    total_samples = 0
    with torch.no_grad():
        for inputs, targets in data_loader:
            inputs = inputs.to(device)
            targets = targets.to(device)
            outputs = model(inputs)
            if criterion is not None:
                loss = criterion(outputs, targets)
                total_loss += loss.item() * targets.size(0)
            preds = outputs.argmax(dim=1)
            total_correct += (preds == targets).sum().item()
            total_samples += targets.size(0)
    avg_loss = total_loss / total_samples if (criterion is not None and total_samples > 0) else 0.0
    acc = total_correct / total_samples if total_samples > 0 else 0.0
    return avg_loss, acc


class Solution:
    def solve(self, train_loader, val_loader, metadata: dict = None) -> torch.nn.Module:
        if metadata is None:
            metadata = {}

        # Device handling
        device_str = metadata.get("device", "cpu")
        device = torch.device(device_str)
        if device.type == "cuda" and not torch.cuda.is_available():
            device = torch.device("cpu")

        input_dim = int(metadata.get("input_dim", 384))
        num_classes = int(metadata.get("num_classes", 128))
        param_limit = int(metadata.get("param_limit", 200000))

        # Reproducibility
        torch.manual_seed(42)
        if torch.cuda.is_available():
            torch.cuda.manual_seed_all(42)

        # Build model within parameter limit, preferring larger hidden sizes
        hidden_candidates = [256, 224, 192, 160, 128, 96, 64]
        model = None
        for h in hidden_candidates:
            candidate = MLPNet(input_dim, num_classes, hidden_dim=h, dropout=0.25)
            params = count_trainable_params(candidate)
            if params <= param_limit:
                model = candidate
                break

        if model is None:
            # Fallback: simple linear classifier
            model = nn.Linear(input_dim, num_classes)

        # Safety check on parameter constraint
        if count_trainable_params(model) > param_limit:
            model = nn.Linear(input_dim, num_classes)

        model.to(device)

        # Training hyperparameters
        train_samples = metadata.get("train_samples", None)
        if train_samples is not None and train_samples <= 1024:
            max_epochs = 150
        else:
            max_epochs = 120
        min_epochs = 30
        patience = 25
        lr = 3e-3
        weight_decay = 1e-4

        # Loss with optional label smoothing
        try:
            criterion = nn.CrossEntropyLoss(label_smoothing=0.1)
        except TypeError:
            criterion = nn.CrossEntropyLoss()

        optimizer = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=weight_decay)
        scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(
            optimizer, T_max=max_epochs, eta_min=lr / 50.0
        )

        best_state = deepcopy(model.state_dict())
        best_val_acc = 0.0
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

            scheduler.step()

            _, val_acc = evaluate(model, val_loader, device, criterion)

            if val_acc > best_val_acc + 1e-4:
                best_val_acc = val_acc
                best_state = deepcopy(model.state_dict())
                epochs_no_improve = 0
            else:
                epochs_no_improve += 1

            if epoch + 1 >= min_epochs and epochs_no_improve >= patience:
                break

        model.load_state_dict(best_state)
        model.to(device)
        model.eval()
        return model