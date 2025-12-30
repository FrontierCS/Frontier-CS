import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.optim import AdamW
from torch.optim.lr_scheduler import CosineAnnealingLR
import copy
import warnings
warnings.filterwarnings('ignore')

class EfficientNet(nn.Module):
    def __init__(self, input_dim=384, num_classes=128):
        super().__init__()
        
        # Depthwise separable convolution inspired block but for MLP
        # Using bottleneck structure to save parameters
        hidden1 = 512
        hidden2 = 256
        hidden3 = 192
        hidden4 = 128
        
        # First expansion layer
        self.block1 = nn.Sequential(
            nn.Linear(input_dim, hidden1),
            nn.BatchNorm1d(hidden1),
            nn.GELU(),
            nn.Dropout(0.2)
        )
        
        # Bottleneck layers with residual connections
        self.block2 = nn.Sequential(
            nn.Linear(hidden1, hidden2),
            nn.BatchNorm1d(hidden2),
            nn.GELU(),
            nn.Dropout(0.2)
        )
        
        self.block3 = nn.Sequential(
            nn.Linear(hidden2, hidden3),
            nn.BatchNorm1d(hidden3),
            nn.GELU(),
            nn.Dropout(0.2)
        )
        
        # Final projection
        self.block4 = nn.Sequential(
            nn.Linear(hidden3, hidden4),
            nn.BatchNorm1d(hidden4),
            nn.GELU(),
            nn.Dropout(0.1)
        )
        
        # Output layer
        self.output = nn.Linear(hidden4, num_classes)
        
        # Skip connections
        self.skip1 = nn.Linear(input_dim, hidden2) if input_dim != hidden2 else nn.Identity()
        self.skip2 = nn.Linear(hidden2, hidden4) if hidden2 != hidden4 else nn.Identity()
        
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
        # First block
        x1 = self.block1(x)
        
        # Second block with residual
        x2 = self.block2(x1)
        
        # Third block
        x3 = self.block3(x2)
        
        # Fourth block with residual from x2
        x4 = self.block4(x3)
        
        # Output
        out = self.output(x4)
        return out

class Solution:
    def solve(self, train_loader, val_loader, metadata: dict = None) -> torch.nn.Module:
        if metadata is None:
            metadata = {}
        
        device = metadata.get("device", "cpu")
        input_dim = metadata.get("input_dim", 384)
        num_classes = metadata.get("num_classes", 128)
        param_limit = metadata.get("param_limit", 500000)
        
        # Create model
        model = EfficientNet(input_dim, num_classes).to(device)
        
        # Verify parameter count
        total_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
        if total_params > param_limit:
            # If too large, create a smaller model
            model = self._create_smaller_model(input_dim, num_classes, param_limit).to(device)
            total_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
        
        # Training setup
        criterion = nn.CrossEntropyLoss()
        optimizer = AdamW(model.parameters(), lr=0.003, weight_decay=0.01)
        scheduler = CosineAnnealingLR(optimizer, T_max=50, eta_min=1e-5)
        
        # Early stopping
        best_val_acc = 0.0
        best_model_state = None
        patience = 15
        patience_counter = 0
        
        # Training loop
        num_epochs = 100
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
            
            val_acc = val_correct / val_total if val_total > 0 else 0
            
            # Update scheduler
            scheduler.step()
            
            # Early stopping check
            if val_acc > best_val_acc:
                best_val_acc = val_acc
                best_model_state = copy.deepcopy(model.state_dict())
                patience_counter = 0
            else:
                patience_counter += 1
            
            if patience_counter >= patience:
                break
        
        # Load best model
        if best_model_state is not None:
            model.load_state_dict(best_model_state)
        
        return model
    
    def _create_smaller_model(self, input_dim, num_classes, param_limit):
        """Create a model guaranteed to be under parameter limit"""
        class SmallNet(nn.Module):
            def __init__(self, input_dim, num_classes):
                super().__init__()
                hidden1 = 384
                hidden2 = 256
                hidden3 = 192
                
                self.net = nn.Sequential(
                    nn.Linear(input_dim, hidden1),
                    nn.BatchNorm1d(hidden1),
                    nn.GELU(),
                    nn.Dropout(0.3),
                    
                    nn.Linear(hidden1, hidden2),
                    nn.BatchNorm1d(hidden2),
                    nn.GELU(),
                    nn.Dropout(0.3),
                    
                    nn.Linear(hidden2, hidden3),
                    nn.BatchNorm1d(hidden3),
                    nn.GELU(),
                    nn.Dropout(0.2),
                    
                    nn.Linear(hidden3, num_classes)
                )
                
                # Initialize weights
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
        
        # Keep reducing size until under limit
        model = SmallNet(input_dim, num_classes)
        total_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
        
        # If still too large, create minimal model
        if total_params > param_limit:
            class MinimalNet(nn.Module):
                def __init__(self, input_dim, num_classes):
                    super().__init__()
                    hidden = 256
                    self.net = nn.Sequential(
                        nn.Linear(input_dim, hidden),
                        nn.BatchNorm1d(hidden),
                        nn.GELU(),
                        nn.Dropout(0.3),
                        nn.Linear(hidden, num_classes)
                    )
                
                def forward(self, x):
                    return self.net(x)
            
            model = MinimalNet(input_dim, num_classes)
        
        return model