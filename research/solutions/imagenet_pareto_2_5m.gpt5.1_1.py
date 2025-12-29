import math
import torch
import torch.nn as nn
import torch.nn.functional as F


class ResidualMLP(nn.Module):
    def __init__(self, input_dim: int, num_classes: int, hidden_dim: int, dropout: float = 0.1):
        super().__init__()
        self.input_bn = nn.BatchNorm1d(input_dim)
        self.fc1 = nn.Linear(input_dim, hidden_dim)
        self.bn1 = nn.BatchNorm1d(hidden_dim)

        self.fc2 = nn.Linear(hidden_dim, hidden_dim)
        self.bn2 = nn.BatchNorm1d(hidden_dim)

        self.fc3 = nn.Linear(hidden_dim, hidden_dim)
        self.bn3 = nn.BatchNorm1d(hidden_dim)

        self.fc_out = nn.Linear(hidden_dim, num_classes)

        self.dropout = nn.Dropout(p=dropout)
        self.act = nn.GELU()

    def forward(self, x):
        x = self.input_bn(x)
        x = self.fc1(x)
        x = self.bn1(x)
        x = self.act(x)
        x = self.dropout(x)

        residual = x
        out = self.fc2(x)
        out = self.bn2(out)
        out = self.act(out)
        out = self.dropout(out)
        x = residual + out

        residual = x
        out = self.fc3(x)
        out = self.bn3(out)
        out = self.act(out)
        out = self.dropout(out)
        x = residual + out

        logits = self.fc_out(x)
        return logits


class Solution:
    def _build_model(self, input_dim: int, num_classes: int, param_limit: int | None) -> nn.Module:
        if param_limit is None or param_limit <= 0:
            hidden_dim = 512
            model = ResidualMLP(input_dim, num_classes, hidden_dim)
            return model

        B = input_dim + num_classes + 9
        C = 2 * input_dim + num_classes
        L = float(param_limit)
        D = B * B + 8.0 * (L - C)
        if D <= 0:
            hidden_est = 256
        else:
            hidden_est = int((math.sqrt(D) - B) / 4.0)

        hidden_est = max(hidden_est, 64)

        hidden_dim = hidden_est
        while hidden_dim >= 32:
            model = ResidualMLP(input_dim, num_classes, hidden_dim)
            param_count = sum(p.numel() for p in model.parameters() if p.requires_grad)
            if param_count <= param_limit:
                return model
            hidden_dim -= 1

        hidden_dim = 32
        model = ResidualMLP(input_dim, num_classes, hidden_dim)
        return model

    def solve(self, train_loader, val_loader, metadata: dict = None) -> torch.nn.Module:
        if metadata is None:
            raise ValueError("metadata must be provided")

        input_dim = int(metadata.get("input_dim", 384))
        num_classes = int(metadata.get("num_classes", 128))
        param_limit = int(metadata.get("param_limit", 2500000))
        device_str = metadata.get("device", "cpu")
        device = torch.device(device_str if torch.cuda.is_available() or device_str == "cpu" else "cpu")

        torch.manual_seed(42)

        model = self._build_model(input_dim, num_classes, param_limit)
        model.to(device)

        criterion = nn.CrossEntropyLoss(label_smoothing=0.1)
        optimizer = torch.optim.AdamW(model.parameters(), lr=5e-4, weight_decay=1e-2)
        num_epochs = 200
        scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=num_epochs, eta_min=1e-5)

        best_val_acc = 0.0
        best_state = None
        patience = 40
        epochs_no_improve = 0

        for epoch in range(num_epochs):
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

            model.eval()
            correct = 0
            total = 0
            with torch.no_grad():
                for inputs, targets in val_loader:
                    inputs = inputs.to(device)
                    targets = targets.to(device)
                    outputs = model(inputs)
                    loss = criterion(outputs, targets)
                    preds = outputs.argmax(dim=1)
                    correct += (preds == targets).sum().item()
                    total += targets.numel()
            val_acc = correct / total if total > 0 else 0.0

            if val_acc > best_val_acc + 1e-4:
                best_val_acc = val_acc
                best_state = {k: v.cpu().clone() for k, v in model.state_dict().items()}
                epochs_no_improve = 0
            else:
                epochs_no_improve += 1

            scheduler.step()

            if epochs_no_improve >= patience:
                break

        if best_state is not None:
            model.load_state_dict(best_state)

        model.to(device)
        model.eval()
        return model