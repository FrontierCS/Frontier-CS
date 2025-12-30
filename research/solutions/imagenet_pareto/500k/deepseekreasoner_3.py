import torch
import torch.nn as nn
import torch.optim as optim
import torch.nn.functional as F
from torch.optim.lr_scheduler import CosineAnnealingLR, ReduceLROnPlateau
import numpy as np
import copy

class ResidualBlock(nn.Module):
    def __init__(self, in_dim, out_dim, stride=1, dropout=0.1):
        super().__init__()
        self.bn1 = nn.BatchNorm1d(in_dim)
        self.conv1 = nn.Linear(in_dim, out_dim)
        self.bn2 = nn.BatchNorm1d(out_dim)
        self.conv2 = nn.Linear(out_dim, out_dim)
        self.dropout = nn.Dropout(dropout)
        
        self.shortcut = nn.Sequential()
        if stride != 1 or in_dim != out_dim:
            self.shortcut = nn.Linear(in_dim, out_dim)
            
    def forward(self, x):
        residual = self.shortcut(x)
        
        out = self.bn1(x)
        out = F.relu(out)
        out = self.conv1(out)
        out = self.bn2(out)
        out = F.relu(out)
        out = self.dropout(out)
        out = self.conv2(out)
        
        out += residual
        return out

class OptimizedModel(nn.Module):
    def __init__(self, input_dim=384, num_classes=128, param_limit=500000):
        super().__init__()
        
        # Optimized architecture to maximize capacity within budget
        # Starting with wider layers then compressing
        self.initial_conv = nn.Linear(input_dim, 512)
        
        # Residual blocks with progressive compression
        self.block1 = ResidualBlock(512, 384, dropout=0.15)
        self.block2 = ResidualBlock(384, 256, dropout=0.15)
        self.block3 = ResidualBlock(256, 192, dropout=0.1)
        
        # Final layers
        self.final_bn = nn.BatchNorm1d(192)
        self.final_dropout = nn.Dropout(0.1)
        self.final_fc = nn.Linear(192, num_classes)
        
        # Initialize weights
        self._initialize_weights()
        
        # Verify parameter count
        total_params = sum(p.numel() for p in self.parameters() if p.requires_grad)
        if total_params > param_limit:
            raise ValueError(f"Model has {total_params} parameters, exceeding limit of {param_limit}")
    
    def _initialize_weights(self):
        for m in self.modules():
            if isinstance(m, nn.Linear):
                nn.init.kaiming_normal_(m.weight, mode='fan_out', nonlinearity='relu')
                if m.bias is not None:
                    nn.init.constant_(m.bias, 0)
            elif isinstance(m, nn.BatchNorm1d):
                nn.init.constant_(m.weight, 1)
                nn.init.constant_(m.bias, 0)
    
    def forward(self, x):
        x = self.initial_conv(x)
        x = F.relu(x)
        
        x = self.block1(x)
        x = self.block2(x)
        x = self.block3(x)
        
        x = self.final_bn(x)
        x = F.relu(x)
        x = self.final_dropout(x)
        x = self.final_fc(x)
        
        return x

class Solution:
    def solve(self, train_loader, val_loader, metadata: dict = None) -> torch.nn.Module:
        device = metadata.get("device", "cpu")
        input_dim = metadata["input_dim"]
        num_classes = metadata["num_classes"]
        param_limit = metadata["param_limit"]
        
        # Initialize model
        model = OptimizedModel(input_dim, num_classes, param_limit)
        model.to(device)
        
        # Training configuration
        criterion = nn.CrossEntropyLoss(label_smoothing=0.1)
        optimizer = optim.AdamW(
            model.parameters(),
            lr=0.001,
            weight_decay=0.05
        )
        
        # Mixed schedulers
        scheduler_cosine = CosineAnnealingLR(optimizer, T_max=30, eta_min=1e-6)
        scheduler_plateau = ReduceLROnPlateau(optimizer, mode='max', factor=0.5, patience=5)
        
        best_val_acc = 0.0
        best_model_state = None
        patience = 15
        patience_counter = 0
        
        num_epochs = 120
        
        for epoch in range(num_epochs):
            # Training phase
            model.train()
            train_loss = 0.0
            train_correct = 0
            train_total = 0
            
            for inputs, targets in train_loader:
                inputs, targets = inputs.to(device), targets.to(device)
                
                optimizer.zero_grad()
                outputs = model(inputs)
                loss = criterion(outputs, targets)
                loss.backward()
                
                # Gradient clipping
                torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
                optimizer.step()
                
                train_loss += loss.item()
                _, predicted = outputs.max(1)
                train_total += targets.size(0)
                train_correct += predicted.eq(targets).sum().item()
            
            train_acc = train_correct / train_total
            
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
            
            val_acc = val_correct / val_total
            
            # Learning rate scheduling
            scheduler_cosine.step()
            scheduler_plateau.step(val_acc)
            
            # Early stopping with patience
            if val_acc > best_val_acc + 1e-4:
                best_val_acc = val_acc
                best_model_state = copy.deepcopy(model.state_dict())
                patience_counter = 0
            else:
                patience_counter += 1
            
            # Early stopping
            if patience_counter >= patience:
                break
        
        # Load best model
        if best_model_state is not None:
            model.load_state_dict(best_model_state)
        
        return model