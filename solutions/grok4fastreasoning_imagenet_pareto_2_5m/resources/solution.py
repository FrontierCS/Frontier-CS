import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim

class Solution:
    def solve(self, train_loader, val_loader, metadata: dict = None) -> torch.nn.Module:
        device = metadata["device"]
        input_dim = metadata["input_dim"]
        num_classes = metadata["num_classes"]

        class Net(nn.Module):
            def __init__(self, input_dim, num_classes):
                super(Net, self).__init__()
                self.fc1 = nn.Linear(input_dim, 512)
                self.bn1 = nn.BatchNorm1d(512)
                self.fc2 = nn.Linear(512, 2048)
                self.bn2 = nn.BatchNorm1d(2048)
                self.fc3 = nn.Linear(2048, 512)
                self.bn3 = nn.BatchNorm1d(512)
                self.fc4 = nn.Linear(512, num_classes)
                self.dropout = nn.Dropout(0.2)

            def forward(self, x):
                x = self.fc1(x)
                x = self.bn1(x)
                x = F.relu(x)
                x = self.dropout(x)
                x = self.fc2(x)
                x = self.bn2(x)
                x = F.relu(x)
                x = self.dropout(x)
                x = self.fc3(x)
                x = self.bn3(x)
                x = F.relu(x)
                x = self.dropout(x)
                x = self.fc4(x)
                return x

        model = Net(input_dim, num_classes).to(device)
        optimizer = optim.Adam(model.parameters(), lr=0.001, weight_decay=1e-4)
        scheduler = optim.lr_scheduler.ReduceLROnPlateau(optimizer, mode='max', patience=30, factor=0.5, verbose=False)
        criterion = nn.CrossEntropyLoss()

        def validate(model, loader, device):
            model.eval()
            correct = 0
            total = 0
            with torch.no_grad():
                for inputs, targets in loader:
                    inputs = inputs.to(device)
                    targets = targets.to(device)
                    outputs = model(inputs)
                    _, predicted = torch.max(outputs.data, 1)
                    total += targets.size(0)
                    correct += (predicted == targets).sum().item()
            accuracy = correct / total
            return accuracy

        best_acc = 0.0
        best_model = None
        for epoch in range(300):
            model.train()
            running_loss = 0.0
            for inputs, targets in train_loader:
                inputs = inputs.to(device)
                targets = targets.to(device)
                optimizer.zero_grad()
                outputs = model(inputs)
                loss = criterion(outputs, targets)
                loss.backward()
                optimizer.step()
                running_loss += loss.item()
            val_acc = validate(model, val_loader, device)
            scheduler.step(val_acc)
            if val_acc > best_acc:
                best_acc = val_acc
                if best_model is None:
                    best_model = Net(input_dim, num_classes).to(device)
                best_model.load_state_dict(model.state_dict())
        if best_model is None:
            best_model = model
        return best_model
