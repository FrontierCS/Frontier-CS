import torch
import torch.nn as nn
import torch.optim as optim
from torch.optim.lr_scheduler import CosineAnnealingLR
import numpy as np
import math

def count_parameters(model):
    return sum(p.numel() for p in model.parameters() if p.requires_grad)

class ResidualBlock(nn.Module):
    def __init__(self, in_features, out_features, dropout_rate=0.1):
        super().__init__()
        self.norm1 = nn.BatchNorm1d(in_features)
        self.fc1 = nn.Linear(in_features, out_features)
        self.relu = nn.ReLU(inplace=True)
        self.dropout = nn.Dropout(dropout_rate)
        self.norm2 = nn.BatchNorm1d(out_features)
        self.fc2 = nn.Linear(out_features, out_features)
        
        # Skip connection
        self.skip = nn.Linear(in_features, out_features) if in_features != out_features else nn.Identity()
        
    def forward(self, x):
        identity = self.skip(x)
        out = self.norm1(x)
        out = self.fc1(out)
        out = self.relu(out)
        out = self.dropout(out)
        out = self.norm2(out)
        out = self.fc2(out)
        out = self.relu(out + identity)
        return out

class BottleneckResidualBlock(nn.Module):
    def __init__(self, in_features, bottleneck_features, dropout_rate=0.1):
        super().__init__()
        self.norm1 = nn.BatchNorm1d(in_features)
        self.fc1 = nn.Linear(in_features, bottleneck_features)
        self.relu = nn.ReLU(inplace=True)
        self.dropout1 = nn.Dropout(dropout_rate)
        self.norm2 = nn.BatchNorm1d(bottleneck_features)
        self.fc2 = nn.Linear(bottleneck_features, in_features)
        self.dropout2 = nn.Dropout(dropout_rate)
        
    def forward(self, x):
        identity = x
        out = self.norm1(x)
        out = self.fc1(out)
        out = self.relu(out)
        out = self.dropout1(out)
        out = self.norm2(out)
        out = self.fc2(out)
        out = self.dropout2(out)
        out = self.relu(out + identity)
        return out

class SolutionModel(nn.Module):
    def __init__(self, input_dim, num_classes):
        super().__init__()
        # Stage 1: Initial projection
        base_dim = 1536
        self.input_proj = nn.Sequential(
            nn.Linear(input_dim, base_dim),
            nn.BatchNorm1d(base_dim),
            nn.ReLU(inplace=True),
            nn.Dropout(0.2)
        )
        
        # Stage 2: Residual blocks with bottleneck
        self.res_blocks = nn.Sequential(
            BottleneckResidualBlock(base_dim, 384, dropout_rate=0.1),
            BottleneckResidualBlock(base_dim, 384, dropout_rate=0.1),
            BottleneckResidualBlock(base_dim, 384, dropout_rate=0.1),
            BottleneckResidualBlock(base_dim, 384, dropout_rate=0.1),
            BottleneckResidualBlock(base_dim, 384, dropout_rate=0.1),
            BottleneckResidualBlock(base_dim, 384, dropout_rate=0.1),
        )
        
        # Stage 3: Head
        self.head = nn.Sequential(
            nn.BatchNorm1d(base_dim),
            nn.Dropout(0.3),
            nn.Linear(base_dim, 1024),
            nn.ReLU(inplace=True),
            nn.BatchNorm1d(1024),
            nn.Dropout(0.2),
            nn.Linear(1024, 512),
            nn.ReLU(inplace=True),
            nn.BatchNorm1d(512),
            nn.Dropout(0.1),
            nn.Linear(512, num_classes)
        )
        
        # Initialize weights
        self._initialize_weights()
        
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
        x = self.res_blocks(x)
        x = self.head(x)
        return x

