import torch
import torch.nn as nn
import torch.optim as optim
from copy import deepcopy
from typing import Dict, Any


class ResidualMLP(nn.Module):
    def __init__(self, input_dim: int, num_classes: int, hidden_dim: int = 256, dropout: float = 0.1):
        super().__init__()
        self.fc1 = nn.Linear(input_dim, hidden_dim)
        self.norm1 = nn.LayerNorm(hidden_dim)
        self.fc2 = nn.Linear(hidden_dim, hidden_dim)
        self.norm2 = nn.LayerNorm(hidden_dim)
        self.fc_out = nn.Linear(hidden_dim, num_classes)
        self.act = nn.GELU()
        self.dropout = nn.Dropout(dropout)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = x.view(x.size(0), -1)

        h1 = self.fc1(x)
        h1 = self.norm1(h1)
        h1 = self.act(h1)
        h1 = self.dropout(h1)

        residual = h1

        h2 = self.fc2(h1)
        h2 = self.norm2(h2)
        h2 = self.act(h2)
        h2 = self.dropout(h2)

        h2 = h2 + residual

        out = self.fc_out(h2)
        return out


class Solution:
    def _count_params(self, model: nn.Module) -> int:
        return sum(p.numel() for p in model.parameters() if p.requires_grad)

    def _build_model(self, input_dim: int, num_classes: int, param_limit: int) -> nn.Module:
        # Try decreasing hidden dimensions until under parameter limit
        for hidden_dim in [256, 192, 160, 128, 96, 64, 48, 32]:
            model = ResidualMLP(input_dim, num_classes, hidden_dim=hidden_dim, dropout=0.1)
            if self._count_params(model) <= param_limit:
                return model
        # Fallback to simple linear classifier if limit is extremely small
        model = nn.Linear(input_dim, num_classes)
        return model

    def _evaluate(self, model: nn.Module, loader, criterion: nn.Module, device: torch.device):
        model.eval()
        total_loss = 0.0
        correct = 0
        total = 0
        with torch.no_grad():
            for inputs, targets in loader:
                inputs = inputs.to(device)
                targets = targets.to(device).long()
                outputs = model(inputs)
                loss = criterion(outputs, targets)
                batch_size = targets.size(0)
                total_loss += loss.item() * batch_size
                preds = outputs.argmax(dim=1)
                correct += (preds == targets).sum().item()
                total += batch_size
        avg_loss = total_loss / total if total > 0 else 0.0
        accuracy = correct / total if total > 0 else 0.0
        return avg_loss, accuracy

    def solve(self, train_loader, val_loader, metadata: Dict[str, Any] = None) -> torch.nn.Module:
        if metadata is None:
            metadata = {}
        device_str = metadata.get("device", "cpu")
        device = torch.device(device_str)

        input_dim = int(metadata.get("input_dim", 384))
        num_classes = int(metadata.get("num_classes", 128))
        param_limit = int(metadata.get("param_limit", 200000))

        torch.manual_seed(42)

        model = self._build_model(input_dim, num_classes, param_limit)
        model.to(device)

        # Ensure parameter constraint is satisfied
        if self._count_params(model) > param_limit:
            # As an extra safeguard, fall back to linear model if somehow over limit
            model = nn.Linear(input_dim, num_classes).to(device)

        criterion = nn.CrossEntropyLoss()
        optimizer = optim.AdamW(model.parameters(), lr=2e-3, weight_decay=1e-2)

        max_epochs = 200
        patience = 30
        scheduler = optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=max_epochs, eta_min=1e-5)

        best_state = deepcopy(model.state_dict())
        best_val_acc = 0.0
        epochs_no_improve = 0

        for epoch in range(max_epochs):
            model.train()
            for inputs, targets in train_loader:
                inputs = inputs.to(device)
                targets = targets.to(device).long()

                optimizer.zero_grad()
                outputs = model(inputs)
                loss = criterion(outputs, targets)
                loss.backward()
                nn.utils.clip_grad_norm_(model.parameters(), max_norm=5.0)
                optimizer.step()

            _, val_acc = self._evaluate(model, val_loader, criterion, device)

            if val_acc > best_val_acc + 1e-4:
                best_val_acc = val_acc
                best_state = deepcopy(model.state_dict())
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
