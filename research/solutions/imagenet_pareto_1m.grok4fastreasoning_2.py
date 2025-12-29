import torch
import torch.nn as nn
from torch.optim import AdamW

class Solution:
    def solve(self, train_loader, val_loader, metadata: dict = None) -> torch.nn.Module:
        device = torch.device(metadata["device"])
        input_dim = metadata["input_dim"]
        num_classes = metadata["num_classes"]

        class Net(nn.Module):
            def __init__(self, input_dim, num_classes):
                super().__init__()
                hidden_sizes = [512, 512, 512, 256, 128]
                self.layers = nn.ModuleList()
                self.bns = nn.ModuleList()
                prev = input_dim
                for h in hidden_sizes:
                    self.layers.append(nn.Linear(prev, h))
                    self.bns.append(nn.BatchNorm1d(h))
                    prev = h
                self.output = nn.Linear(prev, num_classes)
                self.dropout = nn.Dropout(0.2)

            def forward(self, x):
                for i, layer in enumerate(self.layers):
                    x = layer(x)
                    x = self.bns[i](x)
                    x = torch.relu(x)
                    x = self.dropout(x)
                x = self.output(x)
                return x

        model = Net(input_dim, num_classes).to(device)
        optimizer = AdamW(model.parameters(), lr=1e-3, weight_decay=1e-4)
        criterion = nn.CrossEntropyLoss()

        num_epochs = 500
        patience = 30
        best_val_acc = 0.0
        counter = 0
        best_state = None

        for epoch in range(num_epochs):
            model.train()
            train_loss = 0.0
            num_batches = 0
            for inputs, targets in train_loader:
                inputs = inputs.to(device)
                targets = targets.to(device)
                optimizer.zero_grad()
                outputs = model(inputs)
                loss = criterion(outputs, targets)
                loss.backward()
                optimizer.step()
                train_loss += loss.item()
                num_batches += 1

            model.eval()
            val_correct = 0
            val_total = 0
            with torch.no_grad():
                for inputs, targets in val_loader:
                    inputs = inputs.to(device)
                    targets = targets.to(device)
                    outputs = model(inputs)
                    _, preds = torch.max(outputs, 1)
                    val_total += targets.size(0)
                    val_correct += (preds == targets).sum().item()
            val_acc = val_correct / val_total

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