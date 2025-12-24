import torch
import torch.nn as nn
import torch.nn.functional as F
import copy
import math


def count_parameters(model: nn.Module) -> int:
    return sum(p.numel() for p in model.parameters() if p.requires_grad)


class MLPNet(nn.Module):
    def __init__(self, input_dim: int, num_classes: int, hidden_dims, dropout: float = 0.15):
        super().__init__()
        if isinstance(hidden_dims, int):
            hidden_dims = [hidden_dims]
        self.hidden_dims = hidden_dims

        dims = [input_dim] + hidden_dims + [num_classes]

        self.fcs = nn.ModuleList()
        for in_dim, out_dim in zip(dims[:-1], dims[1:]):
            self.fcs.append(nn.Linear(in_dim, out_dim))

        self.bns = nn.ModuleList()
        for h in hidden_dims:
            self.bns.append(nn.BatchNorm1d(h))

        self.dropout = nn.Dropout(dropout)

    def forward(self, x):
        # Hidden layers
        for i in range(len(self.hidden_dims)):
            x = self.fcs[i](x)
            x = self.bns[i](x)
            x = F.relu(x, inplace=True)
            x = self.dropout(x)
        # Output layer
        x = self.fcs[-1](x)
        return x


class Solution:
    def _build_model(self, input_dim, num_classes, param_limit):
        base_hidden = [512, 320, 256]
        scale = 1.0
        best_model = None

        for _ in range(15):
            hidden_dims = [max(16, int(round(h * scale))) for h in base_hidden]
            # Ensure strictly positive and non-zero
            hidden_dims = [h if h > 0 else 16 for h in hidden_dims]

            model = MLPNet(input_dim, num_classes, hidden_dims, dropout=0.15)
            params = count_parameters(model)
            if params <= param_limit:
                best_model = model
                break
            scale *= 0.8

        if best_model is not None:
            return best_model

        # Fallback: single hidden layer MLP sized to fit param budget
        # Approximate hidden size from quadratic formula on params:
        # params ≈ input_dim*h + h*num_classes + h + num_classes
        # => h ≈ (param_limit - num_classes) / (input_dim + num_classes + 1)
        approx_h = max(
            16,
            min(
                512,
                (param_limit - num_classes) // (input_dim + num_classes + 2)
                if (input_dim + num_classes + 2) > 0
                else 64,
            ),
        )
        model = MLPNet(input_dim, num_classes, [int(approx_h)], dropout=0.15)
        # Final safety: if still above limit, reduce further
        while count_parameters(model) > param_limit and approx_h > 16:
            approx_h = max(16, approx_h // 2)
            model = MLPNet(input_dim, num_classes, [int(approx_h)], dropout=0.15)
        return model

    def _evaluate_accuracy(self, model, data_loader, device):
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
        if total == 0:
            return 0.0
        return correct / total

    def solve(self, train_loader, val_loader, metadata: dict = None) -> torch.nn.Module:
        if metadata is None:
            metadata = {}
        input_dim = int(metadata.get("input_dim", 384))
        num_classes = int(metadata.get("num_classes", 128))
        param_limit = int(metadata.get("param_limit", 500_000))
        device_str = metadata.get("device", "cpu")
        device = torch.device(device_str if torch.cuda.is_available() or device_str == "cpu" else "cpu")

        torch.manual_ace = 0  # no-op to avoid unused variable warnings if any tooling inspects
        torch.manual_seed(42)

        model = self._build_model(input_dim, num_classes, param_limit)
        model.to(device)

        # Final safety check on parameter budget
        if count_parameters(model) > param_limit:
            # As a last resort, minimal linear classifier
            model = nn.Linear(input_dim, num_classes)
            model.to(device)

        train_samples = metadata.get("train_samples", None)
        if train_samples is None:
            try:
                train_samples = len(train_loader.dataset)
            except Exception:
                train_samples = 2048

        if train_samples <= 4096:
            max_epochs = 220
            patience = 35
        elif train_samples <= 10000:
            max_epochs = 140
            patience = 30
        else:
            max_epochs = 100
            patience = 25

        lr = 0.0025
        weight_decay = 1e-4

        optimizer = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=weight_decay)
        criterion = nn.CrossEntropyLoss(label_smoothing=0.05)

        best_state = copy.deepcopy(model.state_dict())
        best_val_acc = 0.0
        bad_epochs = 0

        for epoch in range(max_epochs):
            model.train()
            for inputs, targets in train_loader:
                inputs = inputs.to(device)
                targets = targets.to(device)

                optimizer.zero_grad(set_to_none=True)
                outputs = model(inputs)
                loss = criterion(outputs, targets)
                loss.backward()
                nn.utils.clip_grad_norm_(model.parameters(), max_norm=5.0)
                optimizer.step()

            if val_loader is not None:
                val_acc = self._evaluate_accuracy(model, val_loader, device)
                if val_acc > best_val_acc + 1e-4:
                    best_val_acc = val_acc
                    best_state = copy.deepcopy(model.state_dict())
                    bad_epochs = 0
                else:
                    bad_epochs += 1
                    if bad_epochs >= patience:
                        break

        model.load_state_dict(best_state)
        model.to(device)
        model.eval()
        return model
