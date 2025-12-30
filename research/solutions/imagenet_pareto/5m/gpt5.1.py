import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.optim import AdamW
from torch.optim.lr_scheduler import CosineAnnealingLR
import copy


class MLPResNet(nn.Module):
    def __init__(self, input_dim, num_classes, hidden_dim=1024, num_layers=6, dropout=0.2):
        super().__init__()
        self.hidden_dim = hidden_dim
        self.num_layers = num_layers

        self.input_layer = nn.Linear(input_dim, hidden_dim)
        self.input_bn = nn.BatchNorm1d(hidden_dim)

        # num_layers hidden layers total (including first), so we add num_layers-1 more
        self.hidden_layers = nn.ModuleList(
            [nn.Linear(hidden_dim, hidden_dim) for _ in range(num_layers - 1)]
        )
        self.hidden_bns = nn.ModuleList(
            [nn.BatchNorm1d(hidden_dim) for _ in range(num_layers - 1)]
        )

        self.output_layer = nn.Linear(hidden_dim, num_classes)

        self.dropout = nn.Dropout(dropout)
        self.activation = nn.ReLU(inplace=True)

    def forward(self, x):
        x = self.input_layer(x)
        x = self.input_bn(x)
        x = self.activation(x)
        x = self.dropout(x)

        for layer, bn in zip(self.hidden_layers, self.hidden_bns):
            residual = x
            out = layer(x)
            out = bn(out)
            out = self.activation(out)
            out = self.dropout(out)
            x = out + residual

        x = self.output_layer(x)
        return x


def count_params(model: nn.Module) -> int:
    return sum(p.numel() for p in model.parameters() if p.requires_grad)


class Solution:
    def _build_model(self, input_dim: int, num_classes: int, param_limit: int) -> nn.Module:
        # Fixed depth, search for maximal width under parameter budget
        num_layers = 6
        low, high = 64, 4096
        best_model = None
        best_params = 0

        while low <= high:
            mid = (low + high) // 2
            candidate = MLPResNet(
                input_dim=input_dim,
                num_classes=num_classes,
                hidden_dim=mid,
                num_layers=num_layers,
                dropout=0.2,
            )
            n_params = count_params(candidate)
            if n_params <= param_limit:
                best_model = candidate
                best_params = n_params
                low = mid + 1
            else:
                high = mid - 1

        if best_model is None:
            best_model = nn.Sequential(nn.Linear(input_dim, num_classes))
            # This should always be under the limit in this problem setup

        return best_model

    def solve(self, train_loader, val_loader, metadata: dict = None) -> torch.nn.Module:
        if metadata is None:
            metadata = {}

        torch.manual_seed(42)

        device_str = metadata.get("device", "cpu")
        device = torch.device(device_str)

        input_dim = int(metadata.get("input_dim", 384))
        num_classes = int(metadata.get("num_classes", 128))
        param_limit = int(metadata.get("param_limit", 5_000_000))

        model = self._build_model(input_dim, num_classes, param_limit)
        model.to(device)

        # Safety check on parameter count
        if count_params(model) > param_limit:
            # Fallback minimal model if something went wrong
            model = nn.Sequential(nn.Linear(input_dim, num_classes)).to(device)

        # Loss with label smoothing if supported
        try:
            criterion = nn.CrossEntropyLoss(label_smoothing=0.1)
        except TypeError:
            criterion = nn.CrossEntropyLoss()

        optimizer = AdamW(model.parameters(), lr=1e-3, weight_decay=1e-2)

        max_epochs = 200
        patience = 30
        scheduler = CosineAnnealingLR(optimizer, T_max=max_epochs, eta_min=1e-5)

        best_val_acc = 0.0
        best_state = copy.deepcopy(model.state_dict())
        epochs_no_improve = 0

        for epoch in range(max_epochs):
            model.train()
            for inputs, targets in train_loader:
                inputs = inputs.to(device, non_blocking=True)
                targets = targets.to(device, non_blocking=True)

                if inputs.dtype != torch.float32:
                    inputs = inputs.float()

                optimizer.zero_grad(set_to_none=True)
                outputs = model(inputs)
                loss = criterion(outputs, targets)
                loss.backward()
                nn.utils.clip_grad_norm_(model.parameters(), max_norm=5.0)
                optimizer.step()

            # Validation
            model.eval()
            correct = 0
            total = 0
            val_loss = 0.0
            with torch.no_grad():
                for inputs, targets in val_loader:
                    inputs = inputs.to(device, non_blocking=True)
                    targets = targets.to(device, non_blocking=True)

                    if inputs.dtype != torch.float32:
                        inputs = inputs.float()

                    outputs = model(inputs)
                    loss = criterion(outputs, targets)
                    val_loss += loss.item() * targets.size(0)

                    preds = outputs.argmax(dim=1)
                    correct += (preds == targets).sum().item()
                    total += targets.size(0)

            val_acc = correct / total if total > 0 else 0.0

            if val_acc > best_val_acc + 1e-4:
                best_val_acc = val_acc
                best_state = copy.deepcopy(model.state_dict())
                epochs_no_improve = 0
            else:
                epochs_no_improve += 1

            scheduler.step()

            if epochs_no_improve >= patience:
                break

        model.load_state_dict(best_state)
        model.to(device)
        model.eval()
        return model