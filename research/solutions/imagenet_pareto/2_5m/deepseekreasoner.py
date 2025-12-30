import torch
import torch.nn as nn
import torch.optim as optim
from torch.optim.lr_scheduler import CosineAnnealingLR
import time
import math

class MLPBlock(nn.Module):
    def __init__(self, in_features, out_features, dropout_rate=0.2, use_bn=True):
        super().__init__()
        self.linear = nn.Linear(in_features, out_features)
        self.bn = nn.BatchNorm1d(out_features) if use_bn else nn.Identity()
        self.act = nn.GELU()
        self.dropout = nn.Dropout(dropout_rate)
        
    def forward(self, x):
        x = self.linear(x)
        x = self.bn(x)
        x = self.act(x)
        x = self.dropout(x)
        return x

class EfficientMLP(nn.Module):
    def __init__(self, input_dim=384, num_classes=128, param_limit=2500000):
        super().__init__()
        self.input_dim = input_dim
        self.num_classes = num_classes
        
        # Design architecture to stay under 2.5M parameters
        # Using expanding then contracting structure
        hidden1 = 1536  # 4x expansion
        hidden2 = 1152  # 3x
        hidden3 = 768   # 2x
        hidden4 = 512
        
        self.block1 = MLPBlock(input_dim, hidden1, dropout_rate=0.3)
        self.block2 = MLPBlock(hidden1, hidden2, dropout_rate=0.3)
        self.block3 = MLPBlock(hidden2, hidden3, dropout_rate=0.25)
        self.block4 = MLPBlock(hidden3, hidden4, dropout_rate=0.2)
        
        # Skip connections for better gradient flow
        self.skip1 = nn.Linear(input_dim, hidden2) if input_dim != hidden2 else nn.Identity()
        self.skip2 = nn.Linear(hidden1, hidden3) if hidden1 != hidden3 else nn.Identity()
        self.skip3 = nn.Linear(hidden2, hidden4) if hidden2 != hidden4 else nn.Identity()
        
        # Final classifier
        self.final_norm = nn.BatchNorm1d(hidden4)
        self.classifier = nn.Linear(hidden4, num_classes)
        
        # Initialize weights
        self._init_weights()
        
        # Verify parameter count
        self._verify_param_count(param_limit)
    
    def _init_weights(self):
        for m in self.modules():
            if isinstance(m, nn.Linear):
                nn.init.kaiming_normal_(m.weight, mode='fan_out', nonlinearity='relu')
                if m.bias is not None:
                    nn.init.constant_(m.bias, 0)
            elif isinstance(m, nn.BatchNorm1d):
                nn.init.constant_(m.weight, 1)
                nn.init.constant_(m.bias, 0)
    
    def _verify_param_count(self, limit):
        total = sum(p.numel() for p in self.parameters() if p.requires_grad)
        if total > limit:
            raise ValueError(f"Model has {total} parameters, exceeding limit of {limit}")
    
    def forward(self, x):
        identity1 = x
        
        x1 = self.block1(x)
        
        # First residual with projection
        x2 = self.block2(x1)
        if isinstance(self.skip1, nn.Linear):
            identity1 = self.skip1(identity1)
        x2 = x2 + identity1
        
        # Second residual
        x3 = self.block3(x2)
        if isinstance(self.skip2, nn.Linear):
            x1_proj = self.skip2(x1)
            x3 = x3 + x1_proj
        
        # Third residual
        x4 = self.block4(x3)
        if isinstance(self.skip3, nn.Linear):
            x2_proj = self.skip3(x2)
            x4 = x4 + x2_proj
        
        x4 = self.final_norm(x4)
        return self.classifier(x4)

class Solution:
    def solve(self, train_loader, val_loader, metadata: dict = None) -> torch.nn.Module:
        device = torch.device(metadata.get("device", "cpu"))
        input_dim = metadata["input_dim"]
        num_classes = metadata["num_classes"]
        param_limit = metadata["param_limit"]
        
        # Create model
        model = EfficientMLP(
            input_dim=input_dim,
            num_classes=num_classes,
            param_limit=param_limit
        ).to(device)
        
        # Training setup
        criterion = nn.CrossEntropyLoss(label_smoothing=0.1)
        
        # Use AdamW with weight decay
        optimizer = optim.AdamW(
            model.parameters(),
            lr=0.0015,
            weight_decay=0.05,
            betas=(0.9, 0.999)
        )
        
        # Cosine annealing scheduler
        scheduler = CosineAnnealingLR(
            optimizer,
            T_max=100,  # Will be adjusted by warmup
            eta_min=1e-6
        )
        
        # Warmup scheduler
        warmup_epochs = 10
        warmup_scheduler = optim.lr_scheduler.LinearLR(
            optimizer,
            start_factor=0.01,
            end_factor=1.0,
            total_iters=warmup_epochs
        )
        
        # Combined scheduler
        from torch.optim.lr_scheduler import SequentialLR
        scheduler = SequentialLR(
            optimizer,
            schedulers=[warmup_scheduler, scheduler],
            milestones=[warmup_epochs]
        )
        
        # Training parameters
        epochs = 150
        best_val_acc = 0.0
        best_model_state = None
        patience = 20
        patience_counter = 0
        
        # Training loop
        for epoch in range(epochs):
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
            
            train_acc = 100. * train_correct / train_total
            val_acc = 100. * val_correct / val_total
            
            # Update scheduler
            scheduler.step()
            
            # Early stopping and model saving
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