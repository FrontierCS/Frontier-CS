import torch
import torch.nn as nn
import copy

class ResBlock(nn.Module):
    def __init__(self, dim):
        super().__init__()
        self.fc1 = nn.Linear(dim, dim)
        self.bn1 = nn.BatchNorm1d(dim)
        self.fc2 = nn.Linear(dim, dim)
        self.bn2 = nn.BatchNorm1d(dim)
        self.relu = nn.ReLU(inplace=True)

    def forward(self, x):
        residual = x
        out = self.fc1(x)
        out = self.bn1(out)
        out = self.relu(out)
        out = self.fc2(out)
        out = self.bn2(out)
        out += residual
        out = self.relu(out)
        return out

class Net(nn.Module):
    def __init__(self, input_dim, num_classes):
        super().__init__()
        self.input_proj = nn.Linear(input_dim, 256)
        self.bn_in = nn.BatchNorm1d(256)
        self.relu = nn.ReLU(inplace=True)
        self.blocks = nn.ModuleList([ResBlock(256) for _ in range(6)])
        self.output = nn.Linear(256, num_classes)

    def forward(self, x):
        x = self.input_proj(x)
        x = self.bn_in(x)
        x = self.relu(x)
        for block in self.blocks:
            x = block(x)
        x = self.output(x)
        return x

class Solution:
    def solve(self, train_loader, val_loader, metadata: dict = None) -> torch.nn.Module:
        input_dim = metadata["input_dim"]
        num_classes = metadata["num_classes"]
        device = torch.device(metadata["device"])
        model = Net(input_dim, num_classes).to(device)
        optimizer = torch.optim.Adam(model.parameters(), lr=0.001, weight_decay=1e-4)
        criterion = nn.CrossEntropyLoss()
        scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=100)
        epochs = 200
        best_val_acc = 0.0
        best_model_state = None
        for epoch in range(epochs):
            model.train()
            for inputs, targets in train_loader:
                inputs = inputs.to(device)
                targets = targets.to(device)
                optimizer.zero_grad()
                outputs = model(inputs)
                loss = criterion(outputs, targets)
                loss.backward()
                optimizer.step()
            scheduler.step()
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
            if val_acc > best_val_acc:
                best_val_acc = val_acc
                best_model_state = copy.deepcopy(model.state_dict())
        if best_model_state is not None:
            model.load_state_dict(best_model_state)
        return model