import torch
import torch.nn as nn

class Solution:
    def solve(self, train_loader, val_loader, metadata: dict = None) -> torch.nn.Module:
        class Net(nn.Module):
            def __init__(self, input_dim, num_classes):
                super(Net, self).__init__()
                self.fc1 = nn.Linear(input_dim, 600)
                self.bn1 = nn.BatchNorm1d(600)
                self.fc2 = nn.Linear(600, 300)
                self.bn2 = nn.BatchNorm1d(300)
                self.fc3 = nn.Linear(300, 150)
                self.bn3 = nn.BatchNorm1d(150)
                self.fc4 = nn.Linear(150, num_classes)

            def forward(self, x):
                x = self.fc1(x)
                x = self.bn1(x)
                x = torch.relu(x)
                x = self.fc2(x)
                x = self.bn2(x)
                x = torch.relu(x)
                x = self.fc3(x)
                x = self.bn3(x)
                x = torch.relu(x)
                x = self.fc4(x)
                return x

        def evaluate(model, loader, device):
            model.eval()
            correct = 0
            total = 0
            with torch.no_grad():
                for inputs, targets in loader:
                    inputs = inputs.to(device)
                    targets = targets.to(device)
                    outputs = model(inputs)
                    preds = outputs.argmax(dim=1)
                    correct += (preds == targets).sum().item()
                    total += targets.size(0)
            return correct / total if total > 0 else 0.0

        device = metadata["device"]
        input_dim = metadata["input_dim"]
        num_classes = metadata["num_classes"]

        model = Net(input_dim, num_classes).to(device)
        optimizer = torch.optim.AdamW(model.parameters(), lr=0.001, weight_decay=1e-4)
        criterion = nn.CrossEntropyLoss()

        best_val_acc = 0.0
        best_state = None
        patience = 20
        counter = 0
        max_epochs = 300

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

            val_acc = evaluate(model, val_loader, device)
            if val_acc > best_val_acc:
                best_val_acc = val_acc
                best_state = model.state_dict().copy()
                counter = 0
            else:
                counter += 1

            if counter >= patience:
                break

        if best_state is not None:
            model.load_state_dict(best_state)

        return model
