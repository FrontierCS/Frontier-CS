import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.optim.lr_scheduler import CosineAnnealingLR
import copy


class HighCapacityNet(nn.Module):
    def __init__(self, input_dim: int, num_classes: int, dropout: float = 0.15):
        super().__init__()
        hidden1 = 304
        hidden2 = 176

        self.ln_in = nn.LayerNorm(input_dim)
        self.fc1 = nn.Linear(input_dim, hidden1)
        self.bn1 = nn.BatchNorm1d(hidden1)
        self.fc2 = nn.Linear(hidden1, hidden2)
        self.bn2 = nn.BatchNorm1d(hidden2)
        self.fc3 = nn.Linear(hidden2, num_classes)
        self.dropout = nn.Dropout(dropout)

    def forward(self, x):
        x = self.ln_in(x)
        x = self.fc1(x)
        x = self.bn1(x)
        x = F.gelu(x)
        x = self.dropout(x)
        x = self.fc2(x)
        x = self.bn2(x)
        x = F.gelu(x)
        x = self.dropout(x)
        x = self.fc3(x)
        return x


class BaselineNet(nn.Module):
    def __init__(self, input_dim: int, num_classes: int, hidden_dim: int = 256, dropout: float = 0.1):
        super().__init__()
        self.fc1 = nn.Linear(input_dim, hidden_dim)
        self.bn1 = nn.BatchNorm1d(hidden_dim)
        self.fc2 = nn.Linear(hidden_dim, num_classes)
        self.dropout = nn.Dropout(dropout)

    def forward(self, x):
        x = self.fc1(x)
        x = self.bn1(x)
        x = F.gelu(x)
        x = self.dropout(x)
        x = self.fc2(x)
        return x


class Solution:
    def count_params(self, model: nn.Module) -> int:
        return sum(p.numel() for p in model.parameters() if p.requires_grad)

    def evaluate(self, model: nn.Module, data_loader, device: torch.device) -> float:
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
                total += targets.size(0)
        return correct / total if total > 0 else 0.0

    def solve(self, train_loader, val_loader, metadata: dict = None) -> torch.nn.Module:
        if metadata is not None:
            input_dim = int(metadata.get("input_dim", 384))
            num_classes = int(metadata.get("num_classes", 128))
            param_limit = int(metadata.get("param_limit", 200000))
            device_str = metadata.get("device", "cpu")
        else:
            first_x, first_y = next(iter(train_loader))
            input_dim = first_x.shape[1]
            num_classes = int(torch.max(first_y).item()) + 1
            param_limit = 200000
            device_str = "cpu"

        device = torch.device(device_str)

        torch.manual_seed(42)

        model = HighCapacityNet(input_dim, num_classes)
        if self.count_params(model) > param_limit:
            model = BaselineNet(input_dim, num_classes, hidden_dim=256)

        model.to(device)

        criterion = nn.CrossEntropyLoss(label_smoothing=0.1)
        optimizer = torch.optim.AdamW(model.parameters(), lr=3e-3, weight_decay=1e-2)
        max_epochs = 200
        patience = 30
        scheduler = CosineAnnealingLR(optimizer, T_max=max_epochs, eta_min=1e-5)

        best_state = copy.deepcopy(model.state_dict())
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
                optimizer.step()

            val_acc = self.evaluate(model, val_loader, device)

            if val_acc > best_val_acc + 1e-4:
                best_val_acc = val_acc
                best_state = copy.deepcopy(model.state_dict())
                epochs_no_improve = 0
            else:
                epochs_no_improve += 1
                if epochs_no_improve >= patience:
                    scheduler.step()
                    break

            scheduler.step()

        model.load_state_dict(best_state)
        model.to(device)
        model.eval()
        return model
