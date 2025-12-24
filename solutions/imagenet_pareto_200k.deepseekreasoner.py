import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
from typing import Optional
import math

class ChannelAttention(nn.Module):
    def __init__(self, channels, reduction=8):
        super().__init__()
        self.avg_pool = nn.AdaptiveAvgPool1d(1)
        self.max_pool = nn.AdaptiveMaxPool1d(1)
        
        self.fc = nn.Sequential(
            nn.Linear(channels, channels // reduction, bias=False),
            nn.ReLU(),
            nn.Linear(channels // reduction, channels, bias=False)
        )
        self.sigmoid = nn.Sigmoid()
        
    def forward(self, x):
        b, c, _ = x.size()
        avg_out = self.fc(self.avg_pool(x).view(b, c))
        max_out = self.fc(self.max_pool(x).view(b, c))
        out = avg_out + max_out
        scale = self.sigmoid(out).view(b, c, 1)
        return x * scale.expand_as(x)

class EfficientBlock(nn.Module):
    def __init__(self, in_dim, out_dim, bottleneck_ratio=4, dropout=0.1):
        super().__init__()
        hidden_dim = in_dim // bottleneck_ratio
        
        self.conv1 = nn.Conv1d(in_dim, hidden_dim, 1, bias=False)
        self.bn1 = nn.BatchNorm1d(hidden_dim)
        
        self.depthwise = nn.Conv1d(hidden_dim, hidden_dim, 3, padding=1, 
                                  groups=hidden_dim, bias=False)
        self.bn2 = nn.BatchNorm1d(hidden_dim)
        
        self.conv2 = nn.Conv1d(hidden_dim, out_dim, 1, bias=False)
        self.bn3 = nn.BatchNorm1d(out_dim)
        
        self.attention = ChannelAttention(out_dim, reduction=max(2, out_dim // 8))
        self.dropout = nn.Dropout(dropout)
        
        self.shortcut = nn.Sequential()
        if in_dim != out_dim:
            self.shortcut = nn.Sequential(
                nn.Conv1d(in_dim, out_dim, 1, bias=False),
                nn.BatchNorm1d(out_dim)
            )
            
    def forward(self, x):
        residual = self.shortcut(x)
        
        out = F.relu(self.bn1(self.conv1(x)))
        out = F.relu(self.bn2(self.depthwise(out)))
        out = self.bn3(self.conv2(out))
        out = self.attention(out)
        out = self.dropout(out)
        
        out += residual
        return F.relu(out)

class ImageNetParetoModel(nn.Module):
    def __init__(self, input_dim=384, num_classes=128, param_limit=200000):
        super().__init__()
        self.input_dim = input_dim
        self.num_classes = num_classes
        
        # Reshape input to 1D sequence for conv1d
        self.initial_proj = nn.Linear(input_dim, 256)
        
        # Feature extraction with efficient blocks
        self.features = nn.Sequential(
            EfficientBlock(256, 256, bottleneck_ratio=8, dropout=0.2),
            EfficientBlock(256, 256, bottleneck_ratio=8, dropout=0.2),
            nn.AdaptiveAvgPool1d(1)
        )
        
        # Final classifier
        self.classifier = nn.Sequential(
            nn.Linear(256, 256),
            nn.BatchNorm1d(256),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(256, 128),
            nn.BatchNorm1d(128),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(128, num_classes)
        )
        
        # Initialize weights
        self._initialize_weights()
        
        # Verify parameter count
        self._verify_param_count(param_limit)
        
    def _initialize_weights(self):
        for m in self.modules():
            if isinstance(m, nn.Conv1d) or isinstance(m, nn.Linear):
                nn.init.kaiming_normal_(m.weight, mode='fan_out', nonlinearity='relu')
                if m.bias is not None:
                    nn.init.constant_(m.bias, 0)
            elif isinstance(m, nn.BatchNorm1d):
                nn.init.constant_(m.weight, 1)
                nn.init.constant_(m.bias, 0)
    
    def _verify_param_count(self, limit):
        total = sum(p.numel() for p in self.parameters() if p.requires_grad)
        if total > limit:
            raise ValueError(f"Model exceeds parameter limit: {total} > {limit}")
    
    def forward(self, x):
        # Reshape for conv1d: (batch, features, 1)
        x = self.initial_proj(x).unsqueeze(-1)
        x = self.features(x).squeeze(-1)
        x = self.classifier(x)
        return x

class Solution:
    def solve(self, train_loader, val_loader, metadata: dict = None) -> nn.Module:
        if metadata is None:
            metadata = {}
            
        device = metadata.get("device", "cpu")
        input_dim = metadata.get("input_dim", 384)
        num_classes = metadata.get("num_classes", 128)
        param_limit = metadata.get("param_limit", 200000)
        
        # Create model
        model = ImageNetParetoModel(
            input_dim=input_dim,
            num_classes=num_classes,
            param_limit=param_limit
        ).to(device)
        
        # Count parameters
        total_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
        print(f"Model parameters: {total_params:,}")
        
        # Training setup
        criterion = nn.CrossEntropyLoss(label_smoothing=0.1)
        optimizer = torch.optim.AdamW(
            model.parameters(),
            lr=0.001,
            weight_decay=0.05
        )
        
        scheduler = torch.optim.lr_scheduler.OneCycleLR(
            optimizer,
            max_lr=0.003,
            epochs=100,
            steps_per_epoch=len(train_loader),
            pct_start=0.3,
            anneal_strategy='cos'
        )
        
        # Training loop
        best_val_acc = 0.0
        best_model_state = None
        patience = 15
        patience_counter = 0
        
        for epoch in range(100):
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
            
            # Early stopping and model selection
            if val_acc > best_val_acc:
                best_val_acc = val_acc
                best_model_state = model.state_dict().copy()
                patience_counter = 0
            else:
                patience_counter += 1
            
            if patience_counter >= patience:
                print(f"Early stopping at epoch {epoch+1}")
                break
            
            if epoch % 10 == 0:
                print(f'Epoch {epoch+1:3d}: Train Acc: {train_acc:.2f}%, '
                      f'Val Acc: {val_acc:.2f}%, LR: {scheduler.get_last_lr()[0]:.6f}')
        
        # Load best model
        if best_model_state is not None:
            model.load_state_dict(best_model_state)
        
        model.eval()
        return model
