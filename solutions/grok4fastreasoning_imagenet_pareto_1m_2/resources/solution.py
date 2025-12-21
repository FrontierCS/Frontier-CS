import torch
import torch.nn as nn
import copy
from torch.optim.lr_scheduler import ReduceLROnPlateau

class Solution:
    def solve(self, train_loader, val_loader, metadata: dict = None) -> torch.nn.Module:
        input_dim = metadata["input_dim"]
        num_classes = metadata["num_classes"]
        device = metadata["device"]

        class Net(nn.Module):
            def __init__(self, input_dim, num_classes):
                super(Net, self).__init__()
                self.fc1 = nn.Linear(input_dim, 768)
                self.bn1 = nn.BatchNorm1d(768)
                self.fc2 = nn.Linear(768, 768)
                self.bn2 = nn.BatchNorm1d(768)
                self.fc3 = nn.Linear(768, num_classes)
                self.relu = nn.ReLU()
                self.dropout = nn.Dropout(0.2)

            def forward(self, x):
                x = self.relu(self.bn1(self.fc1(x)))
                x = self.dropout(x)
                x = self.relu(self.bn2(self.fc2(x)))
                x = self.dropout(x)
                x = self.fc3(x)
                return x

        model = Net(input_dim, num_classes).to(device)
        optimizer = torch.optim.Adam(model.parameters(), lr=0.001, weight_decay=1e-4)
        criterion = nn.CrossEntropyLoss()
        scheduler = ReduceLROnPlateau(optimizer, mode='max', factor=0.5, patience=10, verbose=False)

        best_val_acc = 0.0
        best_state = None
        patience_counter = 0
        max_patience = 20
        num_epochs = 200

        for epoch in range(num_epochs):
            # Training
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
                    correct += (preds == targets).sum().item()
                    total += targets.size(0)

            val_acc = correct / total if total > 0 else 0.0

            scheduler.step(val_acc)

            if val_acc > best_val_acc:
                best_val_acc = val_acc
                best_state = copy.deepcopy(model.state_dict())
                patience_counter = 0
            else:
                patience_counter += 1

            if patience_counter >= max_patience:
                break

        if best_state is not None:
            model.load_state_dict(best_state)

        return model
