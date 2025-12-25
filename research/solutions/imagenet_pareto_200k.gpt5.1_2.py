import torch
import torch.nn as nn
import torch.optim as optim
import copy


class MLPNet(nn.Module):
    def __init__(self, input_dim: int, num_classes: int, hidden_dim: int, use_input_bn: bool = True,
                 dropout_p: float = 0.25):
        super().__init__()
        self.use_input_bn = use_input_bn
        if use_input_bn:
            self.input_bn = nn.BatchNorm1d(input_dim)
        else:
            self.input_bn = None

        self.fc1 = nn.Linear(input_dim, hidden_dim)
        self.bn1 = nn.BatchNorm1d(hidden_dim)

        self.fc2 = nn.Linear(hidden_dim, hidden_dim)
        self.bn2 = nn.BatchNorm1d(hidden_dim)

        self.fc3 = nn.Linear(hidden_dim, num_classes)

        self.act = nn.GELU()
        self.dropout = nn.Dropout(p=dropout_p)

    def forward(self, x):
        if self.input_bn is not None:
            x = self.input_bn(x)

        x = self.fc1(x)
        x = self.bn1(x)
        x = self.act(x)
        x = self.dropout(x)

        h = self.fc2(x)
        h = self.bn2(h)
        h = self.act(h)
        h = self.dropout(h)

        x = x + h
        x = self.fc3(x)
        return x


class Solution:
    def __init__(self):
        pass

    def _build_model(self, input_dim: int, num_classes: int, param_limit: int, device: torch.device):
        candidate_widths = [512, 448, 384, 320, 288, 256, 224, 192, 160, 128, 96, 64, 48, 32, 24, 16, 8]
        selected_model = None

        for h in candidate_widths:
            model = MLPNet(input_dim=input_dim, num_classes=num_classes, hidden_dim=h, use_input_bn=True,
                           dropout_p=0.25)
            param_count = sum(p.numel() for p in model.parameters() if p.requires_grad)
            if param_count <= param_limit:
                selected_model = model
                break

        if selected_model is None:
            # Fallback very small model (shouldn't be needed for given constraints)
            selected_model = nn.Sequential(
                nn.Linear(input_dim, num_classes)
            )

        selected_model.to(device)
        return selected_model

    def _evaluate(self, model, data_loader, device):
        model.eval()
        total_loss = 0.0
        total_correct = 0
        total_samples = 0
        criterion = nn.CrossEntropyLoss(label_smoothing=0.1)

        with torch.no_grad():
            for inputs, targets in data_loader:
                inputs = inputs.to(device=device, dtype=torch.float32)
                targets = targets.to(device=device, dtype=torch.long)

                outputs = model(inputs)
                loss = criterion(outputs, targets)

                total_loss += loss.item() * inputs.size(0)
                preds = outputs.argmax(dim=1)
                total_correct += (preds == targets).sum().item()
                total_samples += targets.size(0)

        avg_loss = total_loss / max(total_samples, 1)
        avg_acc = total_correct / max(total_samples, 1)
        return avg_loss, avg_acc

    def _train_model(self, model, train_loader, val_loader, device, metadata):
        criterion = nn.CrossEntropyLoss(label_smoothing=0.1)

        optimizer = optim.AdamW(model.parameters(), lr=3e-3, weight_decay=1e-3)

        max_epochs = 200
        min_epochs = 40
        patience = 30

        best_state = copy.deepcopy(model.state_dict())
        best_val_acc = 0.0
        epochs_no_improve = 0

        for epoch in range(max_epochs):
            model.train()
            running_loss = 0.0
            total_samples = 0

            for inputs, targets in train_loader:
                inputs = inputs.to(device=device, dtype=torch.float32)
                targets = targets.to(device=device, dtype=torch.long)

                optimizer.zero_grad(set_to_none=True)
                outputs = model(inputs)
                loss = criterion(outputs, targets)
                loss.backward()
                torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=5.0)
                optimizer.step()

                running_loss += loss.item() * inputs.size(0)
                total_samples += inputs.size(0)

            if epoch in (80, 140):
                for g in optimizer.param_groups:
                    g["lr"] *= 0.3

            val_loss, val_acc = self._evaluate(model, val_loader, device)

            if val_acc > best_val_acc:
                best_val_acc = val_acc
                best_state = copy.deepcopy(model.state_dict())
                epochs_no_improve = 0
            else:
                epochs_no_improve += 1

            if epoch + 1 >= min_epochs and epochs_no_improve >= patience:
                break

        model.load_state_dict(best_state)

    def solve(self, train_loader, val_loader, metadata: dict = None) -> torch.nn.Module:
        if metadata is None:
            metadata = {}
        input_dim = metadata.get("input_dim", 384)
        num_classes = metadata.get("num_classes", 128)
        param_limit = metadata.get("param_limit", 200000)
        device_str = metadata.get("device", "cpu")
        device = torch.device(device_str)

        torch.manual_seed(42)

        model = self._build_model(input_dim, num_classes, param_limit, device)
        self._train_model(model, train_loader, val_loader, device, metadata)

        model.to(device)
        model.eval()
        return model
