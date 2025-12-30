import torch
import torch.nn as nn

class Solution:
    def solve(self, train_loader, val_loader, metadata: dict = None) -> torch.nn.Module:
        device = metadata["device"]
        input_dim = metadata["input_dim"]
        num_classes = metadata["num_classes"]

        class Net(nn.Module):
            def __init__(self, input_dim, num_classes, hidden_dim):
                super(Net, self).__init__()
                layers = []
                prev = input_dim
                for _ in range(4):
                    layers.append(nn.Linear(prev, hidden_dim))
                    layers.append(nn.BatchNorm1d(hidden_dim))
                    layers.append(nn.ReLU(inplace=True))
                    layers.append(nn.Dropout(0.1))
                    prev = hidden_dim
                layers.append(nn.Linear(hidden_dim, num_classes))
                self.net = nn.Sequential(*layers)

            def forward(self, x):
                return self.net(x)

        model = Net(input_dim, num_classes, 1206)
        model.to(device)

        optimizer = torch.optim.Adam(model.parameters(), lr=1e-3, weight_decay=1e-4)
        scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(optimizer, 'min', factor=0.5, patience=20, verbose=False)
        criterion = nn.CrossEntropyLoss()

        best_acc = 0.0
        best_state = None
        num_epochs = 300

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
            val_loss = 0.0
            correct = 0
            total = 0
            with torch.no_grad():
                for inputs, targets in val_loader:
                    inputs = inputs.to(device)
                    targets = targets.to(device)
                    outputs = model(inputs)
                    loss = criterion(outputs, targets)
                    val_loss += loss.item() * inputs.size(0)
                    pred = outputs.argmax(dim=1)
                    correct += (pred == targets).sum().item()
                    total += targets.size(0)
            if total > 0:
                val_loss /= total
                val_acc = correct / total
                if val_acc > best_acc:
                    best_acc = val_acc
                    best_state = {k: v.clone() for k, v in model.state_dict().items()}
                scheduler.step(val_loss)

        if best_state is not None:
            model.load_state_dict(best_state)
        return model