import torch
import torch.nn as nn
import torch.optim as optim
import math
import numpy as np

class Solution:
    def solve(self, train_loader, val_loader, metadata: dict = None) -> torch.nn.Module:
        """
        Solves the ImageNet Pareto Optimization problem by training a parameter-constrained model.
        """
        # 1. Extract Metadata & Configuration
        input_dim = metadata.get("input_dim", 384)
        num_classes = metadata.get("num_classes", 128)
        param_limit = metadata.get("param_limit", 500000)
        device = metadata.get("device", "cpu")
        
        # 2. Dynamic Architecture Calculation
        # We design a 3-layer MLP with Batch Norm and Dropout.
        # Architecture: 
        #   Input -> BN(In) -> Linear(In, W) -> BN(W) -> SiLU -> Dropout 
        #         -> Linear(W, W//2) -> BN(W//2) -> SiLU -> Dropout 
        #         -> Linear(W//2, Out)
        
        # Parameter Count Formula:
        # Input BN: 2 * In
        # L1: In*W + W (bias) + 2*W (BN) = W(In + 3)
        # L2: W*(W/2) + W/2 (bias) + 2*(W/2) (BN) = 0.5*W^2 + 1.5*W
        # L3: (W/2)*Out + Out (bias) = 0.5*Out*W + Out
        # Total = 0.5*W^2 + W(In + 4.5 + 0.5*Out) + (Out + 2*In)
        
        # Solve quadratic equation ax^2 + bx + c = 0 for W (width)
        # target params slightly lower than limit for safety buffer
        target = param_limit - 2500 
        
        a = 0.5
        b = input_dim + 4.5 + 0.5 * num_classes
        c_const = num_classes + 2 * input_dim - target
        
        # Quadratic formula: x = (-b + sqrt(b^2 - 4ac)) / 2a
        # Since 2a = 1, x = -b + sqrt(b^2 - 2*c_const)
        delta = b**2 - 2 * c_const
        w_float = -b + math.sqrt(delta)
        width = int(w_float)
        
        # Ensure width is even for clean division by 2
        if width % 2 != 0:
            width -= 1
            
        # 3. Model Definition
        class ParetoNet(nn.Module):
            def __init__(self, in_d, w, out_d):
                super().__init__()
                self.input_bn = nn.BatchNorm1d(in_d)
                self.features = nn.Sequential(
                    nn.Linear(in_d, w),
                    nn.BatchNorm1d(w),
                    nn.SiLU(),
                    nn.Dropout(p=0.4),
                    
                    nn.Linear(w, w // 2),
                    nn.BatchNorm1d(w // 2),
                    nn.SiLU(),
                    nn.Dropout(p=0.4),
                    
                    nn.Linear(w // 2, out_d)
                )
                
            def forward(self, x):
                x = self.input_bn(x)
                return self.features(x)

        model = ParetoNet(input_dim, width, num_classes).to(device)
        
        # 4. Training Setup
        # Use Label Smoothing to prevent overfitting on small dataset
        criterion = nn.CrossEntropyLoss(label_smoothing=0.15)
        
        # AdamW with weight decay for regularization
        optimizer = optim.AdamW(model.parameters(), lr=1e-3, weight_decay=0.05)
        
        epochs = 60
        # OneCycleLR for super-convergence
        scheduler = optim.lr_scheduler.OneCycleLR(
            optimizer,
            max_lr=1e-3,
            epochs=epochs,
            steps_per_epoch=len(train_loader),
            pct_start=0.2,
            div_factor=25.0,
            final_div_factor=1000.0
        )
        
        best_acc = -1.0
        best_state = None
        
        # Mixup configuration
        mixup_alpha = 0.4
        mixup_prob = 0.7
        
        # 5. Training Loop
        for epoch in range(epochs):
            model.train()
            for inputs, targets in train_loader:
                inputs, targets = inputs.to(device), targets.to(device)
                
                # Apply Mixup Augmentation
                if np.random.random() < mixup_prob:
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
            
            # 6. Validation
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
            
            acc = correct / total
            
            # Save best model
            if acc > best_acc:
                best_acc = acc
                # Save state to CPU to avoid memory issues and persist across device moves
                best_state = {k: v.cpu() for k, v in model.state_dict().items()}
        
        # 7. Restore Best Model
        if best_state is not None:
            model.load_state_dict(best_state)
            model.to(device)
            
        return model