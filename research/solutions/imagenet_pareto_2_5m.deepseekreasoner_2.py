import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim
from torch.optim.lr_scheduler import CosineAnnealingLR
import time
import math
from collections import OrderedDict

class ResidualBlock(nn.Module):
    def __init__(self, in_dim, out_dim, stride=1, dropout=0.0):
        super().__init__()
        self.dropout = dropout
        self.expand = in_dim != out_dim
        
        self.bn1 = nn.BatchNorm1d(in_dim)
        self.conv1 = nn.Linear(in_dim, out_dim, bias=False)
        self.bn2 = nn.BatchNorm1d(out_dim)
        self.conv2 = nn.Linear(out_dim, out_dim, bias=False)
        
        if self.expand:
            self.shortcut = nn.Linear(in_dim, out_dim, bias=False)
        else:
            self.shortcut = nn.Identity()
            
        self.dropout_layer = nn.Dropout(dropout) if dropout > 0 else nn.Identity()
        
    def forward(self, x):
        residual = self.shortcut(x)
        
        out = self.bn1(x)
        out = F.relu(out)
        out = self.conv1(out)
        out = self.bn2(out)
        out = F.relu(out)
        out = self.dropout_layer(out)
        out = self.conv2(out)
        
        return out + residual

class EfficientModel(nn.Module):
    def __init__(self, input_dim=384, num_classes=128, param_limit=2500000):
        super().__init__()
        self.param_limit = param_limit
        
        # Calculate optimal dimensions to stay within parameter budget
        # Using a pyramid structure: 384 -> 512 -> 640 -> 512 -> 384 -> 256 -> 128
        dims = [input_dim, 512, 640, 512, 384, 256, 128]
        
        layers = []
        for i in range(len(dims) - 1):
            layers.append(ResidualBlock(dims[i], dims[i+1], dropout=0.1 if i < len(dims)-2 else 0.0))
        
        self.features = nn.Sequential(*layers)
        self.final_norm = nn.BatchNorm1d(dims[-1])
        self.classifier = nn.Linear(dims[-1], num_classes)
        
        # Initialize weights
        self._initialize_weights()
        
        # Verify parameter count
        total_params = sum(p.numel() for p in self.parameters() if p.requires_grad)
        if total_params > param_limit:
            raise ValueError(f"Model exceeds parameter limit: {total_params} > {param_limit}")
    
    def _initialize_weights(self):
        for m in self.modules():
            if isinstance(m, nn.Linear):
                nn.init.kaiming_normal_(m.weight, mode='fan_out', nonlinearity='relu')
                if m.bias is not None:
                    nn.init.zeros_(m.bias)
            elif isinstance(m, nn.BatchNorm1d):
                nn.init.ones_(m.weight)
                nn.init.zeros_(m.bias)
    
    def forward(self, x):
        x = self.features(x)
        x = self.final_norm(x)
        x = F.relu(x)
        x = self.classifier(x)
        return x

class Solution:
    def solve(self, train_loader, val_loader, metadata: dict = None) -> torch.nn.Module:
        # Extract metadata
        input_dim = metadata["input_dim"]
        num_classes = metadata["num_classes"]
        device = metadata.get("device", "cpu")
        param_limit = metadata.get("param_limit", 2500000)
        
        # Create model
        model = EfficientModel(
            input_dim=input_dim,
            num_classes=num_classes,
            param_limit=param_limit
        )
        
        # Check parameter count
        total_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
        print(f"Total parameters: {total_params:,} / {param_limit:,}")
        
        model = model.to(device)
        
        # Training setup
        criterion = nn.CrossEntropyLoss(label_smoothing=0.1)
        optimizer = optim.AdamW(
            model.parameters(),
            lr=0.001,
            weight_decay=0.01
        )
        
        # Learning rate scheduler
        scheduler = CosineAnnealingLR(optimizer, T_max=100, eta_min=1e-5)
        
        # Training loop
        num_epochs = 150
        best_acc = 0.0
        best_model_state = None
        patience_counter = 0
        patience = 15
        
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
                
                train_loss += loss.item()
                _, predicted = outputs.max(1)
                train_total += targets.size(0)
                train_correct += predicted.eq(targets).sum().item()
            
            # Validation phase
            model.eval()
            val_loss = 0.0
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
            
            # Calculate accuracies
            train_acc = 100. * train_correct / train_total
            val_acc = 100. * val_correct / val_total
            
            # Update scheduler
            scheduler.step()
            
            # Early stopping and model saving
            if val_acc > best_acc:
                best_acc = val_acc
                best_model_state = model.state_dict().copy()
                patience_counter = 0
            else:
                patience_counter += 1
            
            # Print progress
            if epoch % 10 == 0 or epoch == num_epochs - 1:
                print(f"Epoch {epoch+1:3d}/{num_epochs}: "
                      f"Train Loss: {train_loss/len(train_loader):.4f}, "
                      f"Train Acc: {train_acc:.2f}%, "
                      f"Val Loss: {val_loss/len(val_loader):.4f}, "
                      f"Val Acc: {val_acc:.2f}%, "
                      f"Best Val Acc: {best_acc:.2f}%")
            
            if patience_counter >= patience:
                print(f"Early stopping at epoch {epoch+1}")
                break
        
        # Load best model
        if best_model_state is not None:
            model.load_state_dict(best_model_state)
        
        print(f"Training completed. Best validation accuracy: {best_acc:.2f}%")
        
        return model