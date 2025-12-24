import torch
import torch.nn as nn
import copy

class Solution:
    def solve(self, train_loader, val_loader, metadata: dict = None) -> torch.nn.Module:
        device = metadata["device"]
        input_dim = metadata["input_dim"]
        num_classes = metadata["num_classes"]
        
        class Net(nn.Module):
            def __init__(self, input_dim, num_classes, hidden_dim=1424):
                super().__init__()
                self.seq = nn.Sequential(
                    nn.Linear(input_dim, hidden_dim),
                    nn.BatchNorm1d(hidden_dim),
                    nn.ReLU(inplace=True),
                    nn.Dropout(0.05),
                    nn.Linear(hidden_dim, hidden_dim),
                    nn.BatchNorm1d(hidden_dim),
                    nn.ReLU(inplace=True),
                    nn.Dropout(0.05),
                    nn.Linear(hidden_dim, hidden_dim),
                    nn.BatchNorm1d(hidden_dim),
                    nn.ReLU(inplace=True),
                    nn.Dropout(0.05),
                    nn.Linear(hidden_dim, num_classes)
                )
            
            def forward(self, x):
                return self.seq(x)
        
        model = Net(input_dim, num_classes)
        model.to(device)
        
        optimizer = torch.optim.Adam(model.parameters(), lr=0.001, weight_decay=1e-4)
        criterion = nn.CrossEntropyLoss()
        
        best_val_acc = 0.0
        patience = 15
        counter = 0
        max_epochs = 150
        best_model = None
        
        for epoch in range(max_epochs):
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
            
            # validate
            model.eval()
            val_correct = 0
            val_total = 0
            with torch.no_grad():
                for inputs, targets in val_loader:
                    inputs = inputs.to(device)
                    targets = targets.to(device)
                    outputs = model(inputs)
                    pred = outputs.argmax(dim=1)
                    val_correct += (pred == targets).sum().item()
                    val_total += targets.numel()
            val_acc = val_correct / val_total if val_total > 0 else 0.0
            
            if val_acc > best_val_acc:
                best_val_acc = val_acc
                best_model = copy.deepcopy(model)
                counter = 0
            else:
                counter += 1
            
            if counter >= patience:
                break
        
        return best_model if best_model is not None else model
