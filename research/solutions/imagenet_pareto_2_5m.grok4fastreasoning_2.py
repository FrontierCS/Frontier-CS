import torch
import torch.nn as nn
import copy

class Solution:
    def solve(self, train_loader, val_loader, metadata: dict = None) -> torch.nn.Module:
        input_dim = metadata["input_dim"]
        num_classes = metadata["num_classes"]
        device = metadata["device"]

        class Net(nn.Module):
            def __init__(self, input_dim, num_classes):
                super(Net, self).__init__()
                self.fc1 = nn.Linear(input_dim, 1024)
                self.bn1 = nn.BatchNorm1d(1024)
                self.dropout1 = nn.Dropout(0.2)
                self.fc2 = nn.Linear(1024, 1024)
                self.bn2 = nn.BatchNorm1d(1024)
                self.dropout2 = nn.Dropout(0.2)
                self.fc3 = nn.Linear(1024, 900)
                self.bn3 = nn.BatchNorm1d(900)
                self.dropout3 = nn.Dropout(0.2)
                self.fc4 = nn.Linear(900, num_classes)

            def forward(self, x):
                x = self.fc1(x)
                x = self.bn1(x)
                x = torch.relu(x)
                x = self.dropout1(x)
                x = self.fc2(x)
                x = self.bn2(x)
                x = torch.relu(x)
                x = self.dropout2(x)
                x = self.fc3(x)
                x = self.bn3(x)
                x = torch.relu(x)
                x = self.dropout3(x)
                x = self.fc4(x)
                return x

        model = Net(input_dim, num_classes)
        model.to(device)

        optimizer = torch.optim.Adam(model.parameters(), lr=0.001, weight_decay=1e-4)
        scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(optimizer, mode='max', factor=0.5, patience=10, verbose=False)
        criterion = nn.CrossEntropyLoss()

        num_epochs = 150
        best_val_acc = 0.0
        best_model_state = None

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
            val_correct = 0
            val_total = 0
            with torch.no_grad():
                for inputs, targets in val_loader:
                    inputs = inputs.to(device)
                    targets = targets.to(device)
                    outputs = model(inputs)
                    preds = outputs.argmax(dim=1)
                    val_correct += (preds == targets).sum().item()
                    val_total += targets.size(0)
            val_acc = val_correct / val_total

            scheduler.step(val_acc)

            if val_acc > best_val_acc:
                best_val_acc = val_acc
                best_model_state = copy.deepcopy(model.state_dict())

        if best_model_state is not None:
            model.load_state_dict(best_model_state)

        return model