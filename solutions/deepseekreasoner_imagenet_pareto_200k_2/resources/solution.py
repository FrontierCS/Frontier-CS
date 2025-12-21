import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.optim import AdamW
from torch.optim.lr_scheduler import CosineAnnealingLR
import copy

class EfficientMLP(nn.Module):
    def __init__(self, input_dim, num_classes, max_params=200000):
        super().__init__()
        
        # Design architecture to maximize capacity within 200K params
        # Using bottleneck structure with residual connections
        hidden1 = 384  # Keep same as input for first layer
        hidden2 = 256  # Bottleneck
        hidden3 = 192  # Further compression
        hidden4 = 256  # Expand back
        hidden5 = 320  # Final hidden layer
        
        # Calculate if we need to adjust dimensions
        total = 0
        total += input_dim * hidden1 + hidden1  # Layer 1
        total += hidden1 * hidden2 + hidden2    # Layer 2
        total += hidden2 * hidden3 + hidden3    # Layer 3
        total += hidden3 * hidden4 + hidden4    # Layer 4
        total += hidden4 * hidden5 + hidden5    # Layer 5
        total += hidden5 * num_classes + num_classes  # Output layer
        
        # Add batch norm parameters (2 per layer)
        total += 2 * (hidden1 + hidden2 + hidden3 + hidden4 + hidden5)
        
        # If exceeding limit, scale down
        if total > max_params:
            scale = (max_params / total) ** 0.5
            hidden1 = int(hidden1 * scale)
            hidden2 = int(hidden2 * scale)
            hidden3 = int(hidden3 * scale)
            hidden4 = int(hidden4 * scale)
            hidden5 = int(hidden5 * scale)
        
        # Residual block structure
        self.layer1 = nn.Sequential(
            nn.Linear(input_dim, hidden1),
            nn.BatchNorm1d(hidden1),
            nn.ReLU(inplace=True),
            nn.Dropout(0.2)
        )
        
        self.layer2 = nn.Sequential(
            nn.Linear(hidden1, hidden2),
            nn.BatchNorm1d(hidden2),
            nn.ReLU(inplace=True),
            nn.Dropout(0.2)
        )
        
        self.res1 = nn.Linear(hidden1, hidden2) if hidden1 != hidden2 else nn.Identity()
        
        self.layer3 = nn.Sequential(
            nn.Linear(hidden2, hidden3),
            nn.BatchNorm1d(hidden3),
            nn.ReLU(inplace=True),
            nn.Dropout(0.1)
        )
        
        self.layer4 = nn.Sequential(
            nn.Linear(hidden3, hidden4),
            nn.BatchNorm1d(hidden4),
            nn.ReLU(inplace=True),
            nn.Dropout(0.1)
        )
        
        self.res2 = nn.Linear(hidden3, hidden4) if hidden3 != hidden4 else nn.Identity()
        
        self.layer5 = nn.Sequential(
            nn.Linear(hidden4, hidden5),
            nn.BatchNorm1d(hidden5),
            nn.ReLU(inplace=True),
            nn.Dropout(0.1)
        )
        
        self.output = nn.Linear(hidden5, num_classes)
        
        # Initialize weights
        self._init_weights()
        
        # Verify parameter count
        self.param_count = sum(p.numel() for p in self.parameters() if p.requires_grad)
    
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
        x1 = self.layer1(x)
        x2 = self.layer2(x1)
        x2 = x2 + self.res1(x1)  # Residual connection
        
        x3 = self.layer3(x2)
        x4 = self.layer4(x3)
        x4 = x4 + self.res2(x3)  # Residual connection
        
        x5 = self.layer5(x4)
        return self.output(x5)

class Solution:
    def solve(self, train_loader, val_loader, metadata: dict = None) -> torch.nn.Module:
        device = torch.device(metadata.get("device", "cpu"))
        num_classes = metadata["num_classes"]
        input_dim = metadata["input_dim"]
        param_limit = metadata["param_limit"]
        
        # Create model with parameter constraint
        model = EfficientMLP(input_dim, num_classes, max_params=param_limit)
        
        # Verify parameter count
        param_count = sum(p.numel() for p in model.parameters() if p.requires_grad)
        if param_count > param_limit:
            # Emergency reduction
            for layer in [model.layer5, model.layer4]:
                if hasattr(layer[0], 'out_features'):
                    layer[0].out_features = max(64, layer[0].out_features // 2)
        
        model = model.to(device)
        
        # Training hyperparameters
        criterion = nn.CrossEntropyLoss()
        optimizer = AdamW(model.parameters(), lr=0.001, weight_decay=0.01)
        scheduler = CosineAnnealingLR(optimizer, T_max=100, eta_min=1e-5)
        
        # Early stopping
        best_val_acc = 0
        best_model = None
        patience = 15
        patience_counter = 0
        
        # Training loop
        epochs = 150
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
                best_model = copy.deepcopy(model)
                patience_counter = 0
            else:
                patience_counter += 1
            
            if patience_counter >= patience:
                break
        
        # Return best model
        if best_model is not None:
            return best_model
        return model
