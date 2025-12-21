import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim
from torch.optim.lr_scheduler import CosineAnnealingLR, ReduceLROnPlateau
import math
import warnings
import time

class ResidualBlock(nn.Module):
    def __init__(self, in_dim, out_dim, dropout_rate=0.3, use_batchnorm=True):
        super().__init__()
        self.linear1 = nn.Linear(in_dim, out_dim)
        self.linear2 = nn.Linear(out_dim, out_dim)
        self.shortcut = nn.Linear(in_dim, out_dim) if in_dim != out_dim else nn.Identity()
        self.bn1 = nn.BatchNorm1d(out_dim) if use_batchnorm else nn.Identity()
        self.bn2 = nn.BatchNorm1d(out_dim) if use_batchnorm else nn.Identity()
        self.dropout = nn.Dropout(dropout_rate)
        
    def forward(self, x):
        residual = self.shortcut(x)
        out = self.linear1(x)
        out = self.bn1(out)
        out = F.relu(out)
        out = self.dropout(out)
        
        out = self.linear2(out)
        out = self.bn2(out)
        out = F.relu(out + residual)
        return out

class EfficientNet(nn.Module):
    def __init__(self, input_dim, num_classes, param_limit=5000000):
        super().__init__()
        self.param_limit = param_limit
        
        # Calculate dimensions based on parameter budget
        # Start with a base width and adjust depth
        base_width = 1536
        depth = 4  # We'll adjust this
        
        # Reduce width if needed to stay under limit
        while True:
            layers = []
            current_dim = input_dim
            
            # Initial projection
            layers.append(nn.Linear(input_dim, base_width))
            layers.append(nn.BatchNorm1d(base_width))
            layers.append(nn.ReLU())
            layers.append(nn.Dropout(0.3))
            
            # Residual blocks
            for i in range(depth):
                layers.append(ResidualBlock(base_width, base_width, dropout_rate=0.3))
            
            # Final layers
            layers.append(nn.Linear(base_width, base_width // 2))
            layers.append(nn.BatchNorm1d(base_width // 2))
            layers.append(nn.ReLU())
            layers.append(nn.Dropout(0.3))
            
            layers.append(nn.Linear(base_width // 2, num_classes))
            
            test_model = nn.Sequential(*layers)
            param_count = sum(p.numel() for p in test_model.parameters() if p.requires_grad)
            
            if param_count <= param_limit:
                break
            elif base_width > 512:
                base_width -= 128
            elif depth > 2:
                depth -= 1
            else:
                base_width = 512
                depth = 2
                break
        
        # Build final model
        self.layers = nn.ModuleList([
            nn.Linear(input_dim, base_width),
            nn.BatchNorm1d(base_width),
            nn.ReLU(),
            nn.Dropout(0.3)
        ])
        
        for i in range(depth):
            self.layers.append(ResidualBlock(base_width, base_width, dropout_rate=0.3))
        
        self.layers.append(nn.Linear(base_width, base_width // 2))
        self.layers.append(nn.BatchNorm1d(base_width // 2))
        self.layers.append(nn.ReLU())
        self.layers.append(nn.Dropout(0.3))
        self.layers.append(nn.Linear(base_width // 2, num_classes))
        
        # Verify parameter count
        total_params = sum(p.numel() for p in self.parameters() if p.requires_grad)
        if total_params > param_limit:
            warnings.warn(f"Model has {total_params} parameters, exceeding limit of {param_limit}")
    
    def forward(self, x):
        for layer in self.layers:
            x = layer(x)
        return x

class Solution:
    def solve(self, train_loader, val_loader, metadata: dict = None):
        if metadata is None:
            metadata = {}
        
        device = torch.device(metadata.get("device", "cpu"))
        input_dim = metadata.get("input_dim", 384)
        num_classes = metadata.get("num_classes", 128)
        param_limit = metadata.get("param_limit", 5000000)
        
        # Create model
        model = EfficientNet(input_dim, num_classes, param_limit).to(device)
        
        # Verify parameter constraint
        total_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
        if total_params > param_limit:
            # Drastic reduction if still over limit
            model = nn.Sequential(
                nn.Linear(input_dim, 1024),
                nn.BatchNorm1d(1024),
                nn.ReLU(),
                nn.Dropout(0.3),
                nn.Linear(1024, 1024),
                nn.BatchNorm1d(1024),
                nn.ReLU(),
                nn.Dropout(0.3),
                nn.Linear(1024, 512),
                nn.BatchNorm1d(512),
                nn.ReLU(),
                nn.Dropout(0.3),
                nn.Linear(512, num_classes)
            ).to(device)
        
        # Optimizer and scheduler
        optimizer = optim.AdamW(
            model.parameters(),
            lr=0.001,
            weight_decay=1e-4,
            betas=(0.9, 0.999)
        )
        
        scheduler = CosineAnnealingLR(
            optimizer,
            T_max=50,
            eta_min=1e-6
        )
        
        # Loss function with label smoothing
        criterion = nn.CrossEntropyLoss(label_smoothing=0.1)
        
        # Training loop
        num_epochs = 100
        best_val_acc = 0.0
        best_model_state = None
        patience = 15
        patience_counter = 0
        
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
            
            # Learning rate scheduling
            scheduler.step()
            
            # Early stopping and model checkpoint
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
        
        return model
