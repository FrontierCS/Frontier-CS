import torch
import torch.nn as nn
import torch.optim as optim
import numpy as np
import copy
import math

class ResidualBlock(nn.Module):
    def __init__(self, dim, dropout=0.3):
        super(ResidualBlock, self).__init__()
        self.net = nn.Sequential(
            nn.Linear(dim, dim, bias=False),
            nn.BatchNorm1d(dim),
            nn.ReLU(),
            nn.Dropout(dropout)
        )
        
    def forward(self, x):
        return x + self.net(x)

class ParetoNet(nn.Module):
    def __init__(self, input_dim, num_classes, param_limit):
        super(ParetoNet, self).__init__()
        
        # Determine hidden dimension to maximize capacity within budget
        # We aim for 3 Residual Blocks + Head
        # Params ~= 3 * (h^2 + 2h) + (h * c + c)
        # For h=384, c=128:
        # 3 * (147456 + 768) + (49152 + 128)
        # 3 * 148224 + 49280 = 444672 + 49280 = 493,952 < 500,000
        
        # If input_dim matches 384, we use h=384.
        # If input_dim is different, we verify or scale.
        
        self.hidden_dim = input_dim
        
        # Verify estimated cost
        estimated_params = 3 * (self.hidden_dim**2 + 2*self.hidden_dim) + (self.hidden_dim * num_classes + num_classes)
        
        if estimated_params > param_limit:
            # Fallback to a safe dimension if inputs differ significantly
            # Solve 3h^2 approx param_limit
            self.hidden_dim = int(math.sqrt(param_limit / 3.5))
            self.project = nn.Linear(input_dim, self.hidden_dim)
        else:
            self.project = nn.Identity()
            
        self.blocks = nn.ModuleList([
            ResidualBlock(self.hidden_dim, dropout=0.4),
            ResidualBlock(self.hidden_dim, dropout=0.4),
            ResidualBlock(self.hidden_dim, dropout=0.4)
        ])
        
        self.head = nn.Linear(self.hidden_dim, num_classes)
        
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
        x = self.project(x)
        for block in self.blocks:
            x = block(x)
        return self.head(x)

class Solution:
    def solve(self, train_loader, val_loader, metadata: dict = None) -> torch.nn.Module:
        if metadata is None:
            metadata = {}
            
        input_dim = metadata.get("input_dim", 384)
        num_classes = metadata.get("num_classes", 128)
        param_limit = metadata.get("param_limit", 500000)
        device = metadata.get("device", "cpu")
        
        model = ParetoNet(input_dim, num_classes, param_limit).to(device)
        
        # Optimization Setup
        # Using AdamW with Weight Decay for regularization
        optimizer = optim.AdamW(model.parameters(), lr=0.001, weight_decay=0.02)
        criterion = nn.CrossEntropyLoss()
        
        epochs = 75
        steps_per_epoch = len(train_loader)
        
        # OneCycleLR for efficient convergence
        scheduler = optim.lr_scheduler.OneCycleLR(
            optimizer, 
            max_lr=0.002, 
            steps_per_epoch=steps_per_epoch, 
            epochs=epochs,
            pct_start=0.3
        )
        
        # Mixup parameters
        mixup_alpha = 0.4
        
        best_acc = 0.0
        best_state = copy.deepcopy(model.state_dict())
        
        for epoch in range(epochs):
            model.train()
            for inputs, targets in train_loader:
                inputs, targets = inputs.to(device), targets.to(device)
                
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
                
                optimizer.zero_grad()
                loss.backward()
                optimizer.step()
                scheduler.step()
            
            # Evaluate periodically and at the end
            if epoch >= epochs - 15 or epoch % 5 == 0:
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
                
                if total > 0:
                    acc = correct / total
                    if acc >= best_acc:
                        best_acc = acc
                        best_state = copy.deepcopy(model.state_dict())
                        
        model.load_state_dict(best_state)
        return model