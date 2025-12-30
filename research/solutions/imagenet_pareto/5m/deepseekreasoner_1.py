import torch
import torch.nn as nn
import torch.optim as optim
from torch.optim.lr_scheduler import CosineAnnealingLR, ReduceLROnPlateau
import math
import time

class ResidualBlock(nn.Module):
    def __init__(self, in_features, out_features, dropout_rate=0.2):
        super().__init__()
        self.norm1 = nn.BatchNorm1d(in_features)
        self.linear1 = nn.Linear(in_features, out_features)
        self.norm2 = nn.BatchNorm1d(out_features)
        self.linear2 = nn.Linear(out_features, out_features)
        self.activation = nn.GELU()
        self.dropout = nn.Dropout(dropout_rate)
        
        self.shortcut = nn.Identity() if in_features == out_features else nn.Linear(in_features, out_features)
        
    def forward(self, x):
        identity = self.shortcut(x)
        
        out = self.norm1(x)
        out = self.linear1(out)
        out = self.activation(out)
        out = self.dropout(out)
        
        out = self.norm2(out)
        out = self.linear2(out)
        out = self.activation(out)
        out = self.dropout(out)
        
        return out + identity

class EfficientMLP(nn.Module):
    def __init__(self, input_dim, num_classes, width_mult=1.0, depth_mult=1.0):
        super().__init__()
        
        # Calculate dimensions based on multipliers while staying under 5M params
        base_width = 768
        base_depth = 6
        
        hidden_dim = int(base_width * width_mult)
        num_blocks = int(base_depth * depth_mult)
        
        # Adjust to ensure we stay under parameter limit
        if hidden_dim * num_blocks > 4600:  # Empirical adjustment
            hidden_dim = 768
            num_blocks = 6
        
        # Initial projection
        self.input_proj = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.BatchNorm1d(hidden_dim),
            nn.GELU(),
            nn.Dropout(0.1)
        )
        
        # Residual blocks
        self.blocks = nn.ModuleList([
            ResidualBlock(hidden_dim, hidden_dim, dropout_rate=0.2) 
            for _ in range(num_blocks)
        ])
        
        # Final layers
        self.norm = nn.BatchNorm1d(hidden_dim)
        self.output = nn.Linear(hidden_dim, num_classes)
        
        # Initialize weights
        self._init_weights()
    
    def _init_weights(self):
        for m in self.modules():
            if isinstance(m, nn.Linear):
                nn.init.kaiming_normal_(m.weight, mode='fan_out', nonlinearity='relu')
                if m.bias is not None:
                    nn.init.zeros_(m.bias)
            elif isinstance(m, nn.BatchNorm1d):
                nn.init.ones_(m.weight)
                nn.init.zeros_(m.bias)
    
    def forward(self, x):
        x = self.input_proj(x)
        
        for block in self.blocks:
            x = block(x)
        
        x = self.norm(x)
        return self.output(x)

class Solution:
    def solve(self, train_loader, val_loader, metadata: dict = None) -> torch.nn.Module:
        device = metadata.get("device", "cpu")
        num_classes = metadata["num_classes"]
        input_dim = metadata["input_dim"]
        param_limit = metadata["param_limit"]
        
        # Hyperparameter search space within param limit
        configs = [
            (0.85, 1.2),  # narrower, deeper
            (1.0, 1.0),   # balanced
            (1.2, 0.85),  # wider, shallower
        ]
        
        best_model = None
        best_val_acc = 0
        
        for width_mult, depth_mult in configs:
            # Create and verify model fits parameter constraint
            model = EfficientMLP(input_dim, num_classes, width_mult, depth_mult).to(device)
            total_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
            
            if total_params > param_limit:
                continue
            
            # Train this configuration
            print(f"Training config: width_mult={width_mult:.2f}, depth_mult={depth_mult:.2f}, params={total_params:,}")
            
            val_acc = self._train_model(model, train_loader, val_loader, device)
            
            if val_acc > best_val_acc:
                best_val_acc = val_acc
                best_model = model
            
            if val_acc > 0.95:  # Good enough accuracy
                break
        
        # If no model was trained (all exceeded param limit), use conservative one
        if best_model is None:
            best_model = EfficientMLP(input_dim, num_classes, 0.8, 0.8).to(device)
            self._train_model(best_model, train_loader, val_loader, device)
        
        return best_model
    
    def _train_model(self, model, train_loader, val_loader, device):
        # Optimizer with weight decay
        optimizer = optim.AdamW(
            model.parameters(),
            lr=0.001,
            weight_decay=0.05,
            betas=(0.9, 0.999)
        )
        
        # Learning rate scheduler
        scheduler = CosineAnnealingLR(
            optimizer,
            T_max=100,  # Total epochs for cosine annealing
            eta_min=1e-6
        )
        
        # Mixed scheduler strategy
        plateau_scheduler = ReduceLROnPlateau(
            optimizer,
            mode='max',
            factor=0.5,
            patience=5,
            verbose=False
        )
        
        criterion = nn.CrossEntropyLoss(label_smoothing=0.1)
        
        # Training parameters
        epochs = 150
        best_val_acc = 0
        patience_counter = 0
        patience = 15
        
        for epoch in range(epochs):
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
            
            # Learning rate scheduling
            if epoch < 50:
                scheduler.step()
            else:
                plateau_scheduler.step(val_acc)
            
            # Early stopping check
            if val_acc > best_val_acc:
                best_val_acc = val_acc
                patience_counter = 0
            else:
                patience_counter += 1
            
            if patience_counter >= patience and epoch > 50:
                break
            
            if epoch % 20 == 0:
                print(f"Epoch {epoch}: Train Loss: {train_loss/len(train_loader):.4f}, "
                      f"Train Acc: {train_acc:.2f}%, Val Acc: {val_acc:.2f}%")
        
        return best_val_acc / 100.0