import torch
import torch.nn as nn
import torch.nn.functional as F
import math
from typing import Optional

class ResidualBlock(nn.Module):
    def __init__(self, in_dim, out_dim, downsample=False):
        super().__init__()
        self.downsample = downsample
        stride = 2 if downsample else 1
        
        # Main path
        self.conv1 = nn.Conv1d(in_dim, out_dim, kernel_size=3, stride=stride, padding=1, bias=False)
        self.bn1 = nn.BatchNorm1d(out_dim)
        self.conv2 = nn.Conv1d(out_dim, out_dim, kernel_size=3, padding=1, bias=False)
        self.bn2 = nn.BatchNorm1d(out_dim)
        
        # Shortcut path
        self.shortcut = nn.Sequential()
        if in_dim != out_dim or downsample:
            self.shortcut = nn.Sequential(
                nn.Conv1d(in_dim, out_dim, kernel_size=1, stride=stride, bias=False),
                nn.BatchNorm1d(out_dim)
            )
        
    def forward(self, x):
        out = F.relu(self.bn1(self.conv1(x)))
        out = self.bn2(self.conv2(out))
        out += self.shortcut(x)
        out = F.relu(out)
        return out

class EfficientNet(nn.Module):
    def __init__(self, input_dim=384, num_classes=128):
        super().__init__()
        self.input_dim = input_dim
        self.num_classes = num_classes
        
        # Initial convolution - treat 384D as 1D signal with 384 channels
        self.conv1 = nn.Conv1d(1, 32, kernel_size=3, padding=1, bias=False)
        self.bn1 = nn.BatchNorm1d(32)
        
        # Residual blocks with careful dimension management
        self.layer1 = self._make_layer(32, 32, 2, downsample=False)
        self.layer2 = self._make_layer(32, 64, 2, downsample=True)
        self.layer3 = self._make_layer(64, 96, 2, downsample=True)
        
        # Global pooling
        self.global_pool = nn.AdaptiveAvgPool1d(1)
        
        # Final classifier with bottleneck
        self.fc1 = nn.Linear(96, 128)
        self.bn_fc = nn.BatchNorm1d(128)
        self.dropout = nn.Dropout(0.3)
        self.fc2 = nn.Linear(128, num_classes)
        
        # Initialize weights
        self._initialize_weights()
        
    def _make_layer(self, in_channels, out_channels, blocks, downsample):
        layers = []
        layers.append(ResidualBlock(in_channels, out_channels, downsample))
        for _ in range(1, blocks):
            layers.append(ResidualBlock(out_channels, out_channels, False))
        return nn.Sequential(*layers)
    
    def _initialize_weights(self):
        for m in self.modules():
            if isinstance(m, nn.Conv1d):
                nn.init.kaiming_normal_(m.weight, mode='fan_out', nonlinearity='relu')
                if m.bias is not None:
                    nn.init.constant_(m.bias, 0)
            elif isinstance(m, nn.BatchNorm1d):
                nn.init.constant_(m.weight, 1)
                nn.init.constant_(m.bias, 0)
            elif isinstance(m, nn.Linear):
                nn.init.normal_(m.weight, 0, 0.01)
                if m.bias is not None:
                    nn.init.constant_(m.bias, 0)
    
    def forward(self, x):
        # Reshape from (batch, 384) to (batch, 1, 384) for 1D conv
        x = x.unsqueeze(1)
        
        # Initial convolution
        x = F.relu(self.bn1(self.conv1(x)))
        
        # Residual blocks
        x = self.layer1(x)
        x = self.layer2(x)
        x = self.layer3(x)
        
        # Global pooling
        x = self.global_pool(x)
        x = x.view(x.size(0), -1)
        
        # Classifier
        x = F.relu(self.bn_fc(self.fc1(x)))
        x = self.dropout(x)
        x = self.fc2(x)
        
        return x

