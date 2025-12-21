import torch
import torch.nn as nn
from torch.optim import Adam
from torch.optim.lr_scheduler import ReduceLROnPlateau

class Solution:
    def solve(self, train_loader, val_loader, metadata: dict = None) -> torch.nn.Module:
        input_dim = metadata["input_dim"]
        num_classes = metadata["num_classes"]
        device = metadata["device"]

        class Net(nn.Module):
            def __init__(self, input_dim, num_classes):
                super(Net, self).__init__()
                self.fc1 = nn.Linear(input_dim, 280)
                self.bn1 = nn.BatchNorm1d(280)
                self.fc2 = nn.Linear(280, 200)
                self.bn2 = nn.BatchNorm1d(200)
                self.fc3 = nn.Linear(200, num_classes)
                self.relu = nn.ReLU(inplace=True)
                self.dropout = nn.Dropout(0.2)

            def forward(self, x):
                x = self.fc1(x)
                x = self.bn1(x)
                x = self.relu(x)
                x = self.dropout(x)
                x = self.fc2(x)
                x = self.bn2(x)
                x = self.relu(x)
                x = self.dropout(x)
                x = self.fc3(x)
                return x

        model = Net(input_dim, num_classes).to(device)

        optimizer = Adam(model.parameters(), lr=0.001, weight_decay=1e-4)
        criterion = nn.CrossEntropyLoss()
        scheduler = ReduceLROnPlateau(optimizer, mode='max', patience=10, factor=0.5, verbose=False)

        best_acc = -1.0
        best_state = None
        num_epochs = 100

        for epoch in range(num_epochs):
            model.train()
            for inputs, targets in train_loader:
                inputs = inputs.to(device)
                targets = targets.to(device)
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
                    inputs = inputs.to(device)
                    targets = targets.to(device)
                    outputs = model(inputs)
                    preds = outputs.argmax(dim=1)
                    correct += (preds == targets).sum().item()
                    total += targets.size(0)
            val_acc = correct / total

            scheduler.step(val_acc)

            if val_acc > best_acc:
                best_acc = val_acc
                best_state = {k: v.clone() for k, v in model.state_dict().items()}

        if best_state is not None:
            model.load_state_dict(best_state)

        return model
