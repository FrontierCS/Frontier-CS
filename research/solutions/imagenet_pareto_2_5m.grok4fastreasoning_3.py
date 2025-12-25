import torch
import torch.nn as nn
import torch.optim as optim
from torch.optim.lr_scheduler import ReduceLROnPlateau

class Solution:
    def solve(self, train_loader, val_loader, metadata: dict = None) -> torch.nn.Module:
        input_dim = metadata["input_dim"]
        num_classes = metadata["num_classes"]
        device = metadata["device"]

        class Net(nn.Module):
            def __init__(self, input_dim, num_classes):
                super().__init__()
                self.fc1 = nn.Linear(input_dim, 256)
                self.bn1 = nn.BatchNorm1d(256)
                self.fc2 = nn.Linear(256, 512)
                self.bn2 = nn.BatchNorm1d(512)
                self.fc3 = nn.Linear(512, 1024)
                self.bn3 = nn.BatchNorm1d(1024)
                self.fc4 = nn.Linear(1024, 1024)
                self.bn4 = nn.BatchNorm1d(1024)
                self.fc5 = nn.Linear(1024, 512)
                self.bn5 = nn.BatchNorm1d(512)
                self.fc6 = nn.Linear(512, 256)
                self.bn6 = nn.BatchNorm1d(256)
                self.fc7 = nn.Linear(256, num_classes)
                self.relu = nn.ReLU()
                self.dropout = nn.Dropout(0.1)

            def forward(self, x):
                x = self.relu(self.bn1(self.fc1(x)))
                x = self.dropout(x)
                x = self.relu(self.bn2(self.fc2(x)))
                x = self.dropout(x)
                x = self.relu(self.bn3(self.fc3(x)))
                x = self.dropout(x)
                x = self.relu(self.bn4(self.fc4(x)))
                x = self.dropout(x)
                x = self.relu(self.bn5(self.fc5(x)))
                x = self.dropout(x)
                x = self.relu(self.bn6(self.fc6(x)))
                x = self.dropout(x)
                x = self.fc7(x)
                return x

        model = Net(input_dim, num_classes).to(device)
        best_model = Net(input_dim, num_classes).to(device)
        best_acc = 0.0

        criterion = nn.CrossEntropyLoss()
        optimizer = optim.Adam(model.parameters(), lr=0.001, weight_decay=1e-4)
        scheduler = ReduceLROnPlateau(optimizer, mode='min', factor=0.5, patience=10)

        patience = 20
        epochs_no_improve = 0
        num_epochs = 300

        for epoch in range(num_epochs):
            model.train()
            train_loss = 0.0
            for inputs, targets in train_loader:
                inputs, targets = inputs.to(device), targets.to(device)
                optimizer.zero_grad()
                outputs = model(inputs)
                loss = criterion(outputs, targets)
                loss.backward()
                optimizer.step()
                train_loss += loss.item() * inputs.size(0)

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

            avg_val_loss = val_loss / total if total > 0 else 0
            val_acc = correct / total if total > 0 else 0

            scheduler.step(avg_val_loss)

            if val_acc > best_acc:
                best_acc = val_acc
                best_model.load_state_dict(model.state_dict())
                epochs_no_improve = 0
            else:
                epochs_no_improve += 1

            if epochs_no_improve >= patience:
                break

        return best_model
