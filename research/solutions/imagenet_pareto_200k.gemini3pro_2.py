import torch
import torch.nn as nn
import torch.optim as optim
import math
import numpy as np

class DynamicMLP(nn.Module):
    def __init__(self, input_dim, num_classes, param_limit=200000):
        super().__init__()
        
        # Architecture:
        # BN(I) -> [Linear(I, H) -> BN(H) -> GELU -> Dropout] 
        #       -> [Linear(H, H) -> BN(H) -> GELU -> Dropout] 
        #       -> Linear(H, O)
        
        # Parameter Count Calculation:
        # BN(I): 2*I
        # L1: I*H + H
        # BN1: 2*H
        # L2: H*H + H
        # BN2: 2*H
        # L3: H*O + O
        # Total P = H^2 + H*(I + O + 6) + (2*I + O)
        
        # Solving for H to satisfy P <= param_limit
        a = 1.0
        b = float(input_dim + num_classes + 6)
        c_val = float(2 * input_dim + num_classes)
        c = c_val - param_limit
        
        # Quadratic formula: (-b + sqrt(b^2 - 4ac)) / 2a
        delta = b**2 - 4*a*c
        if delta < 0:
            hidden_dim = 16 # Fallback for extremely strict limits
        else:
            hidden_dim = int(math.floor((-b + math.sqrt(delta)) / (2*a)))
        
        # Ensure a reasonable minimum dimension
        self.hidden_dim = max(hidden_dim, 32)
        
        self.bn_input = nn.BatchNorm1d(input_dim)
        
        self.layers = nn.Sequential(
            nn.Linear(input_dim, self.hidden_dim),
            nn.BatchNorm1d(self.hidden_dim),
            nn.GELU(),
            nn.Dropout(0.3),
            
            nn.Linear(self.hidden_dim, self.hidden_dim),
            nn.BatchNorm1d(self.hidden_dim),
            nn.GELU(),
            nn.Dropout(0.3),
            
            nn.Linear(self.hidden_dim, num_classes)
        )
        
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
        x = self.bn_input(x)
        return self.layers(x)

class Solution:
    def solve(self, train_loader, val_loader, metadata: dict = None) -> torch.nn.Module:
        if metadata is None:
            metadata = {}
            
        input_dim = metadata.get("input_dim", 384)
        num_classes = metadata.get("num_classes", 128)
        param_limit = metadata.get("param_limit", 200000)
        device = metadata.get("device", "cpu")
        
        # Initialize model tailored to the parameter limit
        model = DynamicMLP(input_dim, num_classes, param_limit)
        model = model.to(device)
        
        # Optimization Setup
        # Using AdamW with weight decay is crucial for regularization on small datasets
        optimizer = optim.AdamW(model.parameters(), lr=1e-3, weight_decay=0.02)
        
        # Label smoothing to prevent overconfidence/overfitting
        criterion = nn.CrossEntropyLoss(label_smoothing=0.1)
        
        epochs = 60
        steps_per_epoch = len(train_loader)
        
        # OneCycleLR allows fast convergence
        scheduler = optim.lr_scheduler.OneCycleLR(
            optimizer,
            max_lr=5e-3,
            epochs=epochs,
            steps_per_epoch=steps_per_epoch,
            pct_start=0.3,
            div_factor=25.0,
            final_div_factor=1000.0
        )
        
        best_val_acc = 0.0
        best_model_state = None
        patience = 15
        no_improve_epochs = 0
        
        # Training Loop
        for epoch in range(epochs):
            model.train()
            
            for inputs, targets in train_loader:
                inputs, targets = inputs.to(device), targets.to(device)
                
                # Mixup Augmentation
                # Apply mixup with 50% probability
                if np.random.random() < 0.5 and inputs.size(0) > 1:
                    alpha = 0.4
                    lam = np.random.beta(alpha, alpha)
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
                torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
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
            
            val_acc = correct / total if total > 0 else 0
            
            if val_acc > best_val_acc:
                best_val_acc = val_acc
                best_model_state = {k: v.cpu() for k, v in model.state_dict().items()}
                no_improve_epochs = 0
            else:
                no_improve_epochs += 1
                if no_improve_epochs >= patience and epoch > 20:
                    break
        
        # Load best weights
        if best_model_state is not None:
            model.load_state_dict(best_model_state)
            
        return model
