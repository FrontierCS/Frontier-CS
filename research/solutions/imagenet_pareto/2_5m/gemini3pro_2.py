import torch
import torch.nn as nn
import torch.optim as optim
import numpy as np
import math
import copy

class ParetoModel(nn.Module):
    def __init__(self, input_dim, num_classes, width):
        super().__init__()
        # Input normalization
        self.input_bn = nn.BatchNorm1d(input_dim)
        
        # 3-Hidden Layer MLP (4 Linear Layers)
        self.layers = nn.Sequential(
            nn.Linear(input_dim, width),
            nn.BatchNorm1d(width),
            nn.ReLU(),
            nn.Dropout(0.25),
            
            nn.Linear(width, width),
            nn.BatchNorm1d(width),
            nn.ReLU(),
            nn.Dropout(0.25),
            
            nn.Linear(width, width),
            nn.BatchNorm1d(width),
            nn.ReLU(),
            nn.Dropout(0.25),
            
            nn.Linear(width, num_classes)
        )
        
        # Initialization
        for m in self.modules():
            if isinstance(m, nn.Linear):
                nn.init.kaiming_normal_(m.weight, mode='fan_out', nonlinearity='relu')
                if m.bias is not None:
                    nn.init.constant_(m.bias, 0)
            elif isinstance(m, nn.BatchNorm1d):
                nn.init.constant_(m.weight, 1)
                nn.init.constant_(m.bias, 0)

    def forward(self, x):
        x = self.input_bn(x)
        return self.layers(x)

class Solution:
    def solve(self, train_loader, val_loader, metadata: dict = None) -> torch.nn.Module:
        if metadata is None:
            metadata = {}
            
        input_dim = metadata.get("input_dim", 384)
        num_classes = metadata.get("num_classes", 128)
        param_limit = metadata.get("param_limit", 2500000)
        device = metadata.get("device", "cpu")
        
        # Dynamic Width Calculation to maximize capacity within budget
        # Model Parameter Equation P(w):
        # InputBN: 2*in
        # L1: (in+1)*w
        # BN1: 2*w
        # L2: (w+1)*w
        # BN2: 2*w
        # L3: (w+1)*w
        # BN3: 2*w
        # L4: (w+1)*out
        # Total = 2*w^2 + (in + out + 9)*w + (2*in + out)
        
        # Solve for w: 2w^2 + Bw + C <= param_limit
        target_limit = param_limit - 2000  # Safety buffer
        
        a = 2
        b = input_dim + num_classes + 9
        c_val = (2 * input_dim + num_classes) - target_limit
        
        # Quadratic formula positive root
        delta = b**2 - 4*a*c_val
        width = int((-b + math.sqrt(delta)) / (2*a))
        
        # Instantiate Model
        model = ParetoModel(input_dim, num_classes, width).to(device)
        
        # Training Hyperparameters
        epochs = 80
        lr = 0.002
        weight_decay = 0.01
        mixup_alpha = 0.4
        
        optimizer = optim.AdamW(model.parameters(), lr=lr, weight_decay=weight_decay)
        
        # Label Smoothing Cross Entropy
        try:
            criterion = nn.CrossEntropyLoss(label_smoothing=0.1)
        except:
            criterion = nn.CrossEntropyLoss()
            
        scheduler = optim.lr_scheduler.OneCycleLR(
            optimizer,
            max_lr=lr,
            epochs=epochs,
            steps_per_epoch=len(train_loader),
            pct_start=0.3
        )
        
        best_acc = 0.0
        best_model_state = copy.deepcopy(model.state_dict())
        
        for epoch in range(epochs):
            model.train()
            for inputs, targets in train_loader:
                inputs, targets = inputs.to(device), targets.to(device)
                optimizer.zero_grad()
                
                # Mixup Data Augmentation
                if mixup_alpha > 0:
                    lam = np.random.beta(mixup_alpha, mixup_alpha)
                    index = torch.randperm(inputs.size(0)).to(device)
                    mixed_inputs = lam * inputs + (1 - lam) * inputs[index]
                    y_a, y_b = targets, targets[index]
                    
                    outputs = model(mixed_inputs)
                    loss = lam * criterion(outputs, y_a) + (1 - lam) * criterion(outputs, y_b)
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
            
            # Save best model
            if acc >= best_acc:
                best_acc = acc
                best_model_state = copy.deepcopy(model.state_dict())
        
        # Return best performing model
        model.load_state_dict(best_model_state)
        return model