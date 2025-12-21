import torch
import torch.nn as nn
import torch.optim as optim
from torch.optim.lr_scheduler import ReduceLROnPlateau

class Solution:
    def solve(self, train_loader, val_loader, metadata: dict = None) -> torch.nn.Module:
        device = metadata["device"]
        input_dim = metadata["input_dim"]
        num_classes = metadata["num_classes"]

        class Net(nn.Module):
            def __init__(self):
                super().__init__()
                self.fc1 = nn.Linear(input_dim, 512)
                self.bn1 = nn.BatchNorm1d(512)
                self.fc2 = nn.Linear(512, 384)
                self.bn2 = nn.BatchNorm1d(384)
                self.fc3 = nn.Linear(384, 200)
                self.bn3 = nn.BatchNorm1d(200)
                self.fc4 = nn.Linear(200, num_classes)
                self.dropout = nn.Dropout(0.3)

            def forward(self, x):
                x = torch.relu(self.bn1(self.fc1(x)))
                x = self.dropout(x)
                x = torch.relu(self.bn2(self.fc2(x)))
                x = self.dropout(x)
                x = torch.relu(self.bn3(self.fc3(x)))
                x = self.dropout(x)
                x = self.fc4(x)
                return x

        model = Net().to(device)
        optimizer = optim.Adam(model.parameters(), lr=0.001, weight_decay=1e-4)
        criterion = nn.CrossEntropyLoss()
        scheduler = ReduceLROnPlateau(optimizer, mode='max', factor=0.5, patience=10, verbose=False)

        best_val_acc = 0.0
        best_state = None
        patience = 20
        epochs_no_improve = 0
        num_epochs = 300

        for epoch in range(num_epochs):
            model.train()
            for inputs, targets in train_loader:
                inputs, targets = inputs.to(device), targets.to(device)
                optimizer.zero_grad()
                outputs = model(inputs)
                loss = criterion(outputs, targets)
                loss.backward()
                optimizer.step()

            model.eval()
            correct = 0
            total = 0
            with torch.no_grad():
                for inputs, targets in val_loader:
                    inputs, targets = inputs.to(device), targets.to(device)
                    outputs = model(inputs)
                    preds = outputs.argmax(dim=1)
                    correct += (preds == targets).sum().item()
                    total += targets.size(0)
            val_acc = correct / total

            scheduler.step(val_acc)

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
