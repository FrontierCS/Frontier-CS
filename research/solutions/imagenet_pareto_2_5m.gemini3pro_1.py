import torch
import torch.nn as nn
import torch.optim as optim
import math
import copy

class ResidualBlock(nn.Module):
    def __init__(self, dim, dropout=0.2):
        super(ResidualBlock, self).__init__()
        self.net = nn.Sequential(
            nn.Linear(dim, dim),
            nn.BatchNorm1d(dim),
            nn.ReLU(),
            nn.Dropout(dropout)
        )
        self.relu = nn.ReLU()

    def forward(self, x):
        return self.relu(x + self.net(x))

class OptimizedModel(nn.Module):
    def __init__(self, input_dim, num_classes, param_limit):
        super(OptimizedModel, self).__init__()
        
        # Calculate maximum hidden dimension W to fit within parameter budget
        # Architecture: 
        # 1. Input Layer: Linear(In, W) + BN(W)
        # 2. 3x Residual Blocks: Linear(W, W) + BN(W)
        # 3. Output Layer: Linear(W, Out)
        
        # Parameter Count Equation:
        # P_in = (input_dim * W + W) + (2 * W) = W(input_dim + 3)
        # P_block = (W * W + W) + (2 * W) = W^2 + 3W
        # P_out = (W * num_classes + num_classes)
        # Total = P_in + 3 * P_block + P_out
        # Total = W(input_dim + 3) + 3(W^2 + 3W) + W(num_classes) + num_classes
        # Total = 3W^2 + W(input_dim + 12 + num_classes) + num_classes
        
        # Quadratic: 3W^2 + bW + c = 0
        a = 3.0
        b = input_dim + num_classes + 12.0
        # Use a safety buffer to ensure we are strictly under the limit
        c_val = num_classes - param_limit + 2500 
        
        delta = b*b - 4*a*c_val
        if delta < 0:
            width = 512 # Fallback safe width
        else:
            width = int((-b + math.sqrt(delta)) / (2*a))
            
        # Verify strict limit and adjust if necessary due to rounding
        while True:
            total_params = (input_dim * width + width) + (2 * width) # Input + BN
            total_params += 3 * ((width * width + width) + (2 * width)) # 3 Blocks
            total_params += (width * num_classes + num_classes) # Output
            
            if total_params < param_limit:
                break
            width -= 4 # Reduce width slightly until fit

        self.input_layer = nn.Sequential(
            nn.Linear(input_dim, width),
            nn.BatchNorm1d(width),
            nn.ReLU(),
            nn.Dropout(0.2)
        )
        
        self.blocks = nn.ModuleList([ResidualBlock(width, 0.2) for _ in range(3)])
        
        self.output_layer = nn.Linear(width, num_classes)

    def forward(self, x):
        x = self.input_layer(x)
        for block in self.blocks:
            x = block(x)
        return self.output_layer(x)

class Solution:
    def solve(self, train_loader, val_loader, metadata: dict = None) -> torch.nn.Module:
        # Extract metadata
        input_dim = metadata.get("input_dim", 384)
        num_classes = metadata.get("num_classes", 128)
        param_limit = metadata.get("param_limit", 2500000)
        device = metadata.get("device", "cpu")
        
        # Initialize model
        model = OptimizedModel(input_dim, num_classes, param_limit)
        model = model.to(device)
        
        # Training Configuration
        # Label smoothing helps with generalization on synthetic data
        criterion = nn.CrossEntropyLoss(label_smoothing=0.1)
        optimizer = optim.AdamW(model.parameters(), lr=0.001, weight_decay=0.01)
        
        # OneCycleLR for efficient convergence
        epochs = 70
        scheduler = optim.lr_scheduler.OneCycleLR(
            optimizer,
            max_lr=0.0015,
            epochs=epochs,
            steps_per_epoch=len(train_loader),
            pct_start=0.3,
            div_factor=25.0,
            final_div_factor=1000.0
        )
        
        best_acc = 0.0
        best_weights = copy.deepcopy(model.state_dict())
        
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
                    _, preds = torch.max(outputs, 1)
                    correct += (preds == targets).sum().item()
                    total += targets.size(0)
            
            acc = correct / total
            if acc > best_acc:
                best_acc = acc
                best_weights = copy.deepcopy(model.state_dict())
        
        # Return best model found during training
        model.load_state_dict(best_weights)
        return model