class Solution:
    def solve(self, train_loader, val_loader, metadata: dict = None) -> torch.nn.Module:
        if metadata is None:
            metadata = {}
        
        num_classes = metadata.get("num_classes", 128)
        input_dim = metadata.get("input_dim", 384)
        device = metadata.get("device", "cpu")
        param_limit = metadata.get("param_limit", 500000)
        
        # Create model with careful parameter counting
        model = EfficientNet(input_dim, num_classes).to(device)
        
        # Verify parameter count
        param_count = sum(p.numel() for p in model.parameters() if p.requires_grad)
        if param_count > param_limit:
            # Scale down model if needed
            model = self._create_smaller_model(input_dim, num_classes).to(device)
            param_count = sum(p.numel() for p in model.parameters() if p.requires_grad)
        
        print(f"Model parameters: {param_count}")
        
        # Training setup
        criterion = nn.CrossEntropyLoss()
        optimizer = torch.optim.AdamW(model.parameters(), lr=0.001, weight_decay=1e-4)
        scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=50)
        
        # Mixed precision training setup
        scaler = torch.cuda.amp.GradScaler() if device != 'cpu' else None
        
        # Early stopping
        best_val_acc = 0.0
        patience = 10
        patience_counter = 0
        best_model_state = None
        
        # Training loop
        num_epochs = 80
        
        for epoch in range(num_epochs):
            # Training phase
            model.train()
            train_loss = 0.0
            train_correct = 0
            train_total = 0
            
            for batch_idx, (inputs, targets) in enumerate(train_loader):
                inputs, targets = inputs.to(device), targets.to(device)
                
                optimizer.zero_grad()
                
                if scaler:
                    with torch.cuda.amp.autocast():
                        outputs = model(inputs)
                        loss = criterion(outputs, targets)
                    scaler.scale(loss).backward()
                    scaler.step(optimizer)
                    scaler.update()
                else:
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
            
            # Update scheduler
            scheduler.step()
            
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
            
            # Print progress
            if (epoch + 1) % 5 == 0:
                print(f"Epoch [{epoch+1}/{num_epochs}] "
                      f"Train Loss: {train_loss/(batch_idx+1):.4f}, "
                      f"Train Acc: {train_acc:.2f}%, "
                      f"Val Acc: {val_acc:.2f}%, "
                      f"Best Val Acc: {best_val_acc:.2f}%")
        
        # Load best model
        if best_model_state is not None:
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
        print(f"Final validation accuracy: {final_val_acc:.2f}%")
        
        # Final parameter count verification
        final_param_count = sum(p.numel() for p in model.parameters() if p.requires_grad)
        if final_param_count > param_limit:
            print(f"WARNING: Model exceeds parameter limit: {final_param_count} > {param_limit}")
            # Fallback to minimal model
            model = self._create_minimal_model(input_dim, num_classes).to(device)
        
        return model
    
    def _create_smaller_model(self, input_dim, num_classes):
        """Create an even smaller model if the main one exceeds limits"""
        class TinyResNet(nn.Module):
            def __init__(self, input_dim, num_classes):
                super().__init__()
                self.conv1 = nn.Conv1d(1, 24, kernel_size=3, padding=1, bias=False)
                self.bn1 = nn.BatchNorm1d(24)
                
                # Tiny residual blocks
                self.block1 = nn.Sequential(
                    nn.Conv1d(24, 24, kernel_size=3, padding=1, bias=False),
                    nn.BatchNorm1d(24),
                    nn.ReLU(),
                    nn.Conv1d(24, 24, kernel_size=3, padding=1, bias=False),
                    nn.BatchNorm1d(24)
                )
                
                self.block2 = nn.Sequential(
                    nn.Conv1d(24, 48, kernel_size=3, stride=2, padding=1, bias=False),
                    nn.BatchNorm1d(48),
                    nn.ReLU(),
                    nn.Conv1d(48, 48, kernel_size=3, padding=1, bias=False),
                    nn.BatchNorm1d(48)
                )
                
                self.shortcut2 = nn.Sequential(
                    nn.Conv1d(24, 48, kernel_size=1, stride=2, bias=False),
                    nn.BatchNorm1d(48)
                )
                
                self.global_pool = nn.AdaptiveAvgPool1d(1)
                self.fc = nn.Linear(48, num_classes)
                
            def forward(self, x):
                x = x.unsqueeze(1)
                x = F.relu(self.bn1(self.conv1(x)))
                
                # Block 1
                residual = x
                out = self.block1(x)
                out += residual
                out = F.relu(out)
                
                # Block 2
                residual = self.shortcut2(out)
                out = self.block2(out)
                out += residual
                out = F.relu(out)
                
                out = self.global_pool(out)
                out = out.view(out.size(0), -1)
                out = self.fc(out)
                return out
        
        return TinyResNet(input_dim, num_classes)
    
    def _create_minimal_model(self, input_dim, num_classes):
        """Create a minimal model that definitely stays under parameter limit"""
        class MinimalModel(nn.Module):
            def __init__(self, input_dim, num_classes):
                super().__init__()
                hidden_dim = 192  # Carefully chosen to stay under 500K
                self.fc1 = nn.Linear(input_dim, hidden_dim)
                self.bn1 = nn.BatchNorm1d(hidden_dim)
                self.dropout1 = nn.Dropout(0.3)
                self.fc2 = nn.Linear(hidden_dim, hidden_dim // 2)
                self.bn2 = nn.BatchNorm1d(hidden_dim // 2)
                self.dropout2 = nn.Dropout(0.3)
                self.fc3 = nn.Linear(hidden_dim // 2, num_classes)
                
            def forward(self, x):
                x = F.relu(self.bn1(self.fc1(x)))
                x = self.dropout1(x)
                x = F.relu(self.bn2(self.fc2(x)))
                x = self.dropout2(x)
                x = self.fc3(x)
                return x
        
        return MinimalModel(input_dim, num_classes)