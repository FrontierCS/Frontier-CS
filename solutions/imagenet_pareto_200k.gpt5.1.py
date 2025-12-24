import torch
import torch.nn as nn
import torch.optim as optim


def count_parameters(model: nn.Module) -> int:
    return sum(p.numel() for p in model.parameters() if p.requires_grad)


class MLPNet(nn.Module):
    def __init__(self, input_dim: int, num_classes: int, hidden_dim: int = 256, dropout: float = 0.1):
        super().__init__()
        self.fc1 = nn.Linear(input_dim, hidden_dim)
        self.bn1 = nn.BatchNorm1d(hidden_dim)
        self.fc2 = nn.Linear(hidden_dim, hidden_dim)
        self.bn2 = nn.BatchNorm1d(hidden_dim)
        self.fc_out = nn.Linear(hidden_dim, num_classes)
        self.act = nn.ReLU(inplace=True)
        self.drop1 = nn.Dropout(dropout)
        self.drop2 = nn.Dropout(dropout)

    def forward(self, x):
        x = self.fc1(x)
        x = self.bn1(x)
        x = self.act(x)
        x = self.drop1(x)
        x = self.fc2(x)
        x = self.bn2(x)
        x = self.act(x)
        x = self.drop2(x)
        x = self.fc_out(x)
        return x


class Solution:
    def _build_model(self, input_dim: int, num_classes: int, param_limit: int) -> nn.Module:
        # Choose largest hidden_dim from candidates that keeps params <= param_limit
        candidate_hidden = [512, 384, 320, 288, 256, 224, 192, 160, 128, 96, 64, 48, 32, 24, 16]
        chosen_hidden = 16
        chosen_model = None
        for h in candidate_hidden:
            model = MLPNet(input_dim=input_dim, num_classes=num_classes, hidden_dim=h, dropout=0.1)
            if count_parameters(model) <= param_limit:
                chosen_hidden = h
                chosen_model = model
                break
        if chosen_model is None:
            # Fallback minimal model if something unexpected happens
            chosen_model = MLPNet(input_dim=input_dim, num_classes=num_classes, hidden_dim=16, dropout=0.0)
        return chosen_model

    def _evaluate(self, model: nn.Module, data_loader, device, criterion=None):
        model.eval()
        total_loss = 0.0
        correct = 0
        total = 0
        with torch.no_grad():
            for inputs, targets in data_loader:
                inputs = inputs.to(device)
                targets = targets.to(device)
                outputs = model(inputs)
                if criterion is not None:
                    loss = criterion(outputs, targets)
                    total_loss += loss.item() * targets.size(0)
                preds = outputs.argmax(dim=1)
                correct += (preds == targets).sum().item()
                total += targets.numel()
        avg_loss = total_loss / total if criterion is not None and total > 0 else 0.0
        acc = correct / total if total > 0 else 0.0
        return avg_loss, acc

    def solve(self, train_loader, val_loader, metadata: dict = None) -> torch.nn.Module:
        if metadata is None:
            metadata = {}
        input_dim = int(metadata.get("input_dim", 384))
        num_classes = int(metadata.get("num_classes", 128))
        param_limit = int(metadata.get("param_limit", 200000))
        device_str = metadata.get("device", "cpu")
        device = torch.device(device_str if torch.cuda.is_available() or device_str == "cpu" else "cpu")

        model = self._build_model(input_dim, num_classes, param_limit)
        model.to(device)

        # Double-check parameter constraint
        if count_parameters(model) > param_limit:
            # As an extreme fallback, use a very small single-layer model
            model = nn.Sequential(
                nn.Linear(input_dim, num_classes)
            )
            model.to(device)

        # Training hyperparameters
        train_samples = metadata.get("train_samples", None)
        if train_samples is None and hasattr(train_loader, "dataset"):
            try:
                train_samples = len(train_loader.dataset)
            except Exception:
                train_samples = 2048
        if train_samples is None:
            train_samples = 2048

        max_epochs = 150
        if train_samples > 10000:
            max_epochs = 80

        patience = 20
        lr = 3e-4
        weight_decay = 1e-4

        criterion = nn.CrossEntropyLoss(label_smoothing=0.1)
        optimizer = optim.AdamW(model.parameters(), lr=lr, weight_decay=weight_decay)
        scheduler = optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=max_epochs, eta_min=1e-5)

        best_val_acc = 0.0
        best_state_dict = None
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

            if val_loader is not None:
                val_loss, val_acc = self._evaluate(model, val_loader, device, criterion)
                if val_acc > best_val_acc + 1e-4:
                    best_val_acc = val_acc
                    best_state_dict = {k: v.cpu().clone() for k, v in model.state_dict().items()}
                    epochs_no_improve = 0
                else:
                    epochs_no_improve += 1
                    if epochs_no_improve >= patience:
                        scheduler.step()
                        break
            scheduler.step()

        if best_state_dict is not None:
            model.load_state_dict(best_state_dict)

        model.to(device)
        model.eval()
        return model
