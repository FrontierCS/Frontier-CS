import torch
import torch.nn as nn
import torch.optim as optim
import torch.nn.functional as F
from torch.optim.lr_scheduler import CosineAnnealingLR
import numpy as np
from collections import OrderedDict

class Solution:
    def solve(self, train_loader, val_loader, metadata: dict = None) -> torch.nn.Module:
        device = metadata.get("device", "cpu")
        input_dim = metadata["input_dim"]
        num_classes = metadata["num_classes"]
        param_limit = metadata["param_limit"]
        
        class ResidualBlock(nn.Module):
            def __init__(self, in_features, out_features, dropout=0.2, use_bn=True):
                super().__init__()
                self.linear1 = nn.Linear(in_features, out_features)
                self.bn1 = nn.BatchNorm1d(out_features) if use_bn else nn.Identity()
                self.linear2 = nn.Linear(out_features, out_features)
                self.bn2 = nn.BatchNorm1d(out_features) if use_bn else nn.Identity()
                self.dropout = nn.Dropout(dropout)
                self.shortcut = nn.Linear(in_features, out_features) if in_features != out_features else nn.Identity()
                
            def forward(self, x):
                residual = self.shortcut(x)
                out = self.linear1(x)
                out = self.bn1(out)
                out = F.gelu(out)
                out = self.dropout(out)
                out = self.linear2(out)
                out = self.bn2(out)
                out = F.gelu(out)
                out = out + residual
                return out
        
        class EfficientModel(nn.Module):
            def __init__(self, input_dim, num_classes):
                super().__init__()
                self.input_dim = input_dim
                self.num_classes = num_classes
                
                # Optimized architecture within 5M parameters
                hidden1 = 1024
                hidden2 = 1536
                hidden3 = 1024
                hidden4 = 512
                
                self.features = nn.Sequential(OrderedDict([
                    ('fc1', nn.Linear(input_dim, hidden1)),
                    ('bn1', nn.BatchNorm1d(hidden1)),
                    ('act1', nn.GELU()),
                    ('drop1', nn.Dropout(0.25)),
                    
                    ('res1', ResidualBlock(hidden1, hidden2, dropout=0.25)),
                    ('res2', ResidualBlock(hidden2, hidden2, dropout=0.25)),
                    
                    ('fc2', nn.Linear(hidden2, hidden3)),
                    ('bn2', nn.BatchNorm1d(hidden3)),
                    ('act2', nn.GELU()),
                    ('drop2', nn.Dropout(0.25)),
                    
                    ('res3', ResidualBlock(hidden3, hidden4, dropout=0.25)),
                    
                    ('fc3', nn.Linear(hidden4, hidden4)),
                    ('bn3', nn.BatchNorm1d(hidden4)),
                    ('act3', nn.GELU()),
                    ('drop3', nn.Dropout(0.25)),
                ]))
                
                self.classifier = nn.Linear(hidden4, num_classes)
                
                # Initialize weights
                self._init_weights()
                
            def _init_weights(self):
                for m in self.modules():
                    if isinstance(m, nn.Linear):
                        nn.init.kaiming_normal_(m.weight, mode='fan_out', nonlinearity='relu')
                        if m.bias is not None:
                            nn.init.constant_(m.bias, 0)
                    elif isinstance(m, nn.BatchNorm1d):
                        nn.init.constant_(m.weight, 1)
                        nn.init.constant_(m.bias, 0)
                        
            def forward(self, x):
                features = self.features(x)
                return self.classifier(features)
        
        # Verify parameter count
        model = EfficientModel(input_dim, num_classes).to(device)
        total_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
        
        # If model is too large, create a smaller one
        if total_params > param_limit:
            # Create a more compact model
            hidden1 = 896
            hidden2 = 1408
            hidden3 = 896
            hidden4 = 448
            
            class CompactModel(nn.Module):
                def __init__(self):
                    super().__init__()
                    layers = [
                        nn.Linear(input_dim, hidden1),
                        nn.BatchNorm1d(hidden1),
                        nn.GELU(),
                        nn.Dropout(0.25),
                        nn.Linear(hidden1, hidden2),
                        nn.BatchNorm1d(hidden2),
                        nn.GELU(),
                        nn.Dropout(0.25),
                        nn.Linear(hidden2, hidden3),
                        nn.BatchNorm1d(hidden3),
                        nn.GELU(),
                        nn.Dropout(0.25),
                        nn.Linear(hidden3, hidden4),
                        nn.BatchNorm1d(hidden4),
                        nn.GELU(),
                        nn.Dropout(0.25),
                        nn.Linear(hidden4, num_classes)
                    ]
                    self.net = nn.Sequential(*layers)
                    
                def forward(self, x):
                    return self.net(x)
            
            model = CompactModel().to(device)
            total_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
        
        # Training setup
        criterion = nn.CrossEntropyLoss()
        optimizer = optim.AdamW(
            model.parameters(),
            lr=0.001,
            weight_decay=0.05
        )
        scheduler = CosineAnnealingLR(optimizer, T_max=100, eta_min=1e-6)
        
        # Early stopping
        best_val_acc = 0.0
        best_model_state = None
        patience = 15
        patience_counter = 0
        
        num_epochs = 150
        
        for epoch in range(num_epochs):
            # Training phase
            model.train()
            train_loss = 0.0
            correct = 0
            total = 0
            
            for batch_idx, (inputs, targets) in enumerate(train_loader):
                inputs, targets = inputs.to(device), targets.to(device)
                
                optimizer.zero_grad()
                outputs = model(inputs)
                loss = criterion(outputs, targets)
                
                # Add label smoothing
                smooth_loss = -outputs.mean(dim=-1).mean()
                loss = loss + 0.1 * smooth_loss
                
                loss.backward()
                
                # Gradient clipping
                torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
                
                optimizer.step()
                
                train_loss += loss.item()
                _, predicted = outputs.max(1)
                total += targets.size(0)
                correct += predicted.eq(targets).sum().item()
            
            train_acc = 100. * correct / total
            train_loss = train_loss / len(train_loader)
            
            # Validation phase
            model.eval()
            val_loss = 0.0
            correct = 0
            total = 0
            
            with torch.no_grad():
                for inputs, targets in val_loader:
                    inputs, targets = inputs.to(device), targets.to(device)
                    outputs = model(inputs)
                    loss = criterion(outputs, targets)
                    
                    val_loss += loss.item()
                    _, predicted = outputs.max(1)
                    total += targets.size(0)
                    correct += predicted.eq(targets).sum().item()
            
            val_acc = 100. * correct / total
            val_loss = val_loss / len(val_loader)
            
            scheduler.step()
            
            # Early stopping check
            if val_acc > best_val_acc:
                best_val_acc = val_acc
                best_model_state = model.state_dict().copy()
                patience_counter = 0
            else:
                patience_counter += 1
            
            if patience_counter >= patience:
                break
        
        # Load best model
        if best_model_state is not None:
            model.load_state_dict(best_model_state)
        
        model.eval()
        return model