class Solution:
    def solve(self, train_loader, val_loader, metadata: dict = None):
        device = torch.device(metadata.get("device", "cpu"))
        input_dim = metadata["input_dim"]
        num_classes = metadata["num_classes"]
        param_limit = metadata["param_limit"]
        
        # Create model
        model = SolutionModel(input_dim, num_classes).to(device)
        
        # Verify parameter count
        total_params = count_parameters(model)
        if total_params > param_limit:
            # If model exceeds limit, scale it down
            model = self._create_scaled_model(input_dim, num_classes, param_limit).to(device)
            total_params = count_parameters(model)
            
        print(f"Model parameters: {total_params:,} / {param_limit:,}")
        
        # Training setup
        criterion = nn.CrossEntropyLoss(label_smoothing=0.1)
        optimizer = optim.AdamW(
            model.parameters(),
            lr=0.001,
            weight_decay=0.05,
            betas=(0.9, 0.999)
        )
        
        scheduler = CosineAnnealingLR(
            optimizer,
            T_max=100,
            eta_min=1e-6
        )
        
        # Mixed precision training
        scaler = torch.cuda.amp.GradScaler() if device.type == 'cuda' else None
        
        # Early stopping
        best_val_acc = 0.0
        patience_counter = 0
        patience = 20
        best_model_state = None
        
        # Training loop
        num_epochs = 200
        for epoch in range(num_epochs):
            # Training phase
            model.train()
            train_loss = 0.0
            train_correct = 0
            train_total = 0
            
            for batch_idx, (inputs, targets) in enumerate(train_loader):
                inputs, targets = inputs.to(device), targets.to(device)
                
                optimizer.zero_grad()
                
                if scaler is not None:
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
            
            # Early stopping logic
            if val_acc > best_val_acc:
                best_val_acc = val_acc
                patience_counter = 0
                best_model_state = {k: v.cpu().clone() for k, v in model.state_dict().items()}
            else:
                patience_counter += 1
                
            if patience_counter >= patience:
                print(f"Early stopping at epoch {epoch}")
                break
            
            if (epoch + 1) % 20 == 0:
                print(f"Epoch [{epoch+1}/{num_epochs}], "
                      f"Train Loss: {train_loss/(batch_idx+1):.4f}, "
                      f"Train Acc: {train_acc:.2f}%, "
                      f"Val Acc: {val_acc:.2f}%")
        
        # Load best model
        if best_model_state is not None:
            model.load_state_dict(best_model_state)
        
        print(f"Final validation accuracy: {best_val_acc:.2f}%")
        
        # Final parameter count check
        final_params = count_parameters(model)
        if final_params > param_limit:
            print(f"WARNING: Model exceeds parameter limit ({final_params} > {param_limit})")
        
        return model
    
    def _create_scaled_model(self, input_dim, num_classes, param_limit):
        """Create a scaled-down model if initial design exceeds parameter limit"""
        # Conservative design that should stay under limit
        base_dim = 1024
        
        class ConservativeModel(nn.Module):
            def __init__(self):
                super().__init__()
                self.net = nn.Sequential(
                    nn.Linear(input_dim, base_dim),
                    nn.BatchNorm1d(base_dim),
                    nn.ReLU(inplace=True),
                    nn.Dropout(0.2),
                    
                    nn.Linear(base_dim, base_dim),
                    nn.BatchNorm1d(base_dim),
                    nn.ReLU(inplace=True),
                    nn.Dropout(0.2),
                    
                    nn.Linear(base_dim, base_dim),
                    nn.BatchNorm1d(base_dim),
                    nn.ReLU(inplace=True),
                    nn.Dropout(0.1),
                    
                    nn.Linear(base_dim, base_dim // 2),
                    nn.BatchNorm1d(base_dim // 2),
                    nn.ReLU(inplace=True),
                    nn.Dropout(0.1),
                    
                    nn.Linear(base_dim // 2, num_classes)
                )
                
                # Initialize weights
                self._initialize_weights()
                
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
                return self.net(x)
        
        model = ConservativeModel()
        print(f"Scaled model parameters: {count_parameters(model):,}")
        return model
