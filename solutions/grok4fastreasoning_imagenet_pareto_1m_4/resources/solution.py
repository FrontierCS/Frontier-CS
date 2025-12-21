import torch
import torch.nn as nn
import copy

class Solution:
    def solve(self, train_loader, val_loader, metadata: dict = None) -> torch.nn.Module:
        device = metadata["device"]
        input_dim = metadata["input_dim"]
        num_classes = metadata["num_classes"]

        class Net(nn.Module):
            def __init__(self, input_dim, num_classes):
                super(Net, self).__init__()
                self.fc1 = nn.Linear(input_dim, 1024)
                self.bn1 = nn.BatchNorm1d(1024)
                self.fc2 = nn.Linear(1024, 512)
                self.bn2 = nn.BatchNorm1d(512)
                self.fc3 = nn.Linear(512, num_classes)
                self.relu = nn.ReLU()

            def forward(self, x):
                x = self.fc1(x)
                x = self.bn1(x)
                x = self.relu(x)
                x = self.fc2(x)
                x = self.bn2(x)
                x = self.relu(x)
                x = self.fc3(x)
                return x

        model = Net(input_dim, num_classes).to(device)
        optimizer = torch.optim.Adam(model.parameters(), lr=0.001, weight_decay=1e-5)
        criterion = nn.CrossEntropyLoss()

        best_val_acc = 0.0
        patience = 20
        counter = 0
        max_epochs = 200
        best_model = None

        for epoch in range(max_epochs):
            model.train()
            for inputs, targets in train_loader:
                inputs = inputs.to(device)
                targets = targets.to(device)
                optimizer.zero_grad()
                outputs = model(inputs)
                loss = criterion(outputs, targets)
                loss.backward()
                optimizer.step()

            # Validation
            model.eval()
            correct = 0
            total = 0
            with torch.no_grad():
                for inputs, targets in val_loader:
                    inputs = inputs.to(device)
                    targets = targets.to(device)
                    outputs = model(inputs)
                    preds = outputs.argmax(dim=1)
                    total += targets.size(0)
                    correct += (preds == targets).sum().item()
            val_acc = correct / total

            if val_acc > best_val_acc:
                best_val_acc = val_acc
                best_model = copy.deepcopy(model)
                counter = 0
            else:
                counter += 1

            if counter >= patience:
                break

        return best_model if best_model is not None else model
