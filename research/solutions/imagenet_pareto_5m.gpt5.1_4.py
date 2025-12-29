import math
import torch
import torch.nn as nn
import torch.nn.functional as F


def estimate_mlp_params(input_dim: int, hidden_dim: int, num_classes: int) -> int:
    params = 0
    # Input BatchNorm
    params += 2 * input_dim
    # fc1 + bn1
    params += input_dim * hidden_dim + hidden_dim
    params += 2 * hidden_dim
    # fc2 + bn2
    params += hidden_dim * hidden_dim + hidden_dim
    params += 2 * hidden_dim
    # fc3 + bn3
    params += hidden_dim * hidden_dim + hidden_dim
    params += 2 * hidden_dim
    # fc_out
    params += hidden_dim * num_classes + num_classes
    return params


def choose_hidden_dim(input_dim: int, num_classes: int, param_limit: int) -> int:
    if param_limit is None:
        return min(1024, max(256, input_dim * 2))

    hidden = 1
    # Increase hidden until params would exceed limit
    while estimate_mlp_params(input_dim, hidden * 2, num_classes) <= param_limit:
        hidden *= 2

    lo = hidden
    hi = hidden * 2
    # Binary search for max hidden_dim within param limit
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if estimate_mlp_params(input_dim, mid, num_classes) <= param_limit:
            lo = mid
        else:
            hi = mid - 1
    return max(1, lo)


class MLPNet(nn.Module):
    def __init__(self, input_dim: int, hidden_dim: int, num_classes: int, dropout: float = 0.2):
        super().__init__()
        self.input_bn = nn.BatchNorm1d(input_dim)
        self.fc1 = nn.Linear(input_dim, hidden_dim)
        self.bn1 = nn.BatchNorm1d(hidden_dim)
        self.fc2 = nn.Linear(hidden_dim, hidden_dim)
        self.bn2 = nn.BatchNorm1d(hidden_dim)
        self.fc3 = nn.Linear(hidden_dim, hidden_dim)
        self.bn3 = nn.BatchNorm1d(hidden_dim)
        self.dropout = nn.Dropout(dropout)
        self.fc_out = nn.Linear(hidden_dim, num_classes)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self.input_bn(x)
        x = self.fc1(x)
        x = self.bn1(x)
        x = F.gelu(x)
        x = self.dropout(x)
        h1 = x

        x = self.fc2(x)
        x = self.bn2(x)
        x = F.gelu(x)
        x = self.dropout(x)
        h2 = x

        x = self.fc3(x)
        x = self.bn3(x)
        x = F.gelu(x)
        x = self.dropout(x)

        x = x + h1 + h2
        x = self.fc_out(x)
        return x


class LinearNet(nn.Module):
    def __init__(self, input_dim: int, num_classes: int):
        super().__init__()
        self.fc = nn.Linear(input_dim, num_classes)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.fc(x)


class Solution:
    def solve(self, train_loader, val_loader, metadata: dict = None) -> torch.nn.Module:
        if metadata is None:
            metadata = {}

        input_dim = int(metadata.get("input_dim", 384))
        num_classes = int(metadata.get("num_classes", 128))
        param_limit = metadata.get("param_limit", None)
        device = metadata.get("device", "cpu")

        # Model selection based on parameter budget
        if param_limit is not None:
            min_mlp_params = estimate_mlp_params(input_dim, 1, num_classes)
            linear_params = input_dim * num_classes + num_classes
            if param_limit < min_mlp_params:
                # Fallback to linear model if MLP cannot fit
                model = LinearNet(input_dim, num_classes)
            else:
                hidden_dim = choose_hidden_dim(input_dim, num_classes, param_limit)
                model = MLPNet(input_dim, hidden_dim, num_classes, dropout=0.2)
                # Safety check to ensure we do not exceed the parameter limit
                current_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
                if current_params > param_limit:
                    while hidden_dim > 1 and current_params > param_limit:
                        hidden_dim -= 1
                        model = MLPNet(input_dim, hidden_dim, num_classes, dropout=0.2)
                        current_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
        else:
            hidden_dim = min(1024, max(256, input_dim * 2))
            model = MLPNet(input_dim, hidden_dim, num_classes, dropout=0.2)

        model.to(device)

        # Training setup
        criterion = nn.CrossEntropyLoss(label_smoothing=0.1)
        optimizer = torch.optim.AdamW(model.parameters(), lr=1e-3, weight_decay=1e-4)

        max_epochs = 200
        min_epochs = 40
        early_stop_patience = 25

        scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
            optimizer,
            mode="max",
            factor=0.5,
            patience=5,
            threshold=1e-4,
            min_lr=1e-5,
            verbose=False,
        )

        best_state_dict = None
        best_val_acc = -float("inf")
        epochs_no_improve = 0

        for epoch in range(max_epochs):
            # Training phase
            model.train()
            total_loss = 0.0
            total_correct = 0
            total_samples = 0

            for batch in train_loader:
                if isinstance(batch, (list, tuple)):
                    inputs, targets = batch
                else:
                    inputs = batch["inputs"] if "inputs" in batch else batch["input"]
                    targets = batch["targets"] if "targets" in batch else batch["target"]

                inputs = inputs.to(device, dtype=torch.float32)
                targets = targets.to(device, dtype=torch.long)

                optimizer.zero_grad(set_to_none=True)
                outputs = model(inputs)
                loss = criterion(outputs, targets)
                loss.backward()
                optimizer.step()

                batch_size = targets.size(0)
                total_loss += loss.item() * batch_size
                preds = outputs.argmax(dim=1)
                total_correct += (preds == targets).sum().item()
                total_samples += batch_size

            train_loss = total_loss / max(total_samples, 1)
            train_acc = total_correct / max(total_samples, 1)

            # Validation phase
            if val_loader is not None:
                model.eval()
                val_loss = 0.0
                val_correct = 0
                val_total = 0

                with torch.no_grad():
                    for batch in val_loader:
                        if isinstance(batch, (list, tuple)):
                            inputs, targets = batch
                        else:
                            inputs = batch["inputs"] if "inputs" in batch else batch["input"]
                            targets = batch["targets"] if "targets" in batch else batch["target"]

                        inputs = inputs.to(device, dtype=torch.float32)
                        targets = targets.to(device, dtype=torch.long)

                        outputs = model(inputs)
                        loss = criterion(outputs, targets)

                        batch_size = targets.size(0)
                        val_loss += loss.item() * batch_size
                        preds = outputs.argmax(dim=1)
                        val_correct += (preds == targets).sum().item()
                        val_total += batch_size

                val_loss /= max(val_total, 1)
                val_acc = val_correct / max(val_total, 1)

                scheduler.step(val_acc)

                if val_acc > best_val_acc + 1e-5:
                    best_val_acc = val_acc
                    best_state_dict = {k: v.cpu().clone() for k, v in model.state_dict().items()}
                    epochs_no_improve = 0
                else:
                    epochs_no_improve += 1

                if epoch + 1 >= min_epochs and epochs_no_improve >= early_stop_patience:
                    break
            else:
                scheduler.step(train_acc)

        if best_state_dict is not None:
            model.load_state_dict(best_state_dict)

        model.to("cpu")
        return model