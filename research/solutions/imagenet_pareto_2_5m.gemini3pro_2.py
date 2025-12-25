import torch
import torch.nn as nn
import torch.optim as optim
import numpy as np
import math

class ResidualBlock(nn.Module):
    def __init__(self, hidden_dim, dropout_rate):
        super(ResidualBlock, self).__init__()
        self.linear = nn.Linear(hidden_dim, hidden_dim)
        self.bn = nn.BatchNorm1d(hidden_dim)
        self.act = nn.GELU()
        self.dropout = nn.Dropout(dropout_rate)
        
    def forward(self, x):
        residual = x
        out = self.linear(x)
        out = self.bn(out)
        out = self.act(out)
        out = self.dropout(out)
        return out + residual

class ParetoModel(nn.Module):
    def __init__(self, input_dim, num_classes, param_limit):
        super(ParetoModel, self).__init__()
        
        # Dynamically calculate hidden dimension H to maximize capacity within budget
        # Architecture layout:
        # 1. Input Project: Linear(In, H) + Bias + BN(2H)
        # 2. Block 1:       Linear(H, H) + Bias + BN(2H)
        # 3. Block 2:       Linear(H, H) + Bias + BN(2H)
        # 4. Output Head:   Linear(H, Out) + Bias
        
        # Parameter Count Equation:
        # L1: H*In + H + 2H = H(In + 3)
        # B1: H^2 + H + 2H  = H^2 + 3H
        # B2: H^2 + H + 2H  = H^2 + 3H
        # L4: H*Out + Out   = H*Out + Out
        # Total = 2H^2 + H(In + Out + 9) + Out
        
        # Solve for H: 2H^2 + H(In + Out + 9) + (Out - Limit) = 0
        
        # Use 96% of limit to be safe
        safe_limit = param_limit * 0.96
        
        a = 2
        b = input_dim + num_classes + 9
        c = num_classes - safe_limit
        
        discriminant = b**2 - 4*a*c
        h = int((-b + math.sqrt(discriminant)) / (2*a))
        
        self.hidden_dim = h
        
        self.input_layer = nn.Sequential(
            nn.Linear(input_dim, h),
            nn.BatchNorm1d(h),
            nn.GELU(),
            nn.Dropout(0.3)
        )
        
        self.block1 = ResidualBlock(h, dropout_rate=0.4)
        self.block2 = ResidualBlock(h, dropout_rate=0.4)
        
        self.output_layer = nn.Linear(h, num_classes)
        
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
        x = self.input_layer(x)
        x = self.block1(x)
        x = self.block2(x)
        x = self.output_layer(x)
        return x

class Solution:
    def solve(self, train_loader, val_loader, metadata: dict = None) -> torch.nn.Module:
        # Set seeds for reproducibility
        torch.manual_seed(42)
        np.random.seed(42)
        
        # Extract metadata
        input_dim = metadata.get("input_dim", 384)
        num_classes = metadata.get("num_classes", 128)
        param_limit = metadata.get("param_limit", 2500000)
        device = metadata.get("device", "cpu")
        
        # Initialize model
        model = ParetoModel(input_dim, num_classes, param_limit)
        model = model.to(device)
        
        # Training Hyperparameters
        epochs = 160  # Sufficient for CPU budget and convergence
        lr = 0.001
        weight_decay = 0.02
        mixup_alpha = 0.4
        
        optimizer = optim.AdamW(model.parameters(), lr=lr, weight_decay=weight_decay)
        scheduler = optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=epochs, eta_min=1e-6)
        criterion = nn.CrossEntropyLoss(label_smoothing=0.1)
        
        best_acc = 0.0
        best_state = None
        
        for epoch in range(epochs):
            model.train()
            for inputs, targets in train_loader:
                inputs, targets = inputs.to(device), targets.to(device)
                
                optimizer.zero_grad()
                
                # Mixup Augmentation
                if mixup_alpha > 0:
                    lam = np.random.beta(mixup_alpha, mixup_alpha)
                    index = torch.randperm(inputs.size(0)).to(device)
                    mixed_inputs = lam * inputs + (1 - lam) * inputs[index]
                    target_a, target_b = targets, targets[index]
                    
                    outputs = model(mixed_inputs)
                    loss = lam * criterion(outputs, target_a) + (1 - lam) * criterion(outputs, target_b)
                else:
                    outputs = model(inputs)
                    loss = criterion(outputs, targets)
                
                loss.backward()
                optimizer.step()
            
            scheduler.step()
            
            # Validation
            model.eval()
            correct = 0
            total = 0
            with torch.no_grad():
                for inputs, targets in val_loader:
                    inputs, targets = inputs.to(device), targets.to(device)
                    outputs = model(inputs)
                    preds = outputs.argmax(dim=1)
                    correct += (preds == targets).sum().item()
                    total += targets.size(0)
            
            acc = correct / total
            if acc > best_acc:
                best_acc = acc
                # Save state dict on CPU
                best_state = {k: v.cpu() for k, v in model.state_dict().items()}
        
        # Load best model
        if best_state is not None:
            model.load_state_dict(best_state)
            
        return model
