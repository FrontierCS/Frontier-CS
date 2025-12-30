import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.optim import AdamW
from torch.optim.lr_scheduler import CosineAnnealingLR
import math

class ResidualBlock(nn.Module):
    def __init__(self, in_features, out_features, dropout=0.2):
        super().__init__()
        self.linear1 = nn.Linear(in_features, out_features)
        self.bn1 = nn.BatchNorm1d(out_features)
        self.linear2 = nn.Linear(out_features, out_features)
        self.bn2 = nn.BatchNorm1d(out_features)
        self.dropout = nn.Dropout(dropout)
        self.shortcut = nn.Linear(in_features, out_features) if in_features != out_features else nn.Identity()
        
    def forward(self, x):
        residual = self.shortcut(x)
        out = self.linear1(x)
        out = self.bn1(out)
        out = F.gelu(out)
        out = self.dropout(out)
        out = self.linear2(out)
        out = self.bn2(out)
        out = F.gelu(out)
        out = out + residual
        return out

class OptimizedModel(nn.Module):
    def __init__(self, input_dim, num_classes, param_limit=1000000):
        super().__init__()
        
        # Calculate dimensions to stay under parameter limit
        # Target: ~900K parameters for safety margin
        hidden1 = 768
        hidden2 = 512
        hidden3 = 384
        hidden4 = 256
        
        # Verify parameter count
        def count_params():
            total = 0
            total += input_dim * hidden1 + hidden1  # layer1
            total += hidden1 * hidden2 + hidden2  # layer2
            total += hidden2 * hidden3 + hidden3  # layer3
            total += hidden3 * hidden4 + hidden4  # layer4
            total += hidden4 * num_classes + num_classes  # output
            total += hidden1 * hidden1 + hidden1  # residual shortcut (if needed)
            return total
        
        # Adjust dimensions if needed
        while count_params() > 950000:
            hidden1 = int(hidden1 * 0.95)
            hidden2 = int(hidden2 * 0.95)
            hidden3 = int(hidden3 * 0.95)
            hidden4 = int(hidden4 * 0.95)
        
        self.layer1 = ResidualBlock(input_dim, hidden1)
        self.layer2 = ResidualBlock(hidden1, hidden2)
        self.layer3 = ResidualBlock(hidden2, hidden3)
        self.layer4 = ResidualBlock(hidden3, hidden4)
        
        self.bn_final = nn.BatchNorm1d(hidden4)
        self.dropout = nn.Dropout(0.3)
        self.output = nn.Linear(hidden4, num_classes)
        
        # Initialize weights properly
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
        x = self.layer1(x)
        x = self.layer2(x)
        x = self.layer3(x)
        x = self.layer4(x)
        x = self.bn_final(x)
        x = self.dropout(x)
        x = self.output(x)
        return x

class Solution:
    def solve(self, train_loader, val_loader, metadata: dict = None):
        device = torch.device(metadata.get("device", "cpu"))
        input_dim = metadata["input_dim"]
        num_classes = metadata["num_classes"]
        param_limit = metadata["param_limit"]
        
        # Create model
        model = OptimizedModel(input_dim, num_classes, param_limit).to(device)
        
        # Verify parameter count
        total_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
        assert total_params <= param_limit, f"Model has {total_params} parameters, exceeding limit {param_limit}"
        
        # Training setup
        optimizer = AdamW(model.parameters(), lr=0.001, weight_decay=0.05)
        scheduler = CosineAnnealingLR(optimizer, T_max=50, eta_min=1e-6)
        criterion = nn.CrossEntropyLoss()
        
        # Training loop with validation
        best_acc = 0
        best_state = None
        patience = 10
        patience_counter = 0
        
        for epoch in range(100):
            # Training phase
            model.train()
            total_loss = 0
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
                
                total_loss += loss.item()
                _, predicted = output.max(1)
                total += target.size(0)
                correct += predicted.eq(target).sum().item()
            
            train_acc = 100. * correct / total
            
            # Validation phase
            model.eval()
            val_correct = 0
            val_total = 0
            with torch.no_grad():
                for data, target in val_loader:
                    data, target = data.to(device), target.to(device)
                    output = model(data)
                    _, predicted = output.max(1)
                    val_total += target.size(0)
                    val_correct += predicted.eq(target).sum().item()
            
            val_acc = 100. * val_correct / val_total
            
            # Learning rate scheduling
            scheduler.step()
            
            # Early stopping with patience
            if val_acc > best_acc:
                best_acc = val_acc
                best_state = model.state_dict().copy()
                patience_counter = 0
            else:
                patience_counter += 1
            
            if patience_counter >= patience:
                break
        
        # Load best model
        if best_state is not None:
            model.load_state_dict(best_state)
        
        return model