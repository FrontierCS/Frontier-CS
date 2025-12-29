import torch
import torch.nn as nn
import copy

class Solution:
    def solve(self, train_loader, val_loader, metadata: dict = None) -> torch.nn.Module:
        input_dim = metadata["input_dim"]
        num_classes = metadata["num_classes"]
        device = metadata["device"]

        class MyModel(nn.Module):
            def __init__(self, input_dim, num_classes):
                super().__init__()
                h = 990
                self.fc1 = nn.Linear(input_dim, h)
                self.bn1 = nn.BatchNorm1d(h)
                self.fc2 = nn.Linear(h, h)
                self.bn2 = nn.BatchNorm1d(h)
                self.fc3 = nn.Linear(h, h)
                self.bn3 = nn.BatchNorm1d(h)
                self.fc4 = nn.Linear(h, num_classes)
                self.relu = nn.ReLU()

            def forward(self, x):
                x = self.fc1(x)
                x = self.bn1(x)
                x = self.relu(x)
                x = self.fc2(x)
                x = self.bn2(x)
                x = self.relu(x)
                x = self.fc3(x)
                x = self.bn3(x)
                x = self.relu(x)
                x = self.fc4(x)
                return x

        model = MyModel(input_dim, num_classes).to(device)
        optimizer = torch.optim.Adam(model.parameters(), lr=0.001, weight_decay=1e-4)
        criterion = nn.CrossEntropyLoss()

        best_val_acc = 0.0
        best_model = None
        patience = 20
        counter = 0
        num_epochs = 200

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

            if val_acc > best_val_acc:
                best_val_acc = val_acc
                best_model = copy.deepcopy(model)
                counter = 0
            else:
                counter += 1
                if counter >= patience:
                    break

        return best_model