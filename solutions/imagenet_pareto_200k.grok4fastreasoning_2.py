import torch
import torch.nn as nn
from torch.optim import Adam
from torch.optim.lr_scheduler import ReduceLROnPlateau

class Solution:
    def solve(self, train_loader, val_loader, metadata: dict = None) -> torch.nn.Module:
        device = metadata["device"]
        input_dim = metadata["input_dim"]
        num_classes = metadata["num_classes"]

        class Net(nn.Module):
            def __init__(self):
                super().__init__()
                self.fc1 = nn.Linear(input_dim, 256)
                self.bn1 = nn.BatchNorm1d(256)
                self.fc2 = nn.Linear(256, 256)
                self.bn2 = nn.BatchNorm1d(256)
                self.fc3 = nn.Linear(256, num_classes)
                self.dropout = nn.Dropout(0.2)

            def forward(self, x):
                x = torch.relu(self.bn1(self.fc1(x)))
                x = self.dropout(x)
                x = torch.relu(self.bn2(self.fc2(x)))
                x = self.dropout(x)
                x = self.fc3(x)
                return x

        model = Net().to(device)
        optimizer = Adam(model.parameters(), lr=0.001, weight_decay=1e-4)
        criterion = nn.CrossEntropyLoss()
        scheduler = ReduceLROnPlateau(optimizer, mode='min', patience=10, factor=0.5, verbose=False)

        best_val_acc = 0.0
        best_state = None
        patience = 20
        epochs_no_improve = 0
        max_epochs = 200

        for epoch in range(max_epochs):
            model.train()
            train_loss = 0.0
            for inputs, targets in train_loader:
                inputs, targets = inputs.to(device), targets.to(device)
                optimizer.zero_grad()
                outputs = model(inputs)
                loss = criterion(outputs, targets)
                loss.backward()
                optimizer.step()
                train_loss += loss.item()

            model.eval()
            val_loss = 0.0
            correct = 0
            total = 0
            with torch.no_grad():
                for inputs, targets in val_loader:
                    inputs, targets = inputs.to(device), targets.to(device)
                    outputs = model(inputs)
                    loss = criterion(outputs, targets)
                    val_loss += loss.item() * inputs.size(0)
                    preds = outputs.argmax(dim=1)
                    correct += (preds == targets).sum().item()
                    total += targets.size(0)

            val_loss /= total
            val_acc = correct / total

            scheduler.step(val_loss)

            if val_acc > best_val_acc:
                best_val_acc = val_acc
                best_state = model.state_dict().copy()
                epochs_no_improve = 0
            else:
                epochs_no_improve += 1

            if epochs_no_improve >= patience:
                break

        if best_state is not None:
            model.load_state_dict(best_state)

        return model
