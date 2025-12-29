import torch
import torch.nn as nn
import copy

class ResidualBlock(nn.Module):
    def __init__(self, dim, drop_prob=0.1):
        super().__init__()
        self.fc1 = nn.Linear(dim, dim)
        self.bn1 = nn.BatchNorm1d(dim)
        self.fc2 = nn.Linear(dim, dim)
        self.bn2 = nn.BatchNorm1d(dim)
        self.relu = nn.ReLU(inplace=True)
        self.dropout = nn.Dropout(drop_prob)

    def forward(self, x):
        residual = x
        out = self.fc1(x)
        out = self.bn1(out)
        out = self.relu(out)
        out = self.dropout(out)
        out = self.fc2(out)
        out = self.bn2(out)
        out += residual
        out = self.relu(out)
        return out

class ResMLP(nn.Module):
    def __init__(self, input_dim, num_classes, hidden_dim=1054, num_blocks=2, drop_prob=0.1):
        super().__init__()
        self.proj = nn.Linear(input_dim, hidden_dim)
        self.bn_proj = nn.BatchNorm1d(hidden_dim)
        self.relu = nn.ReLU(inplace=True)
        self.blocks = nn.ModuleList([
            ResidualBlock(hidden_dim, drop_prob) for _ in range(num_blocks)
        ])
        self.head = nn.Linear(hidden_dim, num_classes)

    def forward(self, x):
        x = self.proj(x)
        x = self.bn_proj(x)
        x = self.relu(x)
        for block in self.blocks:
            x = block(x)
        x = self.head(x)
        return x

class Solution:
    def solve(self, train_loader, val_loader, metadata: dict = None) -> torch.nn.Module:
        input_dim = metadata["input_dim"]
        num_classes = metadata["num_classes"]
        device = metadata["device"]
        model = ResMLP(input_dim, num_classes).to(device)
        optimizer = torch.optim.Adam(model.parameters(), lr=0.001, weight_decay=1e-4)
        criterion = nn.CrossEntropyLoss()
        scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(optimizer, mode='max', factor=0.5, patience=10)
        best_val_acc = -1.0
        best_state = None
        patience_counter = 0
        patience = 30
        for epoch in range(1, 501):
            model.train()
            running_loss = 0.0
            num_batches = 0
            for inputs, targets in train_loader:
                inputs, targets = inputs.to(device), targets.to(device)
                optimizer.zero_grad()
                outputs = model(inputs)
                loss = criterion(outputs, targets)
                loss.backward()
                optimizer.step()
                running_loss += loss.item()
                num_batches += 1
            model.eval()
            correct = 0
            total = 0
            with torch.no_grad():
                for inputs, targets in val_loader:
                    inputs, targets = inputs.to(device), targets.to(device)
                    outputs = model(inputs)
                    pred = outputs.argmax(dim=1)
                    correct += (pred == targets).sum().item()
                    total += targets.size(0)
            val_acc = correct / total if total > 0 else 0.0
            scheduler.step(val_acc)
            if val_acc > best_val_acc:
                best_val_acc = val_acc
                best_state = copy.deepcopy(model.state_dict())
                patience_counter = 0
            else:
                patience_counter += 1
            if patience_counter >= patience:
                break
        if best_state is not None:
            model.load_state_dict(best_state)
        return model