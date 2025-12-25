import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
from typing import Optional
import warnings

class ResidualBlock(nn.Module):
    """Bottleneck residual block for parameter efficiency"""
    def __init__(self, in_channels: int, out_channels: int, stride: int = 1):
        super().__init__()
        self.expansion = 4
        mid_channels = out_channels // self.expansion
        
        self.conv1 = nn.Conv1d(in_channels, mid_channels, kernel_size=1, bias=False)
        self.bn1 = nn.BatchNorm1d(mid_channels)
        self.conv2 = nn.Conv1d(mid_channels, mid_channels, kernel_size=3, 
                               stride=stride, padding=1, bias=False)
        self.bn2 = nn.BatchNorm1d(mid_channels)
        self.conv3 = nn.Conv1d(mid_channels, out_channels, kernel_size=1, bias=False)
        self.bn3 = nn.BatchNorm1d(out_channels)
        
        self.shortcut = nn.Sequential()
        if stride != 1 or in_channels != out_channels:
            self.shortcut = nn.Sequential(
                nn.Conv1d(in_channels, out_channels, kernel_size=1, 
                         stride=stride, bias=False),
                nn.BatchNorm1d(out_channels)
            )
    
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        residual = self.shortcut(x)
        out = F.relu(self.bn1(self.conv1(x)))
        out = F.relu(self.bn2(self.conv2(out)))
        out = self.bn3(self.conv3(out))
        out += residual
        out = F.relu(out)
        return out

