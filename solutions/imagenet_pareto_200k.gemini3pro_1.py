import torch
import torch.nn as nn
import torch.optim as optim
import math

class DynamicNet(nn.Module):
    def __init__(self, input_dim, num_classes, hidden_dim):
        super(DynamicNet, self).__init__()
        self.features = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.BatchNorm1d(hidden_dim),
            nn.ReLU(),
            nn.Dropout(0.25),
            nn.Linear(hidden_dim, hidden_dim),
            nn.BatchNorm1d(hidden_dim),
            nn.ReLU(),
            nn.Dropout(0.25),
            nn.Linear(hidden_dim, num_classes)
        )

    def forward(self, x):
        return self.features(x)

class Solution:
    def solve(self, train_loader, val_loader, metadata: dict = None) -> torch.nn.Module:
        # Extract metadata
        input_dim = metadata.get("input_dim", 384)
        num_classes = metadata.get("num_classes", 128)
        param_limit = metadata.get("param_limit", 200000)
        device = metadata.get("device", "cpu")
        
        # Calculate max hidden dim to satisfy parameter limit
        # Architecture: 384 -> H -> H -> 128 (with Batch Norms)
        # Parameters count equation:
        # Layer 1: (Input + 1) * H
        # BN 1: 2 * H
        # Layer 2: (H + 1) * H
        # BN 2: 2 * H
        # Layer 3: (H + 1) * Output
        # Total = H^2 + (Input + Output + 6)H + Output <= Limit
        
        a = 1
        b = input_dim + num_classes + 6
        c = num_classes - param_limit
        
        # Quadratic formula to find max H
        delta = b**2 - 4*a*c
        max_h = math.floor((-b + math.sqrt(delta)) / (2*a))
        
        # Clamp hidden dim to 256 (sufficient for this problem scale and good for regularization)
        hidden_dim = min(int(max_h), 256)
        
        model = DynamicNet(input_dim, num_classes, hidden_dim).to(device)
        
        # Training hyperparameters
        epochs = 80
        lr = 1e-3
        weight_decay = 1e-2
        
        optimizer = optim.AdamW(model.parameters(), lr=lr, weight_decay=weight_decay)
        criterion = nn.CrossEntropyLoss(label_smoothing=0.1)
        
        total_steps = epochs * len(train_loader)
        scheduler = optim.lr_scheduler.OneCycleLR(
            optimizer,
            max_lr=lr,
            total_steps=total_steps,
            pct_start=0.3,
            div_factor=25.0,
            final_div_factor=1000.0
        )
        
        best_val_acc = 0.0
        best_state = None
        
        # Mixup setup
        mixup_alpha = 0.4
        
        for epoch in range(epochs):
            model.train()
            for inputs, targets in train_loader:
                inputs, targets = inputs.to(device), targets.to(device)
                
                optimizer.zero_grad()
                
                # Apply Mixup for the first 85% of epochs
                if epoch < int(epochs * 0.85):
                    lam = torch.distributions.Beta(mixup_alpha, mixup_alpha).sample().item()
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
                    _, predicted = torch.max(outputs, 1)
                    total += targets.size(0)
                    correct += (predicted == targets).sum().item()
            
            val_acc = correct / total
            
            # Save best model
            if val_acc >= best_val_acc:
                best_val_acc = val_acc
                best_state = {k: v.clone() for k, v in model.state_dict().items()}
        
        if best_state is not None:
            model.load_state_dict(best_state)
            
        return model
