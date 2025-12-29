import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim
from torch.optim.lr_scheduler import CosineAnnealingLR, ReduceLROnPlateau
import math
from typing import Optional

def count_parameters(model):
    return sum(p.numel() for p in model.parameters() if p.requires_grad)

class ResidualBlock(nn.Module):
    def __init__(self, in_dim, out_dim, dropout=0.2):
        super().__init__()
        self.norm1 = nn.BatchNorm1d(in_dim)
        self.linear1 = nn.Linear(in_dim, out_dim)
        self.norm2 = nn.BatchNorm1d(out_dim)
        self.linear2 = nn.Linear(out_dim, out_dim)
        self.dropout = nn.Dropout(dropout)
        
        self.shortcut = nn.Linear(in_dim, out_dim) if in_dim != out_dim else nn.Identity()
        
    def forward(self, x):
        identity = self.shortcut(x)
        
        out = self.norm1(x)
        out = F.relu(out)
        out = self.linear1(out)
        
        out = self.norm2(out)
        out = F.relu(out)
        out = self.dropout(out)
        out = self.linear2(out)
        
        return out + identity

class EfficientClassifier(nn.Module):
    def __init__(self, input_dim=384, num_classes=128, param_limit=200000):
        super().__init__()
        
        # Carefully designed architecture to maximize capacity within 200K params
        hidden1 = 256
        hidden2 = 192
        hidden3 = 160
        
        # Initial projection
        self.initial = nn.Sequential(
            nn.Linear(input_dim, hidden1),
            nn.BatchNorm1d(hidden1),
            nn.ReLU(inplace=True),
            nn.Dropout(0.3)
        )
        
        # Residual blocks with bottleneck design
        self.block1 = ResidualBlock(hidden1, hidden2, dropout=0.25)
        self.block2 = ResidualBlock(hidden2, hidden3, dropout=0.2)
        
        # Final layers
        self.final_norm = nn.BatchNorm1d(hidden3)
        self.classifier = nn.Linear(hidden3, num_classes)
        
        # Initialize weights
        self._initialize_weights()
        
        # Verify parameter count
        param_count = count_parameters(self)
        if param_count > param_limit:
            raise ValueError(f"Model exceeds parameter limit: {param_count} > {param_limit}")
        
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
        x = self.initial(x)
        x = self.block1(x)
        x = self.block2(x)
        x = self.final_norm(x)
        x = F.relu(x)
        x = self.classifier(x)
        return x

class Solution:
    def solve(self, train_loader, val_loader, metadata: dict = None) -> torch.nn.Module:
        device = torch.device(metadata.get("device", "cpu"))
        input_dim = metadata["input_dim"]
        num_classes = metadata["num_classes"]
        param_limit = metadata["param_limit"]
        
        # Create model with parameter constraint
        model = EfficientClassifier(
            input_dim=input_dim,
            num_classes=num_classes,
            param_limit=param_limit
        ).to(device)
        
        # Verify parameter count
        param_count = count_parameters(model)
        if param_count > param_limit:
            raise RuntimeError(f"Model violates parameter constraint: {param_count} > {param_limit}")
        
        # Training configuration
        criterion = nn.CrossEntropyLoss(label_smoothing=0.1)
        optimizer = optim.AdamW(
            model.parameters(),
            lr=0.001,
            weight_decay=0.01,
            betas=(0.9, 0.999)
        )
        
        # Dynamic schedulers
        scheduler_cosine = CosineAnnealingLR(optimizer, T_max=50, eta_min=1e-5)
        scheduler_plateau = ReduceLROnPlateau(optimizer, mode='max', patience=5, factor=0.5, min_lr=1e-6)
        
        # Early stopping
        best_val_acc = 0.0
        best_model_state = None
        patience_counter = 0
        max_patience = 15
        
        # Training loop
        num_epochs = 150
        
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
            
            val_acc = 100. * val_correct / val_total
            
            # Update schedulers
            scheduler_cosine.step()
            scheduler_plateau.step(val_acc)
            
            # Early stopping and model selection
            if val_acc > best_val_acc:
                best_val_acc = val_acc
                best_model_state = {k: v.cpu().clone() for k, v in model.state_dict().items()}
                patience_counter = 0
            else:
                patience_counter += 1
            
            # Check early stopping
            if patience_counter >= max_patience:
                break
        
        # Load best model
        if best_model_state is not None:
            model.load_state_dict(best_model_state)
        model.to(device)
        
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
        
        # Ensure we're still within parameter limit
        final_param_count = count_parameters(model)
        if final_param_count > param_limit:
            raise RuntimeError(f"Final model violates parameter constraint: {final_param_count} > {param_limit}")
        
        return model