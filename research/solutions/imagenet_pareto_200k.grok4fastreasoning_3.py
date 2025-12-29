import torch
import torch.nn as nn
from torch.optim.lr_scheduler import ReduceLROnPlateau
import copy

class Solution:
    def solve(self, train_loader, val_loader, metadata: dict = None) -> torch.nn.Module:
        device = metadata["device"]
        input_dim = metadata["input_dim"]
        num_classes = metadata["num_classes"]
        
        model = nn.Sequential(
            nn.Linear(input_dim, 300),
            nn.BatchNorm1d(300),
            nn.ReLU(),
            nn.Linear(300, 192),
            nn.BatchNorm1d(192),
            nn.ReLU(),
            nn.Dropout(0.1),
            nn.Linear(192, num_classes)
        )
        
        model.to(device)
        
        optimizer = torch.optim.Adam(model.parameters(), lr=0.001, weight_decay=1e-4)
        criterion = nn.CrossEntropyLoss()
        scheduler = ReduceLROnPlateau(optimizer, mode='max', factor=0.5, patience=10)
        
        num_epochs = 200
        patience = 20
        no_improve = 0
        best_val_acc = 0.0
        best_state = None
        
        for epoch in range(num_epochs):
            model.train()
            train_loss = 0.0
            for inputs, targets in train_loader:
                inputs, targets = inputs.to(device), targets.to(device)
                optimizer.zero_grad()
                outputs = model(inputs)
                loss = criterion(outputs, targets)
                loss.backward()
                optimizer.step()
                train_loss += loss.item()
            
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
                no_improve = 0
                best_state = copy.deepcopy(model.state_dict())
            else:
                no_improve += 1
            
            scheduler.step(val_acc)
            
            if no_improve >= patience:
                break
        
        if best_state is not None:
            model.load_state_dict(best_state)
        
        return model