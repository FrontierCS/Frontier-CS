import torch
import torch.nn as nn
import torch.optim as optim

class Solution:
    def solve(self, train_loader, val_loader, metadata: dict = None) -> torch.nn.Module:
        input_dim = metadata["input_dim"]
        num_classes = metadata["num_classes"]
        device = metadata.get("device", "cpu")

        class Net(nn.Module):
            def __init__(self, input_dim, num_classes):
                super(Net, self).__init__()
                self.fc1 = nn.Linear(input_dim, 768)
                self.bn1 = nn.BatchNorm1d(768)
                self.fc2 = nn.Linear(768, 512)
                self.bn2 = nn.BatchNorm1d(512)
                self.fc3 = nn.Linear(512, 256)
                self.bn3 = nn.BatchNorm1d(256)
                self.fc4 = nn.Linear(256, num_classes)
                self.dropout = nn.Dropout(0.25)

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

        model = Net(input_dim, num_classes).to(device)
        optimizer = optim.Adam(model.parameters(), lr=0.001, weight_decay=1e-4)
        criterion = nn.CrossEntropyLoss()
        scheduler = optim.lr_scheduler.ReduceLROnPlateau(optimizer, mode='max', patience=15, factor=0.5, verbose=False)
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
            val_acc = val_correct / val_total if val_total > 0 else 0.0
            scheduler.step(val_acc)

        return model
