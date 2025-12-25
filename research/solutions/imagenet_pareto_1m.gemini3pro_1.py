import torch
import torch.nn as nn
import torch.optim as optim
import copy
import math

class ParetoModel(nn.Module):
    def __init__(self, input_dim, num_classes, param_limit=1000000):
        super(ParetoModel, self).__init__()
        
        # Dynamically calculate width to maximize capacity within parameter budget
        # Architecture: Stem(Linear+BN) -> Res1(Linear+BN) -> Res2(Linear+BN) -> Head(Linear)
        # Parameter Count Equation:
        # Stem:  (In * W) + W [bias] + (2 * W) [BN] = In*W + 3W
        # Res1:  (W * W) + W [bias] + (2 * W) [BN]  = W^2 + 3W
        # Res2:  (W * W) + W [bias] + (2 * W) [BN]  = W^2 + 3W
        # Head:  (W * Out) + Out [bias]             = W*Out + Out
        # Total: 2*W^2 + (In + Out + 9)*W + Out
        
        # Safety margin
        target_params = param_limit - 5000 
        
        # Solve quadratic equation: 2W^2 + bW + c = 0
        b = input_dim + num_classes + 9
        c = num_classes - target_params
        
        delta = b**2 - 4 * 2 * c
        width_float = (-b + math.sqrt(delta)) / 4
        self.width = int(width_float)
        
        # Define layers
        self.stem = nn.Sequential(
            nn.Linear(input_dim, self.width),
            nn.BatchNorm1d(self.width),
            nn.SiLU(),
            nn.Dropout(0.4)
        )
        
        self.res1 = nn.Sequential(
            nn.Linear(self.width, self.width),
            nn.BatchNorm1d(self.width),
            nn.SiLU(),
            nn.Dropout(0.4)
        )
        
        self.res2 = nn.Sequential(
            nn.Linear(self.width, self.width),
            nn.BatchNorm1d(self.width),
            nn.SiLU(),
            nn.Dropout(0.4)
        )
        
        self.head = nn.Linear(self.width, num_classes)
        
        # Weight initialization
        for m in self.modules():
            if isinstance(m, nn.Linear):
                nn.init.kaiming_normal_(m.weight, mode='fan_out', nonlinearity='relu')
                if m.bias is not None:
                    nn.init.constant_(m.bias, 0)
            elif isinstance(m, nn.BatchNorm1d):
                nn.init.constant_(m.weight, 1)
                nn.init.constant_(m.bias, 0)

    def forward(self, x):
        x = self.stem(x)
        x = x + self.res1(x) # Residual connection
        x = x + self.res2(x) # Residual connection
        return self.head(x)

class Solution:
    def solve(self, train_loader, val_loader, metadata: dict = None) -> torch.nn.Module:
        # Extract metadata
        input_dim = metadata.get("input_dim", 384)
        num_classes = metadata.get("num_classes", 128)
        param_limit = metadata.get("param_limit", 1000000)
        device = metadata.get("device", "cpu")
        
        # Initialize model
        model = ParetoModel(input_dim, num_classes, param_limit).to(device)
        
        # Optimization configuration
        # AdamW with weight decay for regularization on small dataset
        optimizer = optim.AdamW(model.parameters(), lr=1e-3, weight_decay=2e-2)
        
        # Label smoothing prevents overconfidence and improves generalization
        criterion = nn.CrossEntropyLoss(label_smoothing=0.1)
        
        # Training loop
        epochs = 70 
        scheduler = optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=epochs, eta_min=1e-5)
        
        best_acc = 0.0
        best_model_state = copy.deepcopy(model.state_dict())
        
        for epoch in range(epochs):
            model.train()
            for inputs, targets in train_loader:
                inputs, targets = inputs.to(device), targets.to(device)
                
                optimizer.zero_grad()
                
                # Mixup Augmentation
                # Helps heavily with synthetic data and small sample sizes
                if torch.rand(1).item() < 0.6:
                    alpha = 0.4
                    # Beta distribution for mixup interpolation
                    lam = torch.distributions.Beta(alpha, alpha).sample().item()
                    
                    batch_size = inputs.size(0)
                    index = torch.randperm(batch_size).to(device)
                    
                    mixed_inputs = lam * inputs + (1 - lam) * inputs[index]
                    
                    outputs = model(mixed_inputs)
                    loss = lam * criterion(outputs, targets) + (1 - lam) * criterion(outputs, targets[index])
                else:
                    outputs = model(inputs)
                    loss = criterion(outputs, targets)
                
                loss.backward()
                optimizer.step()
            
            scheduler.step()
            
            # Validation logic
            model.eval()
            correct = 0
            total = 0
            with torch.no_grad():
                for inputs, targets in val_loader:
                    inputs, targets = inputs.to(device), targets.to(device)
                    outputs = model(inputs)
                    _, predicted = torch.max(outputs.data, 1)
                    total += targets.size(0)
                    correct += (predicted == targets).sum().item()
            
            acc = correct / total
            
            # Save best model
            if acc >= best_acc:
                best_acc = acc
                best_model_state = copy.deepcopy(model.state_dict())
        
        # Return best performing model
        model.load_state_dict(best_model_state)
        return model
