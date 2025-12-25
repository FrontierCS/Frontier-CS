import torch
import torch.nn as nn

class Solution:
    def solve(self, train_loader, val_loader, metadata: dict = None) -> torch.nn.Module:
        device = metadata["device"]
        input_dim = metadata["input_dim"]
        num_classes = metadata["num_classes"]

        class MLP(nn.Module):
            def __init__(self, input_dim, num_classes):
                super().__init__()
                self.layers = nn.Sequential(
                    nn.Linear(input_dim, 320),
                    nn.BatchNorm1d(320),
                    nn.ReLU(),
                    nn.Dropout(0.05),
                    nn.Linear(320, 160),
                    nn.BatchNorm1d(160),
                    nn.ReLU(),
                    nn.Dropout(0.05),
                    nn.Linear(160, 80),
                    nn.BatchNorm1d(80),
                    nn.ReLU(),
                    nn.Linear(80, num_classes)
                )

            def forward(self, x):
                return self.layers(x)

        model = MLP(input_dim, num_classes).to(device)
        optimizer = torch.optim.Adam(model.parameters(), lr=0.001, weight_decay=1e-4)
        criterion = nn.CrossEntropyLoss()

        best_val_acc = 0.0
        best_state = None
        patience = 20
        patience_counter = 0

        for epoch in range(200):
            model.train()
            for inputs, targets in train_loader:
                inputs, targets = inputs.to(device), targets.to(device)
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
                    inputs, targets = inputs.to(device), targets.to(device)
                    outputs = model(inputs)
                    preds = outputs.argmax(dim=1)
                    correct += (preds == targets).sum().item()
                    total += targets.size(0)
            val_acc = correct / total

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
