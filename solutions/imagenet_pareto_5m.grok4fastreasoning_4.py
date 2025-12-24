import torch
import torch.nn as nn
import torch.optim as optim
from torch.optim.lr_scheduler import ReduceLROnPlateau

class ResidualBlock(nn.Module):
    def __init__(self, dim, dropout_p=0.1):
        super().__init__()
        self.linear1 = nn.Linear(dim, dim)
        self.bn1 = nn.BatchNorm1d(dim)
        self.linear2 = nn.Linear(dim, dim)
        self.bn2 = nn.BatchNorm1d(dim)
        self.dropout = nn.Dropout(dropout_p)
        self.relu = nn.ReLU()

    def forward(self, x):
        residual = x
        out = self.linear1(x)
        out = self.bn1(out)
        out = self.relu(out)
        out = self.dropout(out)
        out = self.linear2(out)
        out = self.bn2(out)
        out += residual
        out = self.relu(out)
        return out

class MyModel(nn.Module):
    def __init__(self, input_dim, hidden_dim, num_classes, num_blocks=3):
        super().__init__()
        self.input_fc = nn.Linear(input_dim, hidden_dim)
        self.input_bn = nn.BatchNorm1d(hidden_dim)
        self.input_relu = nn.ReLU()
        self.input_dropout = nn.Dropout(0.1)
        self.blocks = nn.ModuleList([ResidualBlock(hidden_dim) for _ in range(num_blocks)])
        self.output_fc = nn.Linear(hidden_dim, num_classes)

    def forward(self, x):
        x = self.input_fc(x)
        x = self.input_bn(x)
        x = self.input_relu(x)
        x = self.input_dropout(x)
        for block in self.blocks:
            x = block(x)
        x = self.output_fc(x)
        return x

class Solution:
    def solve(self, train_loader, val_loader, metadata: dict = None) -> torch.nn.Module:
        input_dim = metadata["input_dim"]
        num_classes = metadata["num_classes"]
        device = metadata["device"]
        hidden_dim = 869
        num_blocks = 3
        dropout_p = 0.1

        model = MyModel(input_dim, hidden_dim, num_classes, num_blocks).to(device)
        optimizer = optim.AdamW(model.parameters(), lr=0.001, weight_decay=1e-4)
        criterion = nn.CrossEntropyLoss()
        scheduler = ReduceLROnPlateau(optimizer, mode='max', factor=0.5, patience=10)

        best_val_acc = 0.0
        patience_counter = 0
        patience = 20
        num_epochs = 200
        best_state = None

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
                    val_total += targets.numel()
            val_acc = val_correct / val_total

            scheduler.step(val_acc)

            if val_acc > best_val_acc:
                best_val_acc = val_acc
                best_state = model.state_dict().copy()
                patience_counter = 0
            else:
                patience_counter += 1

            if patience_counter >= patience:
                break

        if best_state is not None:
            model.load_state_dict(best_state)

        return model
