import torch
import torch.nn as nn
from torch.optim.lr_scheduler import ReduceLROnPlateau

class Solution:
    def solve(self, train_loader, val_loader, metadata: dict = None) -> torch.nn.Module:
        input_dim = metadata["input_dim"]
        num_classes = metadata["num_classes"]
        device = metadata["device"]
        
        hidden_dim = 588
        
        class Net(nn.Module):
            def __init__(self, input_dim, hidden_dim, num_classes):
                super().__init__()
                self.fc1 = nn.Linear(input_dim, hidden_dim)
                self.bn1 = nn.BatchNorm1d(hidden_dim)
                self.relu1 = nn.ReLU()
                self.fc2 = nn.Linear(hidden_dim, hidden_dim)
                self.bn2 = nn.BatchNorm1d(hidden_dim)
                self.relu2 = nn.ReLU()
                self.fc3 = nn.Linear(hidden_dim, hidden_dim)
                self.bn3 = nn.BatchNorm1d(hidden_dim)
                self.relu3 = nn.ReLU()
                self.fc4 = nn.Linear(hidden_dim, num_classes)
            
            def forward(self, x):
                x = self.relu1(self.bn1(self.fc1(x)))
                x = self.relu2(self.bn2(self.fc2(x)))
                x = self.relu3(self.bn3(self.fc3(x)))
                x = self.fc4(x)
                return x
        
        model = Net(input_dim, hidden_dim, num_classes).to(device)
        
        optimizer = torch.optim.Adam(model.parameters(), lr=0.001, weight_decay=1e-4)
        scheduler = ReduceLROnPlateau(optimizer, mode='min', factor=0.5, patience=10)
        criterion = nn.CrossEntropyLoss()
        
        best_val_acc = 0.0
        best_state = None
        patience_counter = 0
        patience = 20
        num_epochs = 200
        
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
                    val_loss += loss.item()
                    pred = outputs.argmax(dim=1)
                    correct += (pred == targets).sum().item()
                    total += targets.size(0)
            
            val_acc = correct / total
            avg_val_loss = val_loss / len(val_loader)
            
            scheduler.step(avg_val_loss)
            
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
