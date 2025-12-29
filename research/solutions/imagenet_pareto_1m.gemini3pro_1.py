import torch
import torch.nn as nn
import torch.optim as optim
import numpy as np
import copy
import math

class ResidualBlock(nn.Module):
    def __init__(self, dim, dropout_rate):
        super(ResidualBlock, self).__init__()
        self.net = nn.Sequential(
            nn.Linear(dim, dim),
            nn.BatchNorm1d(dim),
            nn.SiLU(),
            nn.Dropout(dropout_rate)
        )

    def forward(self, x):
        return x + self.net(x)

class OptimizedModel(nn.Module):
    def __init__(self, input_dim, num_classes, hidden_dim, dropout_rate):
        super(OptimizedModel, self).__init__()
        
        # Normalize raw input features
        self.input_norm = nn.BatchNorm1d(input_dim)
        
        # Project to hidden dimension
        self.input_proj = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.BatchNorm1d(hidden_dim),
            nn.SiLU(),
            nn.Dropout(dropout_rate)
        )
        
        # Deep residual processing
        # Using 3 blocks (each contains 1 Linear layer + skip connection)
        self.blocks = nn.ModuleList([
            ResidualBlock(hidden_dim, dropout_rate),
            ResidualBlock(hidden_dim, dropout_rate),
            ResidualBlock(hidden_dim, dropout_rate)
        ])
        
        # Output projection
        self.output_proj = nn.Linear(hidden_dim, num_classes)
        
        # Robust initialization
        for m in self.modules():
            if isinstance(m, nn.Linear):
                nn.init.kaiming_normal_(m.weight, mode='fan_out', nonlinearity='relu')
                if m.bias is not None:
                    nn.init.constant_(m.bias, 0)
            elif isinstance(m, nn.BatchNorm1d):
                nn.init.constant_(m.weight, 1)
                nn.init.constant_(m.bias, 0)

    def forward(self, x):
        x = self.input_norm(x)
        x = self.input_proj(x)
        for block in self.blocks:
            x = block(x)
        return self.output_proj(x)

class Solution:
    def solve(self, train_loader, val_loader, metadata: dict = None) -> torch.nn.Module:
        if metadata is None:
            metadata = {}
            
        input_dim = metadata.get("input_dim", 384)
        num_classes = metadata.get("num_classes", 128)
        device = metadata.get("device", "cpu")
        
        # Dynamic Hidden Dimension Calculation
        # We model the parameter count P as a function of hidden_dim H:
        # P = 3*H^2 + H*(input_dim + num_classes + 12) + (2*input_dim + num_classes)
        # We solve for H to maximize usage of the 1,000,000 budget with a safety margin.
        
        target_budget = 980000  # Leave 20k buffer
        a = 3
        b = input_dim + num_classes + 12
        c = 2 * input_dim + num_classes - target_budget
        
        # Quadratic formula: (-b + sqrt(b^2 - 4ac)) / 2a
        discriminant = b**2 - 4*a*c
        hidden_dim = int((-b + math.sqrt(discriminant)) / (2*a))
        
        # Training Hyperparameters
        epochs = 65
        lr = 0.002
        weight_decay = 0.02
        dropout_rate = 0.25
        mixup_alpha = 0.4
        
        # Initialize Model
        model = OptimizedModel(input_dim, num_classes, hidden_dim, dropout_rate).to(device)
        
        # Setup Optimizer and Scheduler
        optimizer = optim.AdamW(model.parameters(), lr=lr, weight_decay=weight_decay)
        
        # OneCycleLR for super-convergence on small datasets
        steps_per_epoch = len(train_loader)
        scheduler = optim.lr_scheduler.OneCycleLR(
            optimizer, 
            max_lr=lr, 
            epochs=epochs, 
            steps_per_epoch=steps_per_epoch,
            pct_start=0.3,
            div_factor=25,
            final_div_factor=1000
        )
        
        # Loss function with Label Smoothing
        criterion = nn.CrossEntropyLoss(label_smoothing=0.1)
        
        best_acc = 0.0
        best_state = copy.deepcopy(model.state_dict())
        
        for epoch in range(epochs):
            # Training Phase
            model.train()
            for inputs, targets in train_loader:
                inputs, targets = inputs.to(device), targets.to(device)
                
                # Apply Mixup Augmentation
                # Only apply if batch size > 1
                if inputs.size(0) > 1 and np.random.random() < 0.6:
                    lam = np.random.beta(mixup_alpha, mixup_alpha)
                    index = torch.randperm(inputs.size(0)).to(device)
                    mixed_inputs = lam * inputs + (1 - lam) * inputs[index]
                    y_a, y_b = targets, targets[index]
                    
                    outputs = model(mixed_inputs)
                    loss = lam * criterion(outputs, y_a) + (1 - lam) * criterion(outputs, y_b)
                else:
                    outputs = model(inputs)
                    loss = criterion(outputs, targets)
                
                optimizer.zero_grad()
                loss.backward()
                optimizer.step()
                scheduler.step()
            
            # Validation Phase
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
            
            val_acc = correct / total
            
            # Save Best Model
            if val_acc >= best_acc:
                best_acc = val_acc
                best_state = copy.deepcopy(model.state_dict())
        
        # Return best performing model
        model.load_state_dict(best_state)
        return model