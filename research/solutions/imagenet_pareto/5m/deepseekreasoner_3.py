import torch
import torch.nn as nn
import torch.optim as optim
from torch.optim.lr_scheduler import CosineAnnealingLR, ReduceLROnPlateau
import numpy as np
from copy import deepcopy
import time

class ResidualBlock(nn.Module):
    def __init__(self, in_features, out_features, dropout_rate=0.2):
        super().__init__()
        self.norm1 = nn.BatchNorm1d(in_features)
        self.linear1 = nn.Linear(in_features, out_features)
        self.norm2 = nn.BatchNorm1d(out_features)
        self.linear2 = nn.Linear(out_features, out_features)
        self.dropout = nn.Dropout(dropout_rate)
        self.relu = nn.ReLU()
        
        if in_features != out_features:
            self.shortcut = nn.Linear(in_features, out_features)
        else:
            self.shortcut = nn.Identity()
    
    def forward(self, x):
        identity = self.shortcut(x)
        out = self.norm1(x)
        out = self.relu(out)
        out = self.linear1(out)
        out = self.norm2(out)
        out = self.relu(out)
        out = self.dropout(out)
        out = self.linear2(out)
        out += identity
        return out

class EfficientNet(nn.Module):
    def __init__(self, input_dim, num_classes, param_limit=5000000):
        super().__init__()
        self.input_dim = input_dim
        self.num_classes = num_classes
        
        # Carefully designed architecture to maximize capacity within 5M params
        # Using expansion-contraction pattern with residual connections
        hidden1 = 1536  # 4x expansion
        hidden2 = 1024  # ~2.7x
        hidden3 = 768   # 2x
        hidden4 = 512   # ~1.33x
        
        self.input_proj = nn.Sequential(
            nn.Linear(input_dim, hidden1),
            nn.BatchNorm1d(hidden1),
            nn.ReLU(),
            nn.Dropout(0.3)
        )
        
        # Residual blocks with bottleneck-like structure
        self.block1 = ResidualBlock(hidden1, hidden2, dropout_rate=0.25)
        self.block2 = ResidualBlock(hidden2, hidden3, dropout_rate=0.2)
        self.block3 = ResidualBlock(hidden3, hidden4, dropout_rate=0.15)
        
        # Final layers
        self.norm_final = nn.BatchNorm1d(hidden4)
        self.final_act = nn.ReLU()
        self.dropout_final = nn.Dropout(0.1)
        self.classifier = nn.Linear(hidden4, num_classes)
        
        # Initialize weights
        self._initialize_weights()
        
        # Verify parameter count
        total_params = sum(p.numel() for p in self.parameters() if p.requires_grad)
        if total_params > param_limit:
            raise ValueError(f"Model has {total_params} params, exceeds {param_limit} limit")
    
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
        x = self.input_proj(x)
        x = self.block1(x)
        x = self.block2(x)
        x = self.block3(x)
        x = self.norm_final(x)
        x = self.final_act(x)
        x = self.dropout_final(x)
        x = self.classifier(x)
        return x

class Solution:
    def solve(self, train_loader, val_loader, metadata: dict = None):
        device = metadata.get("device", "cpu")
        input_dim = metadata["input_dim"]
        num_classes = metadata["num_classes"]
        param_limit = metadata["param_limit"]
        
        # Create model with parameter budget
        model = EfficientNet(input_dim, num_classes, param_limit)
        model.to(device)
        
        # Count parameters
        total_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
        print(f"Model parameters: {total_params:,}")
        
        # Training configuration
        criterion = nn.CrossEntropyLoss(label_smoothing=0.1)
        optimizer = optim.AdamW(
            model.parameters(),
            lr=0.001,
            weight_decay=0.05,
            betas=(0.9, 0.999)
        )
        
        # Multi-step scheduler with warmup
        scheduler = optim.lr_scheduler.OneCycleLR(
            optimizer,
            max_lr=0.003,
            total_steps=100,
            pct_start=0.1,
            anneal_strategy='cos'
        )
        
        # Early stopping
        best_val_acc = 0.0
        best_model_state = None
        patience = 10
        patience_counter = 0
        
        num_epochs = 100
        for epoch in range(num_epochs):
            # Training phase
            model.train()
            train_loss = 0.0
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
                scheduler.step()
                
                train_loss += loss.item()
                _, predicted = outputs.max(1)
                train_total += targets.size(0)
                train_correct += predicted.eq(targets).sum().item()
            
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
            
            # Early stopping and model checkpointing
            if val_acc > best_val_acc:
                best_val_acc = val_acc
                best_model_state = deepcopy(model.state_dict())
                patience_counter = 0
            else:
                patience_counter += 1
            
            if patience_counter >= patience:
                print(f"Early stopping at epoch {epoch}")
                break
            
            if (epoch + 1) % 10 == 0:
                print(f"Epoch [{epoch+1}/{num_epochs}] "
                      f"Train Loss: {train_loss/len(train_loader):.4f} "
                      f"Train Acc: {train_acc:.2f}% "
                      f"Val Acc: {val_acc:.2f}% "
                      f"LR: {optimizer.param_groups[0]['lr']:.6f}")
        
        # Load best model
        model.load_state_dict(best_model_state)
        
        # Final validation check
        model.eval()
        final_val_correct = 0
        final_val_total = 0
        
        with torch.no_grad():
            for inputs, targets in val_loader:
                inputs, targets = inputs.to(device), targets.to(device)
                outputs = model(inputs)
                _, predicted = outputs.max(1)
                final_val_total += targets.size(0)
                final_val_correct += predicted.eq(targets).sum().item()
        
        final_val_acc = 100. * final_val_correct / final_val_total
        print(f"Best validation accuracy: {best_val_acc:.2f}%")
        print(f"Final validation accuracy: {final_val_acc:.2f}%")
        
        return model