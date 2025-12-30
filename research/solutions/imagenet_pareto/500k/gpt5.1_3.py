import torch
import torch.nn as nn
import torch.nn.functional as F
import copy
import math


def count_parameters(model: nn.Module) -> int:
    return sum(p.numel() for p in model.parameters() if p.requires_grad)


class ResidualMLP(nn.Module):
    def __init__(self, input_dim: int, num_classes: int, hidden_dim: int = 384,
                 dropout1: float = 0.2, dropout2: float = 0.3):
        super().__init__()
        self.fc1 = nn.Linear(input_dim, hidden_dim)
        self.bn1 = nn.BatchNorm1d(hidden_dim)

        self.fc2 = nn.Linear(hidden_dim, hidden_dim)
        self.bn2 = nn.BatchNorm1d(hidden_dim)

        self.fc3 = nn.Linear(hidden_dim, hidden_dim)
        self.bn3 = nn.BatchNorm1d(hidden_dim)

        self.dropout1 = nn.Dropout(dropout1)
        self.dropout2 = nn.Dropout(dropout2)
        self.dropout3 = nn.Dropout(dropout2)

        self.out = nn.Linear(hidden_dim, num_classes)

    def forward(self, x):
        x = self.fc1(x)
        x = self.bn1(x)
        x = F.gelu(x)
        x = self.dropout1(x)

        # Residual block 1
        residual = x
        out = self.fc2(x)
        out = self.bn2(out)
        out = F.gelu(out)
        out = self.dropout2(out)
        x = residual + out

        # Residual block 2
        residual = x
        out = self.fc3(x)
        out = self.bn3(out)
        out = F.gelu(out)
        out = self.dropout3(out)
        x = residual + out

        logits = self.out(x)
        return logits


class BaselineMLP(nn.Module):
    def __init__(self, input_dim: int, num_classes: int, hidden_dim: int = 384):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, num_classes),
        )

    def forward(self, x):
        return self.net(x)


class Solution:
    def _build_model(self, input_dim: int, num_classes: int, param_limit: int) -> nn.Module:
        # Try high-capacity residual MLP with various widths, respecting param budget
        hidden_dim_options = [384, 352, 320]
        for hidden_dim in hidden_dim_options:
            model = ResidualMLP(input_dim, num_classes, hidden_dim=hidden_dim)
            if count_parameters(model) <= param_limit:
                return model

        # Fallback to simple 2-layer MLP; adapt width if needed for very small param_limit
        # Params for 2-layer MLP: (input_dim + 1)*H + (H + 1)*num_classes
        max_hidden = min(384, param_limit)  # upper bound
        best_hidden = 16
        for H in range(max_hidden, 15, -16):
            params = (input_dim + 1) * H + (H + 1) * num_classes
            if params <= param_limit:
                best_hidden = H
                break
        return BaselineMLP(input_dim, num_classes, hidden_dim=best_hidden)

    def solve(self, train_loader, val_loader, metadata: dict = None) -> torch.nn.Module:
        """
        Train a model and return it.
        
        Args:
            train_loader: PyTorch DataLoader with training data
            val_loader: PyTorch DataLoader with validation data
            metadata: Dict with keys:
                - num_classes: int (128)
                - input_dim: int (384)
                - param_limit: int (500,000)
                - baseline_accuracy: float (0.72)
                - train_samples: int
                - val_samples: int
                - test_samples: int
                - device: str ("cpu")
        
        Returns:
            Trained torch.nn.Module ready for evaluation
        """
        if metadata is None:
            metadata = {}

        input_dim = int(metadata.get("input_dim", 384))
        num_classes = int(metadata.get("num_classes", 128))
        param_limit = int(metadata.get("param_limit", 500_000))
        device_str = metadata.get("device", "cpu")
        device = torch.device(device_str if torch.cuda.is_available() and "cuda" in device_str else "cpu")

        torch.manual_seed(42)

        model = self._build_model(input_dim, num_classes, param_limit)
        model.to(device)

        # Safety check: ensure we respect param budget
        if count_parameters(model) > param_limit:
            # As a last resort, use a very small baseline MLP
            hidden_dim = max(16, min(128, param_limit // (input_dim + num_classes + 2)))
            model = BaselineMLP(input_dim, num_classes, hidden_dim=hidden_dim).to(device)

        criterion = nn.CrossEntropyLoss(label_smoothing=0.1)
        optimizer = torch.optim.AdamW(model.parameters(), lr=3e-3, weight_decay=1e-2)

        # Scheduler on validation loss
        scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
            optimizer, mode="min", factor=0.5, patience=5, min_lr=1e-5, verbose=False
        )

        # Training settings
        train_samples = metadata.get("train_samples", None)
        if train_samples is not None and train_samples <= 4096:
            max_epochs = 160
        else:
            max_epochs = 120

        early_stopping_patience = 25

        best_val_acc = 0.0
        best_state = copy.deepcopy(model.state_dict())
        epochs_no_improve = 0

        for epoch in range(max_epochs):
            model.train()
            for inputs, targets in train_loader:
                inputs = inputs.to(device).float()
                targets = targets.to(device, dtype=torch.long)

                optimizer.zero_grad()
                outputs = model(inputs)
                loss = criterion(outputs, targets)
                loss.backward()
                torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=5.0)
                optimizer.step()

            # Validation
            model.eval()
            val_loss = 0.0
            correct = 0
            total = 0
            with torch.no_grad():
                for inputs, targets in val_loader:
                    inputs = inputs.to(device).float()
                    targets = targets.to(device, dtype=torch.long)

                    outputs = model(inputs)
                    loss = criterion(outputs, targets)
                    val_loss += loss.item() * targets.size(0)

                    preds = outputs.argmax(dim=1)
                    correct += (preds == targets).sum().item()
                    total += targets.size(0)

            if total > 0:
                val_loss /= total
                val_acc = correct / total
            else:
                val_loss = 0.0
                val_acc = 0.0

            scheduler.step(val_loss)

            if val_acc > best_val_acc + 1e-4:
                best_val_acc = val_acc
                best_state = copy.deepcopy(model.state_dict())
                epochs_no_improve = 0
            else:
                epochs_no_improve += 1
                if epochs_no_improve >= early_stopping_patience:
                    break

        model.load_state_dict(best_state)
        model.to("cpu")
        model.eval()
        return model