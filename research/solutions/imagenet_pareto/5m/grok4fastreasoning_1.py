import torch
import torch.nn as nn

class Solution:
    def solve(self, train_loader, val_loader, metadata: dict = None) -> torch.nn.Module:
        input_dim = metadata["input_dim"]
        num_classes = metadata["num_classes"]
        device = metadata["device"]
        param_limit = metadata["param_limit"]

        class ResidualBlock(nn.Module):
            def __init__(self, dim):
                super().__init__()
                self.fc1 = nn.Linear(dim, dim)
                self.bn1 = nn.BatchNorm1d(dim)
                self.fc2 = nn.Linear(dim, dim)
                self.bn2 = nn.BatchNorm1d(dim)
                self.relu = nn.ReLU()

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

        class MyModel(nn.Module):
            def __init__(self, input_dim, num_classes):
                super().__init__()
                hidden_dim = input_dim
                num_blocks = 16
                self.blocks = nn.ModuleList([ResidualBlock(hidden_dim) for _ in range(num_blocks)])
                self.fc_out = nn.Linear(hidden_dim, num_classes)

            def forward(self, x):
                for block in self.blocks:
                    x = block(x)
                return self.fc_out(x)

        model = MyModel(input_dim, num_classes)
        model.to(device)

        optimizer = torch.optim.AdamW(model.parameters(), lr=1e-3, weight_decay=1e-4)
        criterion = nn.CrossEntropyLoss()

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

        best_val_acc = -1.0
        patience_counter = 0
        patience = 30
        best_state = None
        max_epochs = 500

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
                patience_counter = 0
                best_state = model.state_dict().copy()
            else:
                patience_counter += 1

            if patience_counter >= patience:
                break

        if best_state is not None:
            model.load_state_dict(best_state)

        return model