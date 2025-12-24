import torch
import torch.nn as nn
import copy

class Solution:
    def solve(self, train_loader, val_loader, metadata: dict = None) -> torch.nn.Module:
        input_dim = metadata["input_dim"]
        num_classes = metadata["num_classes"]
        device = metadata.get("device", "cpu")

        class Net(nn.Module):
            def __init__(self, input_dim, num_classes, hidden_dim):
                super(Net, self).__init__()
                self.fc1 = nn.Linear(input_dim, hidden_dim)
                self.fc2 = nn.Linear(hidden_dim, hidden_dim)
                self.fc3 = nn.Linear(hidden_dim, hidden_dim)
                self.fc4 = nn.Linear(hidden_dim, num_classes)
                self.dropout = nn.Dropout(0.2)

            def forward(self, x):
                x = torch.relu(self.fc1(x))
                x = self.dropout(x)
                x = torch.relu(self.fc2(x))
                x = self.dropout(x)
                x = torch.relu(self.fc3(x))
                x = self.dropout(x)
                x = self.fc4(x)
                return x

        model = Net(input_dim, num_classes, 1457).to(device)
        optimizer = torch.optim.Adam(model.parameters(), lr=0.001, weight_decay=1e-4)
        criterion = nn.CrossEntropyLoss()

        def train_epoch(model, loader, optimizer, criterion, device):
            model.train()
            total_loss = 0.0
            num_batches = 0
            for inputs, targets in loader:
                inputs = inputs.to(device)
                targets = targets.to(device)
                optimizer.zero_grad()
                outputs = model(inputs)
                loss = criterion(outputs, targets)
                loss.backward()
                optimizer.step()
                total_loss += loss.item()
                num_batches += 1
            return total_loss / num_batches if num_batches > 0 else 0.0

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

        best_val_acc = 0.0
        best_model = None
        patience = 20
        patience_counter = 0
        num_epochs = 200

        for epoch in range(num_epochs):
            train_loss = train_epoch(model, train_loader, optimizer, criterion, device)
            val_acc = evaluate(model, val_loader, device)
            if val_acc > best_val_acc:
                best_val_acc = val_acc
                best_model = copy.deepcopy(model)
                patience_counter = 0
            else:
                patience_counter += 1
                if patience_counter >= patience:
                    break

        if best_model is None:
            best_model = model

        return best_model