class EfficientResNet(nn.Module):
    """Efficient ResNet-style model for 1D feature vectors"""
    def __init__(self, input_dim: int, num_classes: int):
        super().__init__()
        # Configuration optimized for ~950K parameters
        base_channels = 128
        expansion = 4
        
        # Initial projection with efficient channel size
        self.conv1 = nn.Conv1d(1, base_channels, kernel_size=7, stride=2, padding=3, bias=False)
        self.bn1 = nn.BatchNorm1d(base_channels)
        self.maxpool = nn.MaxPool1d(kernel_size=3, stride=2, padding=1)
        
        # Residual blocks with careful channel progression
        self.layer1 = self._make_layer(base_channels, base_channels, blocks=2, stride=1)
        self.layer2 = self._make_layer(base_channels, base_channels * 2, blocks=2, stride=2)
        self.layer3 = self._make_layer(base_channels * 2, base_channels * 4, blocks=2, stride=2)
        
        # Adaptive pooling to handle varying dimensions
        self.avgpool = nn.AdaptiveAvgPool1d(1)
        
        # Final classifier with dropout
        self.dropout = nn.Dropout(0.2)
        hidden_size = base_channels * 4
        self.fc1 = nn.Linear(hidden_size, hidden_size // 2)
        self.fc2 = nn.Linear(hidden_size // 2, num_classes)
        
        # Initialize weights
        self._initialize_weights()
    
    def _make_layer(self, in_channels: int, out_channels: int, blocks: int, stride: int):
        layers = []
        layers.append(ResidualBlock(in_channels, out_channels, stride))
        for _ in range(1, blocks):
            layers.append(ResidualBlock(out_channels, out_channels, stride=1))
        return nn.Sequential(*layers)
    
    def _initialize_weights(self):
        for m in self.modules():
            if isinstance(m, nn.Conv1d):
                nn.init.kaiming_normal_(m.weight, mode='fan_out', nonlinearity='relu')
            elif isinstance(m, nn.BatchNorm1d):
                nn.init.constant_(m.weight, 1)
                nn.init.constant_(m.bias, 0)
            elif isinstance(m, nn.Linear):
                nn.init.normal_(m.weight, 0, 0.01)
                nn.init.constant_(m.bias, 0)
    
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # Add channel dimension for 1D convolutions
        x = x.unsqueeze(1)  # [batch, 1, input_dim]
        x = F.relu(self.bn1(self.conv1(x)))
        x = self.maxpool(x)
        
        x = self.layer1(x)
        x = self.layer2(x)
        x = self.layer3(x)
        
        x = self.avgpool(x)
        x = torch.flatten(x, 1)
        
        x = self.dropout(x)
        x = F.relu(self.fc1(x))
        x = self.dropout(x)
        x = self.fc2(x)
        return x

class Solution:
    def solve(self, train_loader, val_loader, metadata: Optional[dict] = None) -> nn.Module:
        if metadata is None:
            metadata = {}
        
        input_dim = metadata.get("input_dim", 384)
        num_classes = metadata.get("num_classes", 128)
        param_limit = metadata.get("param_limit", 1000000)
        device = metadata.get("device", "cpu")
        device = torch.device(device)
        
        # Create model
        model = EfficientResNet(input_dim, num_classes).to(device)
        
        # Verify parameter count
        total_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
        if total_params > param_limit:
            # If over budget, scale down the model
            warnings.warn(f"Model has {total_params} parameters, exceeding {param_limit}. Scaling down.")
            model = self._create_scaled_down_model(input_dim, num_classes, param_limit).to(device)
            total_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
        
        print(f"Model parameters: {total_params}")
        
        # Training setup
        criterion = nn.CrossEntropyLoss()
        optimizer = torch.optim.AdamW(
            model.parameters(),
            lr=0.001,
            weight_decay=0.01
        )
        scheduler = torch.optim.lr_scheduler.OneCycleLR(
            optimizer,
            max_lr=0.005,
            epochs=100,
            steps_per_epoch=len(train_loader),
            pct_start=0.3
        )
        
        # Early stopping
        best_val_acc = 0.0
        patience = 10
        patience_counter = 0
        best_model_state = None
        
        # Training loop
        model.train()
        for epoch in range(100):
            # Training phase
            model.train()
            train_loss = 0.0
            correct = 0
            total = 0
            
            for batch_idx, (data, target) in enumerate(train_loader):
                data, target = data.to(device), target.to(device)
                
                optimizer.zero_grad()
                output = model(data)
                loss = criterion(output, target)
                loss.backward()
                
                # Gradient clipping
                torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
                
                optimizer.step()
                scheduler.step()
                
                train_loss += loss.item()
                _, predicted = output.max(1)
                total += target.size(0)
                correct += predicted.eq(target).sum().item()
            
            train_acc = 100. * correct / total
            train_loss = train_loss / len(train_loader)
            
            # Validation phase
            model.eval()
            val_loss = 0.0
            correct = 0
            total = 0
            
            with torch.no_grad():
                for data, target in val_loader:
                    data, target = data.to(device), target.to(device)
                    output = model(data)
                    loss = criterion(output, target)
                    
                    val_loss += loss.item()
                    _, predicted = output.max(1)
                    total += target.size(0)
                    correct += predicted.eq(target).sum().item()
            
            val_acc = 100. * correct / total
            val_loss = val_loss / len(val_loader)
            
            # Early stopping check
            if val_acc > best_val_acc:
                best_val_acc = val_acc
                best_model_state = model.state_dict().copy()
                patience_counter = 0
            else:
                patience_counter += 1
            
            if patience_counter >= patience:
                print(f"Early stopping at epoch {epoch}")
                break
            
            if (epoch + 1) % 10 == 0:
                print(f"Epoch {epoch + 1}: Train Loss: {train_loss:.4f}, "
                      f"Train Acc: {train_acc:.2f}%, Val Loss: {val_loss:.4f}, "
                      f"Val Acc: {val_acc:.2f}%")
        
        # Load best model
        if best_model_state is not None:
            model.load_state_dict(best_model_state)
        
        model.eval()
        return model
    
    def _create_scaled_down_model(self, input_dim: int, num_classes: int, param_limit: int) -> nn.Module:
        """Create a smaller model if initial model exceeds parameter limit"""
        # Try progressively smaller architectures
        for base_channels in [96, 64, 48, 32]:
            model = self._build_model_with_channels(input_dim, num_classes, base_channels)
            total_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
            if total_params <= param_limit:
                print(f"Selected model with {base_channels} base channels, {total_params} parameters")
                return model
        
        # Fallback to very simple model
        print("Using minimal model")
        return nn.Sequential(
            nn.Linear(input_dim, 256),
            nn.BatchNorm1d(256),
            nn.ReLU(inplace=True),
            nn.Dropout(0.3),
            nn.Linear(256, 128),
            nn.BatchNorm1d(128),
            nn.ReLU(inplace=True),
            nn.Dropout(0.2),
            nn.Linear(128, num_classes)
        )
    
    def _build_model_with_channels(self, input_dim: int, num_classes: int, base_channels: int) -> nn.Module:
        """Build model with specified base channels"""
        class ScaledResNet(nn.Module):
            def __init__(self, input_dim, num_classes, base_channels):
                super().__init__()
                self.conv1 = nn.Conv1d(1, base_channels, kernel_size=5, stride=2, padding=2, bias=False)
                self.bn1 = nn.BatchNorm1d(base_channels)
                self.maxpool = nn.MaxPool1d(kernel_size=3, stride=2, padding=1)
                
                self.layer1 = self._make_layer(base_channels, base_channels, blocks=2)
                self.layer2 = self._make_layer(base_channels, base_channels * 2, blocks=2, stride=2)
                
                self.avgpool = nn.AdaptiveAvgPool1d(1)
                self.dropout = nn.Dropout(0.2)
                
                hidden_size = base_channels * 2
                self.fc1 = nn.Linear(hidden_size, hidden_size // 2)
                self.fc2 = nn.Linear(hidden_size // 2, num_classes)
                
                self._initialize_weights()
            
            def _make_layer(self, in_channels, out_channels, blocks, stride=1):
                layers = []
                layers.append(ResidualBlock(in_channels, out_channels, stride))
                for _ in range(1, blocks):
                    layers.append(ResidualBlock(out_channels, out_channels, stride=1))
                return nn.Sequential(*layers)
            
            def _initialize_weights(self):
                for m in self.modules():
                    if isinstance(m, nn.Conv1d):
                        nn.init.kaiming_normal_(m.weight, mode='fan_out', nonlinearity='relu')
                    elif isinstance(m, nn.BatchNorm1d):
                        nn.init.constant_(m.weight, 1)
                        nn.init.constant_(m.bias, 0)
            
            def forward(self, x):
                x = x.unsqueeze(1)
                x = F.relu(self.bn1(self.conv1(x)))
                x = self.maxpool(x)
                x = self.layer1(x)
                x = self.layer2(x)
                x = self.avgpool(x)
                x = torch.flatten(x, 1)
                x = self.dropout(x)
                x = F.relu(self.fc1(x))
                x = self.dropout(x)
                x = self.fc2(x)
                return x
        
        return ScaledResNet(input_dim, num_classes, base_channels)
