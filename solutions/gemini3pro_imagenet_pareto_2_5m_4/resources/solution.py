import torch
import torch.nn as nn
import torch.optim as optim
import math
import copy

class Solution:
    def solve(self, train_loader, val_loader, metadata: dict = None) -> torch.nn.Module:
        """
        Train a model on synthetic ImageNet-like data within parameter constraints.
        """
        if metadata is None:
            metadata = {}
            
        # Extract metadata
        input_dim = metadata.get("input_dim", 384)
        num_classes = metadata.get("num_classes", 128)
        param_limit = metadata.get("param_limit", 2500000)
        device = metadata.get("device", "cpu")
        
        # Calculate target parameters (keep a safety buffer)
        target_params = int(param_limit * 0.98)
        
        # Architecture definition: 4 Hidden Layers of width W
        # Structure:
        #   Layer 1: Linear(In, W) + BN + SiLU + Drop
        #   Layer 2: Linear(W, W) + BN + SiLU + Drop
        #   Layer 3: Linear(W, W) + BN + SiLU + Drop
        #   Layer 4: Linear(W, W) + BN + SiLU + Drop
        #   Layer 5: Linear(W, Out)
        #
        # Parameter Count Estimation:
        #   L1: In*W + W (bias) + 2*W (BN) = (In + 3)*W
        #   L2, L3, L4: 3 * (W*W + W + 2*W) = 3*W^2 + 9*W
        #   L5: W*Out + Out (bias)
        # Total = 3*W^2 + (In + Out + 12)*W + Out
        # Solve quadratic: 3W^2 + (In + Out + 12)W + (Out - Target) = 0
        
        a = 3.0
        b = float(input_dim + num_classes + 12)
        c = float(num_classes - target_params)
        
        delta = b**2 - 4*a*c
        if delta < 0:
            width = 512  # Safe fallback
        else:
            width = int((-b + math.sqrt(delta)) / (2*a))
            
        class OptimizedNet(nn.Module):
            def __init__(self, in_d, out_d, w):
                super().__init__()
                self.features = nn.Sequential(
                    nn.Linear(in_d, w),
                    nn.BatchNorm1d(w),
                    nn.SiLU(),
                    nn.Dropout(0.25),
                    
                    nn.Linear(w, w),
                    nn.BatchNorm1d(w),
                    nn.SiLU(),
                    nn.Dropout(0.25),
                    
                    nn.Linear(w, w),
                    nn.BatchNorm1d(w),
                    nn.SiLU(),
                    nn.Dropout(0.25),
                    
                    nn.Linear(w, w),
                    nn.BatchNorm1d(w),
                    nn.SiLU(),
                    nn.Dropout(0.25),
                )
                self.classifier = nn.Linear(w, out_d)
                
            def forward(self, x):
                x = self.features(x)
                return self.classifier(x)

        # Initialize model
        model = OptimizedNet(input_dim, num_classes, width).to(device)
        
        # Strict parameter check and adjustment
        def get_param_count(m):
            return sum(p.numel() for p in m.parameters() if p.requires_grad)
            
        while get_param_count(model) > param_limit:
            width -= 8
            model = OptimizedNet(input_dim, num_classes, width).to(device)
            
        # Training configuration
        # Small dataset (2048 samples) allows more epochs
        epochs = 75
        lr = 2e-3
        weight_decay = 1e-2
        
        criterion = nn.CrossEntropyLoss(label_smoothing=0.1)
        optimizer = optim.AdamW(model.parameters(), lr=lr, weight_decay=weight_decay)
        
        # OneCycle scheduler for super-convergence
        scheduler = optim.lr_scheduler.OneCycleLR(
            optimizer,
            max_lr=lr,
            epochs=epochs,
            steps_per_epoch=len(train_loader),
            pct_start=0.2,
            div_factor=25.0,
            final_div_factor=1000.0
        )
        
        best_acc = 0.0
        best_state = copy.deepcopy(model.state_dict())
        
        # Training Loop
        for epoch in range(epochs):
            model.train()
            for inputs, targets in train_loader:
                inputs, targets = inputs.to(device), targets.to(device)
                
                optimizer.zero_grad()
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
                    _, predicted = torch.max(outputs, 1)
                    total += targets.size(0)
                    correct += (predicted == targets).sum().item()
            
            acc = correct / total
            if acc > best_acc:
                best_acc = acc
                best_state = copy.deepcopy(model.state_dict())
                
        # Return best model
        model.load_state_dict(best_state)
        return model
