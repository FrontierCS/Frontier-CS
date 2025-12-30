import torch
import torch.nn as nn
import torch.optim as optim
import math
import numpy as np

class ResBlock(nn.Module):
    def __init__(self, dim, dropout_rate=0.25):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(dim, dim),
            nn.BatchNorm1d(dim),
            nn.ReLU(inplace=True),
            nn.Dropout(dropout_rate),
            nn.Linear(dim, dim),
            nn.BatchNorm1d(dim),
            nn.ReLU(inplace=True),
            nn.Dropout(dropout_rate)
        )
        
    def forward(self, x):
        return x + self.net(x)

class DynamicNet(nn.Module):
    def __init__(self, input_dim, num_classes, param_limit):
        super().__init__()
        
        # We aim to maximize model capacity (width) within the parameter budget.
        # Architecture:
        # Input: Linear(In, H) -> BN -> ReLU -> Dropout
        # Body: D x ResBlock(H)
        # Output: Linear(H, Out)
        
        depth = 3  # Number of ResBlocks
        
        # Parameter Count Calculation:
        # Input Block: (In*H + H) + 2*H (BN params) = H*(In + 3)
        # ResBlock: 2 * (H*H + H + 2*H) = 2H^2 + 6H
        # All Blocks: D * (2H^2 + 6H)
        # Output Block: H*Out + Out
        #
        # Total Params = (2*D) * H^2 + (In + 3 + 6*D + Out) * H + Out
        # We solve the quadratic equation ax^2 + bx + c = 0 for H
        
        a = 2.0 * depth
        b = float(input_dim + 3 + 6 * depth + num_classes)
        c = float(num_classes - param_limit)
        
        # Quadratic formula: H = (-b + sqrt(b^2 - 4ac)) / 2a
        delta = b*b - 4*a*c
        if delta < 0:
            # Fallback if budget is extremely tight
            hidden_dim = 64
        else:
            h_max = (-b + math.sqrt(delta)) / (2*a)
            # Subtract small buffer to ensure we are strictly under the limit due to float/int rounding
            hidden_dim = int(h_max) - 2
            
        self.hidden_dim = hidden_dim
        dropout_rate = 0.25
        
        self.input_proj = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.BatchNorm1d(hidden_dim),
            nn.ReLU(inplace=True),
            nn.Dropout(dropout_rate)
        )
        
        self.blocks = nn.ModuleList([
            ResBlock(hidden_dim, dropout_rate) for _ in range(depth)
        ])
        
        self.output_head = nn.Linear(hidden_dim, num_classes)
        
        # Weight Initialization
        for m in self.modules():
            if isinstance(m, nn.Linear):
                nn.init.kaiming_normal_(m.weight, mode='fan_out', nonlinearity='relu')
                if m.bias is not None:
                    nn.init.constant_(m.bias, 0)
            elif isinstance(m, nn.BatchNorm1d):
                nn.init.constant_(m.weight, 1)
                nn.init.constant_(m.bias, 0)
                
    def forward(self, x):
        x = self.input_proj(x)
        for block in self.blocks:
            x = block(x)
        return self.output_head(x)

class Solution:
    def solve(self, train_loader, val_loader, metadata: dict = None) -> torch.nn.Module:
        # Extract metadata
        num_classes = metadata.get("num_classes", 128)
        input_dim = metadata.get("input_dim", 384)
        param_limit = metadata.get("param_limit", 2500000)
        device = metadata.get("device", "cpu")
        
        # Initialize optimized model
        model = DynamicNet(input_dim, num_classes, param_limit)
        model = model.to(device)
        
        # Verify parameter count safety
        total_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
        if total_params > param_limit:
            # This should not happen with the quadratic calc, but failsafe
            print(f"Warning: Model size {total_params} exceeds limit. Reducing size.")
            model = DynamicNet(input_dim, num_classes, int(param_limit * 0.95))
            model = model.to(device)

        # Training Configuration
        # With 2048 samples and 2.5M params, regularization is key.
        epochs = 100
        lr = 0.001
        
        optimizer = optim.AdamW(model.parameters(), lr=lr, weight_decay=0.015)
        # Cosine annealing ensures we settle into a good minima
        scheduler = optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=epochs, eta_min=1e-6)
        # Label smoothing helps with noisy synthetic data and overfitting
        criterion = nn.CrossEntropyLoss(label_smoothing=0.1)
        
        best_acc = 0.0
        best_model_state = {k: v.cpu() for k, v in model.state_dict().items()}
        
        # Mixup Hyperparameters
        mixup_alpha = 0.4
        mixup_prob = 0.6
        
        for epoch in range(epochs):
            model.train()
            
            for inputs, targets in train_loader:
                inputs, targets = inputs.to(device), targets.to(device)
                
                # Apply Mixup Augmentation
                # Essential for small datasets (16 shots/class) to improve generalization
                if np.random.random() < mixup_prob and inputs.size(0) > 1:
                    lam = np.random.beta(mixup_alpha, mixup_alpha)
                    index = torch.randperm(inputs.size(0)).to(device)
                    
                    mixed_inputs = lam * inputs + (1 - lam) * inputs[index]
                    target_a, target_b = targets, targets[index]
                    
                    outputs = model(mixed_inputs)
                    loss = lam * criterion(outputs, target_a) + (1 - lam) * criterion(outputs, target_b)
                else:
                    outputs = model(inputs)
                    loss = criterion(outputs, targets)
                
                optimizer.zero_grad()
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
                    total += targets.numel()
            
            acc = correct / total if total > 0 else 0.0
            
            # Save best model
            if acc >= best_acc:
                best_acc = acc
                best_model_state = {k: v.cpu() for k, v in model.state_dict().items()}
        
        # Restore best weights
        model.load_state_dict(best_model_state)
        return model