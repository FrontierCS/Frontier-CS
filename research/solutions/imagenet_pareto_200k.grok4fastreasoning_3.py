import torch
import torch.nn as nn
import copy

class Solution:
    def solve(self, train_loader, val_loader, metadata: dict = None) -> torch.nn.Module:
        input_dim = metadata["input_dim"]
        num_classes = metadata["num_classes"]
        device = torch.device(metadata["device"])

        class MyModel(nn.Module):
            def __init__(self, input_dim, num_classes):
                super().__init__()
                self.fc1 = nn.Linear(input_dim, 320)
                self.bn1 = nn.BatchNorm1d(320)
                self.fc2 = nn.Linear(320, 160)
                self.bn2 = nn.BatchNorm1d(160)
                self.fc3 = nn.Linear(160, 80)
                self.bn3 = nn.BatchNorm1d(80)
                self.fc4 = nn.Linear(80, num_classes)
                self.dropout = nn.Dropout(0.3)

            def forward(self, x):
                x = self.fc1(x)
                x = self.bn1(x)
                x = torch.relu(x)
                x = self.dropout(x)
                x = self.fc2(x)
                x = self.bn2(x)
                x = torch.relu(x)
                x = self.dropout(x)
                x = self.fc3(x)
                x = self.bn3(x)
                x = torch.relu(x)
                x = self.dropout(x)
                x = self.fc4(x)
                return x

        model = MyModel(input_dim, num_classes).to(device)
        optimizer = torch.optim.Adam(model.parameters(), lr=0.001, weight_decay=1e-5)
        criterion = nn.CrossEntropyLoss()

        best_val_acc = 0.0
        best_model = None
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
            val_correct = 0
            val_total = 0
            with torch.no_grad():
                for inputs, targets in val_loader:
                    inputs, targets = inputs.to(device), targets.to(device)
                    outputs = model(inputs)
                    preds = outputs.argmax(dim=1)
                    val_correct += (preds == targets).sum().item()
                    val_total += targets.size(0)
            val_acc = val_correct / val_total

            if val_acc > best_val_acc:
                best_val_acc = val_acc
                best_model = copy.deepcopy(model)

        return best_model
