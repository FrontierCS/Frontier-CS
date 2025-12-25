import torch
import torch.nn as nn

class Solution:
    def solve(self, train_loader, val_loader, metadata: dict = None) -> torch.nn.Module:
        input_dim = metadata["input_dim"]
        num_classes = metadata["num_classes"]
        device = metadata["device"]

        model = nn.Sequential(
            nn.Linear(input_dim, 995),
            nn.BatchNorm1d(995),
            nn.ReLU(),
            nn.Dropout(0.05),
            nn.Linear(995, 995),
            nn.BatchNorm1d(995),
            nn.ReLU(),
            nn.Dropout(0.05),
            nn.Linear(995, 995),
            nn.BatchNorm1d(995),
            nn.ReLU(),
            nn.Dropout(0.05),
            nn.Linear(995, num_classes)
        ).to(device)

        optimizer = torch.optim.AdamW(model.parameters(), lr=0.001, weight_decay=1e-4)
        criterion = nn.CrossEntropyLoss()
        scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(optimizer, mode='min', factor=0.5, patience=10)

        def train_epoch(model, loader, optimizer, criterion, device):
            model.train()
            total_loss = 0.0
            correct = 0
            total = 0
            for inputs, targets in loader:
                inputs = inputs.to(device)
                targets = targets.to(device)
                optimizer.zero_grad()
                outputs = model(inputs)
                loss = criterion(outputs, targets)
                loss.backward()
                optimizer.step()
                total_loss += loss.item()
                pred = outputs.argmax(dim=1)
                correct += (pred == targets).sum().item()
                total += targets.size(0)
            return total_loss / len(loader), correct / total

        def val_epoch(model, loader, criterion, device):
            model.eval()
            total_loss = 0.0
            correct = 0
            total = 0
            with torch.no_grad():
                for inputs, targets in loader:
                    inputs = inputs.to(device)
                    targets = targets.to(device)
                    outputs = model(inputs)
                    loss = criterion(outputs, targets)
                    total_loss += loss.item()
                    pred = outputs.argmax(dim=1)
                    correct += (pred == targets).sum().item()
                    total += targets.size(0)
            return total_loss / len(loader), correct / total

        best_val_acc = -1.0
        best_state = None
        patience = 50
        counter = 0
        num_epochs = 1000

        for epoch in range(num_epochs):
            train_loss, train_acc = train_epoch(model, train_loader, optimizer, criterion, device)
            val_loss, val_acc = val_epoch(model, val_loader, criterion, device)
            scheduler.step(val_loss)

            if val_acc > best_val_acc:
                best_val_acc = val_acc
                best_state = {k: v.clone() for k, v in model.state_dict().items()}
                counter = 0
            else:
                counter += 1

            if counter >= patience:
                break

        if best_state is not None:
            model.load_state_dict(best_state)

        return model
