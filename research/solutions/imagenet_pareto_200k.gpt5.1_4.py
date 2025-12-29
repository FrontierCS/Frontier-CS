import torch
import torch.nn as nn
import torch.nn.functional as F
import copy
import random


def count_parameters(model: nn.Module) -> int:
    return sum(p.numel() for p in model.parameters() if p.requires_grad)


class MLPNet(nn.Module):
    def __init__(self, input_dim: int, num_classes: int, hidden_dim: int = 256, dropout: float = 0.2):
        super().__init__()
        self.fc1 = nn.Linear(input_dim, hidden_dim)
        self.ln1 = nn.LayerNorm(hidden_dim)
        self.fc2 = nn.Linear(hidden_dim, hidden_dim)
        self.ln2 = nn.LayerNorm(hidden_dim)
        self.fc3 = nn.Linear(hidden_dim, num_classes)
        self.dropout = nn.Dropout(dropout)
        self.activation = nn.ReLU(inplace=True)
        self._init_weights()

    def _init_weights(self):
        for m in self.modules():
            if isinstance(m, nn.Linear):
                nn.init.kaiming_normal_(m.weight, nonlinearity="relu")
                if m.bias is not None:
                    nn.init.zeros_(m.bias)
            elif isinstance(m, nn.LayerNorm):
                if m.elementwise_affine:
                    nn.init.ones_(m.weight)
                    nn.init.zeros_(m.bias)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self.fc1(x)
        x = self.ln1(x)
        x = self.activation(x)
        x = self.dropout(x)
        residual = x
        x = self.fc2(x)
        x = self.ln2(x)
        x = self.activation(x)
        x = self.dropout(x)
        x = x + residual
        x = self.fc3(x)
        return x


def build_model(input_dim: int, num_classes: int, param_limit: int) -> nn.Module:
    for hidden in range(512, 31, -16):
        model = MLPNet(input_dim, num_classes, hidden_dim=hidden, dropout=0.2)
        if count_parameters(model) <= param_limit:
            return model
    for hidden in range(512, 31, -16):
        model = nn.Sequential(
            nn.Linear(input_dim, hidden),
            nn.ReLU(inplace=True),
            nn.Linear(hidden, num_classes),
        )
        if count_parameters(model) <= param_limit:
            return model
    return nn.Linear(input_dim, num_classes)


def evaluate_accuracy(model: nn.Module, data_loader, device: torch.device) -> float:
    model.eval()
    correct = 0
    total = 0
    with torch.no_grad():
        for inputs, targets in data_loader:
            inputs = inputs.to(device, dtype=torch.float32)
            targets = targets.to(device, dtype=torch.long)
            outputs = model(inputs)
            preds = outputs.argmax(dim=1)
            correct += (preds == targets).sum().item()
            total += targets.numel()
    if total == 0:
        return 0.0
    return correct / total


class Solution:
    def solve(self, train_loader, val_loader, metadata: dict = None) -> torch.nn.Module:
        if metadata is None:
            metadata = {}

        input_dim = int(metadata.get("input_dim", 384))
        num_classes = int(metadata.get("num_classes", 128))
        param_limit = int(metadata.get("param_limit", 200000))
        device_str = metadata.get("device", "cpu")
        if device_str == "cuda" and not torch.cuda.is_available():
            device_str = "cpu"
        device = torch.device(device_str)

        torch.manual_seed(42)
        random.seed(42)

        model = build_model(input_dim, num_classes, param_limit)
        if count_parameters(model) > param_limit:
            model = nn.Linear(input_dim, num_classes)
        model.to(device)

        train_samples = metadata.get("train_samples", None)
        if train_samples is not None and train_samples > 0:
            base_epochs = 180
            epochs = int(base_epochs * (2048.0 / float(train_samples)))
            epochs = max(80, min(300, epochs))
        else:
            epochs = 180

        lr = 3e-3
        weight_decay = 1e-4

        criterion = nn.CrossEntropyLoss(label_smoothing=0.1)
        optimizer = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=weight_decay)
        scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(
            optimizer, T_max=epochs, eta_min=lr * 0.1
        )

        best_state = copy.deepcopy(model.state_dict())
        best_val_acc = -1.0

        for _ in range(epochs):
            model.train()
            for inputs, targets in train_loader:
                inputs = inputs.to(device, dtype=torch.float32)
                targets = targets.to(device, dtype=torch.long)

                optimizer.zero_grad(set_to_none=True)
                outputs = model(inputs)
                loss = criterion(outputs, targets)
                loss.backward()
                torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=5.0)
                optimizer.step()

            scheduler.step()

            if val_loader is not None:
                val_acc = evaluate_accuracy(model, val_loader, device)
                if val_acc > best_val_acc:
                    best_val_acc = val_acc
                    best_state = copy.deepcopy(model.state_dict())

        if best_state is not None:
            model.load_state_dict(best_state)

        model.to(device)
        model.eval()
        return model