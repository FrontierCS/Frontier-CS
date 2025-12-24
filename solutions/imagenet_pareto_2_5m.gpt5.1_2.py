import torch
import torch.nn as nn
import torch.optim as optim
import copy


class ResidualBlock(nn.Module):
    def __init__(self, dim: int, dropout: float = 0.1):
        super().__init__()
        self.linear = nn.Linear(dim, dim)
        self.bn = nn.BatchNorm1d(dim)
        self.act = nn.ReLU(inplace=True)
        self.dropout = nn.Dropout(dropout)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        out = self.linear(x)
        out = self.bn(out)
        out = self.act(out)
        out = self.dropout(out)
        return x + out


class MLPNet(nn.Module):
    def __init__(self, input_dim: int, num_classes: int, hidden1: int, hidden2: int, dropout: float = 0.1):
        super().__init__()
        self.fc_in = nn.Linear(input_dim, hidden1)
        self.bn_in = nn.BatchNorm1d(hidden1)
        self.act = nn.ReLU(inplace=True)
        self.dropout = nn.Dropout(dropout)

        self.res1 = ResidualBlock(hidden1, dropout=dropout)

        self.fc_mid = nn.Linear(hidden1, hidden2)
        self.bn_mid = nn.BatchNorm1d(hidden2)

        self.res2 = ResidualBlock(hidden2, dropout=dropout)

        self.fc_out = nn.Linear(hidden2, num_classes)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self.fc_in(x)
        x = self.bn_in(x)
        x = self.act(x)
        x = self.dropout(x)

        x = self.res1(x)

        x = self.fc_mid(x)
        x = self.bn_mid(x)
        x = self.act(x)
        x = self.dropout(x)

        x = self.res2(x)

        x = self.fc_out(x)
        return x


def build_model(input_dim: int, num_classes: int, param_limit: int = None) -> nn.Module:
    candidate_configs = [
        (1024, 512),
        (1024, 384),
        (768, 512),
        (768, 384),
        (512, 512),
        (512, 384),
        (384, 384),
        (384, 256),
    ]

    def count_params(m: nn.Module) -> int:
        return sum(p.numel() for p in m.parameters() if p.requires_grad)

    for h1, h2 in candidate_configs:
        model = MLPNet(input_dim, num_classes, hidden1=h1, hidden2=h2, dropout=0.1)
        if param_limit is None:
            return model
        if count_params(model) <= param_limit:
            return model

    # Fallback minimal model if param_limit is extremely low
    return nn.Sequential(nn.Linear(input_dim, num_classes))


class Solution:
    def _init_weights(self, m: nn.Module) -> None:
        if isinstance(m, nn.Linear):
            nn.init.kaiming_normal_(m.weight, nonlinearity="relu")
            if m.bias is not None:
                nn.init.zeros_(m.bias)
        elif isinstance(m, nn.BatchNorm1d):
            nn.init.ones_(m.weight)
            nn.init.zeros_(m.bias)

    def _evaluate(self, model: nn.Module, data_loader, device: torch.device, criterion: nn.Module) -> float:
        model.eval()
        correct = 0
        total = 0
        with torch.no_grad():
            for inputs, targets in data_loader:
                inputs = inputs.to(device)
                targets = targets.to(device)
                outputs = model(inputs)
                _ = criterion(outputs, targets)
                preds = outputs.argmax(dim=1)
                correct += (preds == targets).sum().item()
                total += targets.size(0)
        return float(correct) / float(total) if total > 0 else 0.0

    def _train(self, model: nn.Module, train_loader, val_loader, device: torch.device, epochs: int) -> None:
        criterion = nn.CrossEntropyLoss(label_smoothing=0.05)
        optimizer = optim.AdamW(model.parameters(), lr=1e-3, weight_decay=1e-4)
        scheduler = optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=epochs)

        best_state = copy.deepcopy(model.state_dict())
        best_val_acc = 0.0
        patience = max(20, epochs // 5)
        epochs_without_improve = 0

        for epoch in range(epochs):
            model.train()
            for inputs, targets in train_loader:
                inputs = inputs.to(device)
                targets = targets.to(device)

                optimizer.zero_grad()
                outputs = model(inputs)
                loss = criterion(outputs, targets)
                loss.backward()
                nn.utils.clip_grad_norm_(model.parameters(), max_norm=5.0)
                optimizer.step()

            scheduler.step()

            val_acc = self._evaluate(model, val_loader, device, criterion)
            if val_acc > best_val_acc:
                best_val_acc = val_acc
                best_state = copy.deepcopy(model.state_dict())
                epochs_without_improve = 0
            else:
                epochs_without_improve += 1
                if epochs_without_improve >= patience:
                    break

        model.load_state_dict(best_state)

    def solve(self, train_loader, val_loader, metadata: dict = None) -> torch.nn.Module:
        if metadata is None:
            metadata = {}

        seed = metadata.get("seed", 42)
        torch.manual_seed(seed)

        input_dim = metadata.get("input_dim", 384)
        num_classes = metadata.get("num_classes", 128)
        param_limit = metadata.get("param_limit", None)

        device_str = metadata.get("device", "cpu")
        device = torch.device(device_str)

        model = build_model(input_dim, num_classes, param_limit)
        model.apply(self._init_weights)
        model.to(device)

        train_samples = metadata.get("train_samples", None)
        if train_samples is None:
            try:
                train_samples = len(train_loader.dataset)
            except Exception:
                train_samples = 2048

        if train_samples <= 3000:
            epochs = 220
        elif train_samples <= 10000:
            epochs = 140
        else:
            epochs = 80

        self._train(model, train_loader, val_loader, device, epochs)

        return model
