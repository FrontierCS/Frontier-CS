import torch
import torch.nn as nn
import torch.optim as optim
from torch.optim.lr_scheduler import CosineAnnealingLR, ReduceLROnPlateau
import numpy as np

class ResidualBlock(nn.Module):
    def __init__(self, in_features, out_features, dropout_rate=0.2):
        super().__init__()
        self.linear1 = nn.Linear(in_features, out_features)
        self.bn1 = nn.BatchNorm1d(out_features)
        self.linear2 = nn.Linear(out_features, out_features)
        self.bn2 = nn.BatchNorm1d(out_features)
        self.dropout = nn.Dropout(dropout_rate)
        self.activation = nn.GELU()
        
        self.shortcut = nn.Linear(in_features, out_features) if in_features != out_features else nn.Identity()
    
    def forward(self, x):
        residual = self.shortcut(x)
        out = self.linear1(x)
        out = self.bn1(out)
        out = self.activation(out)
        out = self.dropout(out)
        out = self.linear2(out)
        out = self.bn2(out)
        out = self.activation(out)
        out = out + residual
        return out

class EfficientMLP(nn.Module):
    def __init__(self, input_dim=384, num_classes=128, param_limit=5000000):
        super().__init__()
        self.param_limit = param_limit
        
        # Calculate dimensions to stay under parameter limit
        hidden_dims = self._calculate_hidden_dims(input_dim, num_classes)
        
        # Initial projection
        layers = [nn.Linear(input_dim, hidden_dims[0]), nn.BatchNorm1d(hidden_dims[0]), nn.GELU(), nn.Dropout(0.2)]
        
        # Residual blocks
        for i in range(len(hidden_dims) - 1):
            layers.append(ResidualBlock(hidden_dims[i], hidden_dims[i+1], dropout_rate=0.2))
        
        # Final layers
        layers.append(nn.Linear(hidden_dims[-1], num_classes))
        
        self.net = nn.Sequential(*layers)
        
        # Initialize weights
        self._initialize_weights()
        
        # Verify parameter count
        self._verify_parameters()
    
    def _calculate_hidden_dims(self, input_dim, num_classes):
        # Start with reasonable dimensions and adjust to fit parameter budget
        base_dim = 1024
        num_blocks = 4
        
        # Try different configurations to maximize capacity within budget
        for trial in range(5):
            hidden_dims = [base_dim // (2**i) for i in range(num_blocks)]
            
            # Estimate parameters
            params = 0
            # First layer
            params += (input_dim * hidden_dims[0] + hidden_dims[0])
            params += 2 * hidden_dims[0]  # BN
            
            # Residual blocks
            for i in range(num_blocks - 1):
                # Linear layers in block
                params += (hidden_dims[i] * hidden_dims[i] + hidden_dims[i]) * 2
                # BN layers (2 per block, 2 params each)
                params += 4 * hidden_dims[i]
                # Shortcut if dimension changes
                if hidden_dims[i] != hidden_dims[i+1]:
                    params += (hidden_dims[i] * hidden_dims[i+1] + hidden_dims[i+1])
            
            # Final layer
            params += (hidden_dims[-1] * num_classes + num_classes)
            
            if params <= self.param_limit * 0.95:  # Leave margin
                return hidden_dims
            
            # Reduce dimensions for next trial
            base_dim = int(base_dim * 0.85)
        
        # Fallback to conservative dimensions
        return [768, 512, 384, 256]
    
    def _initialize_weights(self):
        for m in self.modules():
            if isinstance(m, nn.Linear):
                nn.init.kaiming_normal_(m.weight, mode='fan_out', nonlinearity='relu')
                if m.bias is not None:
                    nn.init.constant_(m.bias, 0)
            elif isinstance(m, nn.BatchNorm1d):
                nn.init.constant_(m.weight, 1)
                nn.init.constant_(m.bias, 0)
    
    def _verify_parameters(self):
        total = sum(p.numel() for p in self.parameters() if p.requires_grad)
        if total > self.param_limit:
            raise ValueError(f"Model exceeds parameter limit: {total} > {self.param_limit}")
    
    def forward(self, x):
        return self.net(x)

class Solution:
    def solve(self, train_loader, val_loader, metadata: dict = None):
        device = torch.device(metadata.get("device", "cpu"))
        input_dim = metadata["input_dim"]
        num_classes = metadata["num_classes"]
        param_limit = metadata["param_limit"]
        
        # Create model
        model = EfficientMLP(input_dim, num_classes, param_limit).to(device)
        
        # Training setup
        criterion = nn.CrossEntropyLoss(label_smoothing=0.1)
        optimizer = optim.AdamW(model.parameters(), lr=0.001, weight_decay=1e-4)
        scheduler = CosineAnnealingLR(optimizer, T_max=100, eta_min=1e-5)
        
        # Training loop
        best_val_acc = 0
        best_model_state = None
        patience = 20
        patience_counter = 0
        
        num_epochs = 150
        
        for epoch in range(num_epochs):
            # Training phase
            model.train()
            train_loss = 0
            for batch_idx, (data, target) in enumerate(train_loader):
                data, target = data.to(device), target.to(device)
                
                optimizer.zero_grad()
                output = model(data)
                loss = criterion(output, target)
                loss.backward()
                
                # Gradient clipping
                torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
                
                optimizer.step()
                train_loss += loss.item()
            
            scheduler.step()
            
            # Validation phase
            model.eval()
            val_correct = 0
            val_total = 0
            with torch.no_grad():
                for data, target in val_loader:
                    data, target = data.to(device), target.to(device)
                    output = model(data)
                    pred = output.argmax(dim=1)
                    val_correct += (pred == target).sum().item()
                    val_total += target.size(0)
            
            val_acc = val_correct / val_total
            
            # Save best model
            if val_acc > best_val_acc:
                best_val_acc = val_acc
                best_model_state = model.state_dict().copy()
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
