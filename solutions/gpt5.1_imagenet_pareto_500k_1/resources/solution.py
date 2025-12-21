import torch
import torch.nn as nn
import torch.nn.functional as F


class ResidualBlock(nn.Module):
    def __init__(self, dim: int, dropout: float = 0.2):
        super().__init__()
        self.fc = nn.Linear(dim, dim)
        self.bn = nn.BatchNorm1d(dim)
        self.act = nn.GELU()
        self.dropout = nn.Dropout(dropout)

    def forward(self, x):
        residual = x
        out = self.fc(x)
        out = self.bn(out)
        out = self.act(out)
        out = self.dropout(out)
        return residual + out


class MLPNet(nn.Module):
    def __init__(self, input_dim: int, num_classes: int, dropout: float = 0.2):
        super().__init__()
        hidden1 = 512
        hidden2 = 256

        self.fc1 = nn.Linear(input_dim, hidden1)
        self.bn1 = nn.BatchNorm1d(hidden1)

        self.fc2 = nn.Linear(hidden1, hidden2)
        self.bn2 = nn.BatchNorm1d(hidden2)

        self.block1 = ResidualBlock(hidden2, dropout=dropout)
        self.block2 = ResidualBlock(hidden2, dropout=dropout)

        self.dropout = nn.Dropout(dropout)
        self.out = nn.Linear(hidden2, num_classes)

    def forward(self, x):
        x = self.fc1(x)
        x = self.bn1(x)
        x = F.gelu(x)
        x = self.dropout(x)

        x = self.fc2(x)
        x = self.bn2(x)
        x = F.gelu(x)
        x = self.dropout(x)

        x = self.block1(x)
        x = self.block2(x)

        x = self.out(x)
        return x


class Solution:
    def solve(self, train_loader, val_loader, metadata: dict = None) -> torch.nn.Module:
        if metadata is None:
            metadata = {}
        input_dim = metadata.get("input_dim", 384)
        num_classes = metadata.get("num_classes", 128)
        device = metadata.get("device", "cpu")
        param_limit = metadata.get("param_limit", 500000)

        torch.manual_seed(42)

        model = MLPNet(input_dim=input_dim, num_classes=num_classes, dropout=0.2)
        param_count = sum(p.numel() for p in model.parameters() if p.requires_grad)
        if param_count > param_limit:
            # In extremely unlikely case of mismatch, fall back to smaller baseline model
            hidden_dim = 384
            model = nn.Sequential(
                nn.Linear(input_dim, hidden_dim),
                nn.ReLU(),
                nn.Linear(hidden_dim, num_classes),
            )

        model.to(device)

        criterion = nn.CrossEntropyLoss(label_smoothing=0.1)
        optimizer = torch.optim.AdamW(model.parameters(), lr=5e-4, weight_decay=1e-2)
        scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
            optimizer, mode="max", factor=0.5, patience=5, min_lr=1e-5, verbose=False
        )

        num_epochs = 120
        patience = 20
        best_val_acc = 0.0
        best_state_dict = None
        epochs_no_improve = 0

        for epoch in range(num_epochs):
            model.train()
            total = 0
            correct = 0
            running_loss = 0.0

            for inputs, targets in train_loader:
                inputs = inputs.to(device)
                targets = targets.to(device)

                optimizer.zero_grad()
                outputs = model(inputs)
                loss = criterion(outputs, targets)
                loss.backward()
                torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=5.0)
                optimizer.step()

                batch_size = targets.size(0)
                running_loss += loss.item() * batch_size
                _, preds = outputs.max(1)
                correct += (preds == targets).sum().item()
                total += batch_size

            model.eval()
            val_total = 0
            val_correct = 0
            val_loss = 0.0
            with torch.no_grad():
                for inputs, targets in val_loader:
                    inputs = inputs.to(device)
                    targets = targets.to(device)
                    outputs = model(inputs)
                    loss = criterion(outputs, targets)

                    batch_size = targets.size(0)
                    val_loss += loss.item() * batch_size
                    _, preds = outputs.max(1)
                    val_correct += (preds == targets).sum().item()
                    val_total += batch_size

            if val_total > 0:
                val_loss /= val_total
                val_acc = val_correct / val_total
            else:
                val_loss = 0.0
                val_acc = 0.0

            scheduler.step(val_acc)

            if val_acc > best_val_acc + 1e-4:
                best_val_acc = val_acc
                best_state_dict = {k: v.cpu().clone() for k, v in model.state_dict().items()}
                epochs_no_improve = 0
            else:
                epochs_no_improve += 1
                if epochs_no_improve >= patience:
                    break

        if best_state_dict is not None:
            model.load_state_dict(best_state_dict)

        model.to("cpu")
        model.eval()
        return model
