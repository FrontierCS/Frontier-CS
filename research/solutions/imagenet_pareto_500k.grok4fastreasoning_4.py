import torch
import torch.nn as nn
import torch.optim as optim

class Solution:
    def solve(self, train_loader, val_loader, metadata: dict = None) -> torch.nn.Module:
        input_dim = metadata["input_dim"]
        num_classes = metadata["num_classes"]
        device = torch.device(metadata["device"])

        class Net(nn.Module):
            def __init__(self, input_dim, num_classes):
                super(Net, self).__init__()
                self.fc1 = nn.Linear(input_dim, 512)
                self.bn1 = nn.BatchNorm1d(512)
                self.fc2 = nn.Linear(512, 256)
                self.bn2 = nn.BatchNorm1d(256)
                self.fc3 = nn.Linear(256, 256)
                self.bn3 = nn.BatchNorm1d(256)
                self.fc4 = nn.Linear(256, num_classes)
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
                x = self.bn3(x)
                x = self.relu(x)
                x = self.dropout(x)

                x = self.fc4(x)
                return x

        model = Net(input_dim, num_classes).to(device)

        optimizer = optim.Adam(model.parameters(), lr=0.001, weight_decay=1e-4)
        criterion = nn.CrossEntropyLoss()

        best_val_acc = 0.0
        patience = 20
        epochs_no_improve = 0
        num_epochs = 200

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

            val_acc = correct / total if total > 0 else 0.0

            if val_acc > best_val_acc:
                best_val_acc = val_acc
                best_state = {name: param.clone().detach() for name, param in model.state_dict().items()}
                epochs_no_improve = 0
            else:
                epochs_no_improve += 1

            if epochs_no_improve >= patience:
                break

        if best_val_acc > 0.0:
            model.load_state_dict(best_state)

        return model
