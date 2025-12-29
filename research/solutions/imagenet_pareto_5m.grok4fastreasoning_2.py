import torch
import torch.nn as nn
import torch.optim as optim
from torch.optim.lr_scheduler import ReduceLROnPlateau

class Solution:
    def solve(self, train_loader, val_loader, metadata: dict = None) -> torch.nn.Module:
        device = metadata["device"]
        input_dim = metadata["input_dim"]
        num_classes = metadata["num_classes"]

        class ResidualBlock(nn.Module):
            def __init__(self, dim):
                super().__init__()
                self.fc1 = nn.Linear(dim, dim)
                self.bn1 = nn.BatchNorm1d(dim)
                self.fc2 = nn.Linear(dim, dim)
                self.bn2 = nn.BatchNorm1d(dim)
                self.dropout = nn.Dropout(0.1)

            def forward(self, x):
                residual = x
                out = torch.relu(self.bn1(self.fc1(x)))
                out = self.dropout(out)
                out = self.bn2(self.fc2(out))
                out += residual
                out = torch.relu(out)
                return out

        class Net(nn.Module):
            def __init__(self, input_dim, num_classes):
                super().__init__()
                dim = 869
                self.pre = nn.Linear(input_dim, dim)
                self.bn_pre = nn.BatchNorm1d(dim)
                self.layer1 = ResidualBlock(dim)
                self.layer2 = ResidualBlock(dim)
                self.layer3 = ResidualBlock(dim)
                self.head = nn.Linear(dim, num_classes)

            def forward(self, x):
                x = torch.relu(self.bn_pre(self.pre(x)))
                x = self.layer1(x)
                x = self.layer2(x)
                x = self.layer3(x)
                x = self.head(x)
                return x

        model = Net(input_dim, num_classes).to(device)
        optimizer = optim.AdamW(model.parameters(), lr=0.001, weight_decay=1e-4)
        criterion = nn.CrossEntropyLoss()
        scheduler = ReduceLROnPlateau(optimizer, mode='min', factor=0.5, patience=10)

        best_val_acc = 0.0
        best_model_state = None
        patience_counter = 0
        max_epochs = 300
        early_patience = 30

        for epoch in range(max_epochs):
            # Training
            model.train()
            train_loss = 0.0
            num_batches = len(train_loader)
            for inputs, targets in train_loader:
                inputs, targets = inputs.to(device), targets.to(device)
                optimizer.zero_grad()
                outputs = model(inputs)
                loss = criterion(outputs, targets)
                loss.backward()
                optimizer.step()
                train_loss += loss.item()

            # Validation
            model.eval()
            val_loss = 0.0
            val_correct = 0
            val_total = 0
            with torch.no_grad():
                for inputs, targets in val_loader:
                    inputs, targets = inputs.to(device), targets.to(device)
                    outputs = model(inputs)
                    loss = criterion(outputs, targets)
                    val_loss += loss.item()
                    preds = outputs.argmax(dim=1)
                    val_correct += (preds == targets).sum().item()
                    val_total += targets.numel()

            avg_val_loss = val_loss / len(val_loader)
            val_acc = val_correct / val_total

            scheduler.step(avg_val_loss)

            # Check for best
            if val_acc > best_val_acc:
                best_val_acc = val_acc
                best_model_state = model.state_dict().copy()
                patience_counter = 0
            else:
                patience_counter += 1

            if patience_counter >= early_patience:
                break

        if best_model_state is not None:
            model.load_state_dict(best_model_state)

        return model