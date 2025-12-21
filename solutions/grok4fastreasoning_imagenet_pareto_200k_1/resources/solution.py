import torch
import torch.nn as nn
import torch.optim as optim

class Solution:
    def solve(self, train_loader, val_loader, metadata: dict = None) -> torch.nn.Module:
        device = metadata["device"]
        input_dim = metadata["input_dim"]
        num_classes = metadata["num_classes"]
        
        class Net(nn.Module):
            def __init__(self):
                super(Net, self).__init__()
                self.fc1 = nn.Linear(input_dim, 350)
                self.bn1 = nn.BatchNorm1d(350)
                self.fc2 = nn.Linear(350, 128)
                self.bn2 = nn.BatchNorm1d(128)
                self.fc3 = nn.Linear(128, 128)
                self.dropout = nn.Dropout(0.3)
            
            def forward(self, x):
                x = torch.relu(self.bn1(self.fc1(x)))
                x = self.dropout(x)
                x = torch.relu(self.bn2(self.fc2(x)))
                x = self.dropout(x)
                x = self.fc3(x)
                return x
        
        model = Net().to(device)
        
        optimizer = optim.Adam(model.parameters(), lr=0.001, weight_decay=1e-4)
        criterion = nn.CrossEntropyLoss()
        
        best_val_acc = 0.0
        best_model_state = None
        patience = 15
        epochs_no_improve = 0
        max_epochs = 300
        
        for epoch in range(max_epochs):
            model.train()
            for inputs, targets in train_loader:
                inputs, targets = inputs.to(device), targets.to(device)
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
                    inputs, targets = inputs.to(device), targets.to(device)
                    outputs = model(inputs)
                    preds = outputs.argmax(dim=1)
                    val_total += targets.size(0)
                    val_correct += (preds == targets).sum().item()
            
            val_acc = val_correct / val_total
            
            if val_acc > best_val_acc:
                best_val_acc = val_acc
                best_model_state = model.state_dict().copy()
                epochs_no_improve = 0
            else:
                epochs_no_improve += 1
            
            if epochs_no_improve >= patience:
                break
        
        if best_model_state is not None:
            model.load_state_dict(best_model_state)
        
        return model
