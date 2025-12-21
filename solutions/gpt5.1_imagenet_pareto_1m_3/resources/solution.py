import torch
import torch.nn as nn
import torch.nn.functional as F
import copy


def count_parameters(model: nn.Module) -> int:
    return sum(p.numel() for p in model.parameters() if p.requires_grad)


class ResidualBlock(nn.Module):
    def __init__(self, dim: int, dropout: float = 0.1):
        super().__init__()
        self.fc1 = nn.Linear(dim, dim)
        self.bn1 = nn.BatchNorm1d(dim)
        self.fc2 = nn.Linear(dim, dim)
        self.bn2 = nn.BatchNorm1d(dim)
        self.dropout = nn.Dropout(dropout)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        residual = x
        out = self.fc1(x)
        out = self.bn1(out)
        out = F.relu(out, inplace=True)
        out = self.dropout(out)
        out = self.fc2(out)
        out = self.bn2(out)
        out = out + residual
        out = F.relu(out, inplace=True)
        return out


class ResidualMLP(nn.Module):
    def __init__(
        self,
        input_dim: int,
        num_classes: int,
        hidden_dim: int = 320,
        num_blocks: int = 4,
        dropout: float = 0.1,
    ):
        super().__init__()
        self.fc_in = nn.Linear(input_dim, hidden_dim)
        self.bn_in = nn.BatchNorm1d(hidden_dim)
        blocks = []
        for _ in range(num_blocks):
            blocks.append(ResidualBlock(hidden_dim, dropout=dropout))
        self.blocks = nn.Sequential(*blocks)
        self.fc_out = nn.Linear(hidden_dim, num_classes)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self.fc_in(x)
        x = self.bn_in(x)
        x = F.relu(x, inplace=True)
        x = self.blocks(x)
        x = self.fc_out(x)
        return x


class SimpleMLP(nn.Module):
    def __init__(
        self,
        input_dim: int,
        num_classes: int,
        hidden_dim: int = 512,
        dropout: float = 0.1,
    ):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.ReLU(inplace=True),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim, num_classes),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x)


class Solution:
    def _build_best_model(self, input_dim: int, num_classes: int, param_limit: int) -> nn.Module:
        dropout = 0.1

        # Search over residual MLP configurations
        candidate_hidden_dims = [512, 448, 384, 352, 320, 288, 256, 224, 192, 160, 128]
        candidate_blocks = [6, 5, 4, 3, 2, 1]

        best_model = None
        best_params = -1

        for h in candidate_hidden_dims:
            if h <= 0:
                continue
            for b in candidate_blocks:
                model = ResidualMLP(
                    input_dim=input_dim,
                    num_classes=num_classes,
                    hidden_dim=h,
                    num_blocks=b,
                    dropout=dropout,
                )
                params = count_parameters(model)
                if params <= param_limit and params > best_params:
                    best_params = params
                    best_model = model

        # Fallback: simple MLP if param_limit is very small
        if best_model is None:
            fallback_hidden_dims = [512, 384, 320, 256, 192, 160, 128, 96, 64, 48, 32]
            for h in fallback_hidden_dims:
                if h <= 0:
                    continue
                model = SimpleMLP(
                    input_dim=input_dim,
                    num_classes=num_classes,
                    hidden_dim=h,
                    dropout=dropout,
                )
                params = count_parameters(model)
                if params <= param_limit and params > best_params:
                    best_params = params
                    best_model = model

        return best_model

    def _evaluate(self, model, data_loader, criterion, device):
        model.eval()
        total_loss = 0.0
        correct = 0
        total = 0
        with torch.no_grad():
            for inputs, targets in data_loader:
                inputs = inputs.to(device)
                targets = targets.to(device)
                outputs = model(inputs)
                loss = criterion(outputs, targets)
                total_loss += loss.item() * targets.size(0)
                preds = outputs.argmax(dim=1)
                correct += (preds == targets).sum().item()
                total += targets.numel()
        avg_loss = total_loss / total if total > 0 else 0.0
        acc = correct / total if total > 0 else 0.0
        return avg_loss, acc

    def solve(self, train_loader, val_loader, metadata: dict = None) -> torch.nn.Module:
        if metadata is None:
            metadata = {}

        torch.manual_seed(42)

        device_str = metadata.get("device", "cpu")
        device = torch.device(device_str)

        input_dim = int(metadata.get("input_dim", 384))
        num_classes = int(metadata.get("num_classes", 128))
        param_limit = int(metadata.get("param_limit", 1_000_000))

        model = self._build_best_model(input_dim, num_classes, param_limit)
        if model is None:
            # Very small limit fallback: smallest possible single-layer classifier
            model = nn.Linear(input_dim, num_classes)

        model.to(device)

        # Verify parameter constraint at construction time
        if count_parameters(model) > param_limit:
            # As a last resort, very small linear classifier
            model = nn.Linear(input_dim, num_classes).to(device)

        # Training setup
        try:
            criterion = nn.CrossEntropyLoss(label_smoothing=0.05)
        except TypeError:
            criterion = nn.CrossEntropyLoss()

        optimizer = torch.optim.AdamW(model.parameters(), lr=0.002, weight_decay=1e-4)

        steps_per_epoch = max(1, len(train_loader))
        if steps_per_epoch <= 50:
            max_epochs = 400
        elif steps_per_epoch <= 200:
            max_epochs = 200
        else:
            max_epochs = 80

        scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(
            optimizer, T_max=max_epochs, eta_min=1e-5
        )

        best_state = copy.deepcopy(model.state_dict())
        best_val_acc = 0.0
        epochs_no_improve = 0
        patience = max(10, max_epochs // 4)

        for epoch in range(max_epochs):
            model.train()
            running_loss = 0.0
            total_train = 0

            for inputs, targets in train_loader:
                inputs = inputs.to(device)
                targets = targets.to(device)

                optimizer.zero_grad(set_to_none=True)
                outputs = model(inputs)
                loss = criterion(outputs, targets)
                loss.backward()
                torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=5.0)
                optimizer.step()

                batch_size = targets.size(0)
                running_loss += loss.item() * batch_size
                total_train += batch_size

            if val_loader is not None:
                val_loss, val_acc = self._evaluate(model, val_loader, criterion, device)
            else:
                val_loss, val_acc = 0.0, 0.0

            scheduler.step()

            if val_loader is not None:
                if val_acc > best_val_acc + 1e-4:
                    best_val_acc = val_acc
                    best_state = copy.deepcopy(model.state_dict())
                    epochs_no_improve = 0
                else:
                    epochs_no_improve += 1
                    if epochs_no_improve >= patience:
                        break

        model.load_state_dict(best_state)
        model.to(device)
        return model
