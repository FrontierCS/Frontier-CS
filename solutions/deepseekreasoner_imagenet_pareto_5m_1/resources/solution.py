import torch
import torch.nn as nn
import torch.optim as optim
from torch.optim.lr_scheduler import ReduceLROnPlateau, CosineAnnealingLR
import numpy as np
from tqdm import tqdm

class ResidualBlock(nn.Module):
    def __init__(self, in_features, out_features, dropout_rate=0.2):
        super().__init__()
        self.linear1 = nn.Linear(in_features, out_features)
        self.bn1 = nn.BatchNorm1d(out_features)
        self.linear2 = nn.Linear(out_features, out_features)
        self.bn2 = nn.BatchNorm1d(out_features)
        self.dropout = nn.Dropout(dropout_rate)
        self.relu = nn.ReLU()
        
        self.shortcut = nn.Identity() if in_features == out_features else nn.Linear(in_features, out_features)
        
    def forward(self, x):
        identity = self.shortcut(x)
        out = self.linear1(x)
        out = self.bn1(out)
        out = self.relu(out)
        out = self.dropout(out)
        out = self.linear2(out)
        out = self.bn2(out)
        out += identity
        out = self.relu(out)
        return out

class EfficientNet(nn.Module):
    def __init__(self, input_dim, num_classes, param_limit=5000000):
        super().__init__()
        
        # Bottleneck architecture for efficiency
        hidden_dims = [512, 768, 1024, 768, 512]
        
        layers = []
        prev_dim = input_dim
        
        # Initial projection
        layers.append(nn.Linear(prev_dim, hidden_dims[0]))
        layers.append(nn.BatchNorm1d(hidden_dims[0]))
        layers.append(nn.ReLU())
        layers.append(nn.Dropout(0.2))
        prev_dim = hidden_dims[0]
        
        # Residual blocks
        for i in range(3):
            layers.append(ResidualBlock(prev_dim, hidden_dims[i+1], 0.2))
            prev_dim = hidden_dims[i+1]
        
        # Final projection
        layers.append(nn.Linear(prev_dim, hidden_dims[-1]))
        layers.append(nn.BatchNorm1d(hidden_dims[-1]))
        layers.append(nn.ReLU())
        layers.append(nn.Dropout(0.2))
        
        # Classifier
        layers.append(nn.Linear(hidden_dims[-1], num_classes))
        
        self.network = nn.Sequential(*layers)
        
        # Verify parameter count
        total_params = sum(p.numel() for p in self.parameters() if p.requires_grad)
        if total_params > param_limit:
            raise ValueError(f"Model has {total_params} parameters, exceeding limit of {param_limit}")
    
    def forward(self, x):
        return self.network(x)

class Solution:
    def solve(self, train_loader, val_loader, metadata: dict = None):
        device = metadata.get("device", "cpu")
        input_dim = metadata["input_dim"]
        num_classes = metadata["num_classes"]
        
        # Create model with parameter constraint
        model = EfficientNet(input_dim, num_classes, metadata["param_limit"])
        model.to(device)
        
        # Optimizer and scheduler
        optimizer = optim.AdamW(model.parameters(), lr=0.001, weight_decay=1e-4)
        scheduler = CosineAnnealingLR(optimizer, T_max=100)
        
        criterion = nn.CrossEntropyLoss()
        
        # Training loop
        num_epochs = 200
        best_val_acc = 0
        best_model_state = None
        
        for epoch in range(num_epochs):
            # Training phase
            model.train()
            train_loss = 0
            train_correct = 0
            train_total = 0
            
            pbar = tqdm(train_loader, desc=f"Epoch {epoch+1}/{num_epochs} [Train]", leave=False)
            for inputs, targets in pbar:
                inputs, targets = inputs.to(device), targets.to(device)
                
                optimizer.zero_grad()
                outputs = model(inputs)
                loss = criterion(outputs, targets)
                loss.backward()
                
                torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
                optimizer.step()
                
                train_loss += loss.item()
                _, predicted = outputs.max(1)
                train_total += targets.size(0)
                train_correct += predicted.eq(targets).sum().item()
                
                pbar.set_postfix(loss=loss.item())
            
            train_acc = 100. * train_correct / train_total
            
            # Validation phase
            model.eval()
            val_correct = 0
            val_total = 0
            
            with torch.no_grad():
                for inputs, targets in val_loader:
                    inputs, targets = inputs.to(device), targets.to(device)
                    outputs = model(inputs)
                    _, predicted = outputs.max(1)
                    val_total += targets.size(0)
                    val_correct += predicted.eq(targets).sum().item()
            
            val_acc = 100. * val_correct / val_total
            
            # Save best model
            if val_acc > best_val_acc:
                best_val_acc = val_acc
                best_model_state = model.state_dict().copy()
            
            # Learning rate scheduling
            scheduler.step()
            
            # Early stopping condition
            if epoch > 50 and best_val_acc > 92.0:
                break
        
        # Load best model
        if best_model_state is not None:
            model.load_state_dict(best_model_state)
        
        return model
