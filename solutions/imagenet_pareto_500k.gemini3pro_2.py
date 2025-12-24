import torch
import torch.nn as nn
import torch.optim as optim
import numpy as np
import math
import copy

class ResidualBlock(nn.Module):
    def __init__(self, hidden_dim, dropout_rate):
        super(ResidualBlock, self).__init__()
        self.block = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim),
            nn.BatchNorm1d(hidden_dim),
            nn.ReLU(),
            nn.Dropout(dropout_rate)
        )

    def forward(self, x):
        return x + self.block(x)

class AdaptiveNet(nn.Module):
    def __init__(self, input_dim, hidden_dim, output_dim, num_res_blocks, dropout_rate):
        super(AdaptiveNet, self).__init__()
        
        # Input projection
        self.input_proj = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.BatchNorm1d(hidden_dim),
            nn.ReLU(),
            nn.Dropout(dropout_rate)
        )
        
        # Residual blocks
        self.blocks = nn.ModuleList([
            ResidualBlock(hidden_dim, dropout_rate) for _ in range(num_res_blocks)
        ])
        
        # Output head
        self.head = nn.Linear(hidden_dim, output_dim)

    def forward(self, x):
        x = self.input_proj(x)
        for block in self.blocks:
            x = block(x)
        return self.head(x)

class Solution:
    def solve(self, train_loader, val_loader, metadata: dict = None) -> torch.nn.Module:
        # Extract metadata
        input_dim = metadata.get("input_dim", 384)
        num_classes = metadata.get("num_classes", 128)
        param_limit = metadata.get("param_limit", 500000)
        device = metadata.get("device", "cpu")
        
        # Architecture Planning to maximize capacity within limits
        # We use an architecture with:
        # 1. Input Block: Linear(In, H) + BN(H) -> Params: In*H + H + 2H = H*(In + 3)
        # 2. ResBlocks (k=2): k * [Linear(H, H) + BN(H)] -> Params: k*(H^2 + H + 2H) = k*(H^2 + 3H)
        # 3. Head: Linear(H, Out) -> Params: H*Out + Out
        # Total Params = k*H^2 + H*(In + 3 + 3k + Out) + Out
        
        k = 2 # Number of residual blocks
        a = float(k)
        b = float(input_dim + num_classes + 3 + (3 * k))
        c = float(num_classes - param_limit)
        
        # Quadratic formula to find max Hidden Dim (H)
        delta = b**2 - 4*a*c
        max_h = int((-b + math.sqrt(delta)) / (2*a))
        
        # Set parameters
        hidden_dim = max_h - 2 # Buffer for safety
        dropout_rate = 0.4     # High dropout for small dataset
        
        # Instantiate Model
        model = AdaptiveNet(input_dim, hidden_dim, num_classes, k, dropout_rate).to(device)
        
        # Strict Parameter Count Check & Adjustment
        def count_params(m):
            return sum(p.numel() for p in m.parameters() if p.requires_grad)
            
        while count_params(model) > param_limit:
            hidden_dim -= 4
            model = AdaptiveNet(input_dim, hidden_dim, num_classes, k, dropout_rate).to(device)
            
        # Training Configuration
        optimizer = optim.AdamW(model.parameters(), lr=0.001, weight_decay=1e-2)
        # Label smoothing helps with synthetic/noisy data and prevents overfitting
        criterion = nn.CrossEntropyLoss(label_smoothing=0.1)
        
        epochs = 80
        scheduler = optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=epochs)
        
        best_val_acc = 0.0
        best_model_state = copy.deepcopy(model.state_dict())
        
        # Mixup Augmentation Settings
        use_mixup = True
        mixup_alpha = 0.4
        
        for epoch in range(epochs):
            model.train()
            
            for inputs, targets in train_loader:
                inputs, targets = inputs.to(device), targets.to(device)
                optimizer.zero_grad()
                
                # Apply Mixup during first 90% of training
                if use_mixup and epoch < int(epochs * 0.9):
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
                    _, predicted = outputs.max(1)
                    total += targets.size(0)
                    correct += predicted.eq(targets).sum().item()
            
            val_acc = correct / total
            
            # Save best model
            if val_acc >= best_val_acc:
                best_val_acc = val_acc
                best_model_state = copy.deepcopy(model.state_dict())
        
        # Restore best model
        model.load_state_dict(best_model_state)
        return model
