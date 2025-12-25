import torch
import torch.nn as nn
import torch.optim as optim
import math
import copy

class Solution:
    def solve(self, train_loader, val_loader, metadata: dict = None) -> torch.nn.Module:
        input_dim = metadata.get("input_dim", 384)
        num_classes = metadata.get("num_classes", 128)
        device = metadata.get("device", "cpu")
        param_limit = metadata.get("param_limit", 1000000)

        # Dynamic architecture sizing to maximize capacity within budget
        # Model Structure:
        # Layer 1: Linear(in, w, bias=False) -> BN -> ReLU -> Dropout
        # Layer 2: Linear(w, w, bias=False) -> BN -> ReLU -> Dropout
        # Layer 3: Linear(w, w, bias=False) -> BN -> ReLU -> Dropout
        # Layer 4: Linear(w, out, bias=True)
        
        # Parameter Count Equation:
        # L1: in*w
        # L2: w*w
        # L3: w*w
        # L4: w*out + out
        # BNs: 3 * 2 * w = 6w
        # Total P(w) = 2w^2 + (in + out + 6)w + out
        
        # Solving 2w^2 + bw + c <= limit
        a = 2
        b = input_dim + num_classes + 6
        c = num_classes - param_limit
        
        # Quadratic formula positive root
        discriminant = b**2 - 4 * a * c
        max_width = int((-b + math.sqrt(discriminant)) / (2 * a))
        
        # Apply safety margin
        width = max_width - 2

        class OptimizedMLP(nn.Module):
            def __init__(self, in_d, out_d, w):
                super().__init__()
                self.features = nn.Sequential(
                    nn.Linear(in_d, w, bias=False),
                    nn.BatchNorm1d(w),
                    nn.ReLU(),
                    nn.Dropout(0.3),
                    
                    nn.Linear(w, w, bias=False),
                    nn.BatchNorm1d(w),
                    nn.ReLU(),
                    nn.Dropout(0.3),
                    
                    nn.Linear(w, w, bias=False),
                    nn.BatchNorm1d(w),
                    nn.ReLU(),
                    nn.Dropout(0.3),
                    
                    nn.Linear(w, out_d)
                )

            def forward(self, x):
                return self.features(x)

        # Instantiate and verify constraint
        model = OptimizedMLP(input_dim, num_classes, width).to(device)
        current_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
        
        # Fallback if calculation was slightly off due to rounding
        if current_params > param_limit:
            width = int(width * 0.98)
            model = OptimizedMLP(input_dim, num_classes, width).to(device)
        
        # Training Setup
        criterion = nn.CrossEntropyLoss()
        # AdamW with weight decay for regularization on small data
        optimizer = optim.AdamW(model.parameters(), lr=0.001, weight_decay=1e-2)
        # Cosine Schedule for smooth convergence
        epochs = 60
        scheduler = optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=epochs)
        
        best_acc = 0.0
        best_model_state = copy.deepcopy(model.state_dict())
        
        # Training Loop
        for epoch in range(epochs):
            model.train()
            for inputs, targets in train_loader:
                inputs, targets = inputs.to(device), targets.to(device)
                
                # Input noise injection for robustness (Data Augmentation for vectors)
                noise = torch.randn_like(inputs) * 0.05
                inputs_noisy = inputs + noise
                
                optimizer.zero_grad()
                outputs = model(inputs_noisy)
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
                    _, preds = torch.max(outputs, 1)
                    correct += (preds == targets).sum().item()
                    total += targets.size(0)
            
            val_acc = correct / total
            
            # Checkpoint best model
            if val_acc >= best_acc:
                best_acc = val_acc
                best_model_state = copy.deepcopy(model.state_dict())
        
        # Restore best model
        model.load_state_dict(best_model_state)
        model.eval()
        return model
