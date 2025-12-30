import torch
import torch.nn as nn
import torch.optim as optim
import torch.nn.functional as F
from torch.optim.lr_scheduler import CosineAnnealingLR
import copy
import math

class ResidualBlock(nn.Module):
    def __init__(self, in_dim, out_dim, dropout=0.2):
        super().__init__()
        self.norm1 = nn.BatchNorm1d(in_dim)
        self.fc1 = nn.Linear(in_dim, out_dim)
        self.norm2 = nn.BatchNorm1d(out_dim)
        self.fc2 = nn.Linear(out_dim, out_dim)
        self.dropout = nn.Dropout(dropout)
        self.act = nn.GELU()
        
        self.shortcut = nn.Linear(in_dim, out_dim) if in_dim != out_dim else nn.Identity()
        
    def forward(self, x):
        identity = self.shortcut(x)
        
        out = self.norm1(x)
        out = self.fc1(out)
        out = self.act(out)
        out = self.dropout(out)
        
        out = self.norm2(out)
        out = self.fc2(out)
        
        out = out + identity
        out = self.act(out)
        out = self.dropout(out)
        
        return out

class EfficientNet(nn.Module):
    def __init__(self, input_dim=384, num_classes=128, param_limit=500000):
        super().__init__()
        
        # Design to stay under 500K parameters
        # Using residual blocks with bottleneck design
        hidden1 = 512
        hidden2 = 256
        hidden3 = 256
        hidden4 = 128
        
        # Calculate parameters to ensure we're under limit
        self.blocks = nn.ModuleList([
            ResidualBlock(input_dim, hidden1, dropout=0.2),
            ResidualBlock(hidden1, hidden2, dropout=0.2),
            ResidualBlock(hidden2, hidden3, dropout=0.2),
            ResidualBlock(hidden3, hidden4, dropout=0.2),
        ])
        
        self.final_norm = nn.BatchNorm1d(hidden4)
        self.classifier = nn.Linear(hidden4, num_classes)
        
        # Initialize weights
        self.apply(self._init_weights)
        
    def _init_weights(self, m):
        if isinstance(m, nn.Linear):
            nn.init.kaiming_normal_(m.weight, mode='fan_out', nonlinearity='relu')
            if m.bias is not None:
                nn.init.constant_(m.bias, 0)
        elif isinstance(m, nn.BatchNorm1d):
            nn.init.constant_(m.weight, 1)
            nn.init.constant_(m.bias, 0)
    
    def forward(self, x):
        for block in self.blocks:
            x = block(x)
        x = self.final_norm(x)
        x = self.classifier(x)
        return x

class Solution:
    def solve(self, train_loader, val_loader, metadata: dict = None):
        device = metadata.get("device", "cpu")
        input_dim = metadata["input_dim"]
        num_classes = metadata["num_classes"]
        param_limit = metadata["param_limit"]
        
        # Create model with parameter constraint
        model = EfficientNet(input_dim, num_classes, param_limit)
        model.to(device)
        
        # Verify parameter count
        total_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
        if total_params > param_limit:
            # Scale down if needed
            model = self._create_scaled_model(input_dim, num_classes, param_limit)
            model.to(device)
        
        # Training setup
        criterion = nn.CrossEntropyLoss(label_smoothing=0.1)
        optimizer = optim.AdamW(model.parameters(), lr=0.001, weight_decay=0.01)
        scheduler = CosineAnnealingLR(optimizer, T_max=50, eta_min=1e-6)
        
        # Training loop with early stopping
        best_val_acc = 0
        best_model_state = None
        patience = 10
        patience_counter = 0
        
        num_epochs = 100
        
        for epoch in range(num_epochs):
            # Training phase
            model.train()
            train_loss = 0
            train_correct = 0
            train_total = 0
            
            for batch_idx, (inputs, targets) in enumerate(train_loader):
                inputs, targets = inputs.to(device), targets.to(device)
                
                optimizer.zero_grad()
                outputs = model(inputs)
                loss = criterion(outputs, targets)
                loss.backward()
                
                # Gradient clipping
                torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
                
                optimizer.step()
                
                train_loss += loss.item()
                _, predicted = outputs.max(1)
                train_total += targets.size(0)
                train_correct += predicted.eq(targets).sum().item()
            
            # Validation phase
            model.eval()
            val_loss = 0
            val_correct = 0
            val_total = 0
            
            with torch.no_grad():
                for inputs, targets in val_loader:
                    inputs, targets = inputs.to(device), targets.to(device)
                    outputs = model(inputs)
                    loss = criterion(outputs, targets)
                    
                    val_loss += loss.item()
                    _, predicted = outputs.max(1)
                    val_total += targets.size(0)
                    val_correct += predicted.eq(targets).sum().item()
            
            train_acc = 100. * train_correct / train_total if train_total > 0 else 0
            val_acc = 100. * val_correct / val_total if val_total > 0 else 0
            
            # Update scheduler
            scheduler.step()
            
            # Early stopping and model selection
            if val_acc > best_val_acc:
                best_val_acc = val_acc
                best_model_state = copy.deepcopy(model.state_dict())
                patience_counter = 0
            else:
                patience_counter += 1
            
            # Stop if no improvement for patience epochs
            if patience_counter >= patience and epoch > 20:
                break
        
        # Load best model
        if best_model_state is not None:
            model.load_state_dict(best_model_state)
        
        return model
    
    def _create_scaled_model(self, input_dim, num_classes, param_limit):
        """Create a smaller model if initial design exceeds limit"""
        # Progressive scaling based on parameter budget
        base_hidden = 384
        
        for scale in [0.9, 0.8, 0.7, 0.6, 0.5]:
            hidden1 = int(base_hidden * scale)
            hidden2 = int(base_hidden * scale * 0.75)
            hidden3 = int(base_hidden * scale * 0.75)
            hidden4 = int(base_hidden * scale * 0.5)
            
            model = nn.Sequential(
                nn.Linear(input_dim, hidden1),
                nn.BatchNorm1d(hidden1),
                nn.GELU(),
                nn.Dropout(0.2),
                
                nn.Linear(hidden1, hidden2),
                nn.BatchNorm1d(hidden2),
                nn.GELU(),
                nn.Dropout(0.2),
                
                nn.Linear(hidden2, hidden3),
                nn.BatchNorm1d(hidden3),
                nn.GELU(),
                nn.Dropout(0.2),
                
                nn.Linear(hidden3, hidden4),
                nn.BatchNorm1d(hidden4),
                nn.GELU(),
                nn.Dropout(0.2),
                
                nn.Linear(hidden4, num_classes)
            )
            
            total_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
            if total_params <= param_limit:
                return model
        
        # Fallback to minimal model
        return nn.Sequential(
            nn.Linear(input_dim, 256),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(256, 128),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(128, num_classes)
        )