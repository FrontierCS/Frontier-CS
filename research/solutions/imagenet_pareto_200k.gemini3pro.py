import torch
import torch.nn as nn
import torch.optim as optim
import numpy as np
import copy

class ResidualBlock(nn.Module):
    def __init__(self, hidden_dim, dropout_p=0.3):
        super().__init__()
        self.block = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim, bias=False),
            nn.BatchNorm1d(hidden_dim),
            nn.ReLU(),
            nn.Dropout(dropout_p),
            nn.Linear(hidden_dim, hidden_dim, bias=False),
            nn.BatchNorm1d(hidden_dim),
            nn.Dropout(dropout_p)
        )
        self.relu = nn.ReLU()

    def forward(self, x):
        return self.relu(x + self.block(x))

class OptimizedModel(nn.Module):
    def __init__(self, input_dim, num_classes, hidden_dim, num_blocks, dropout_p=0.2):
        super().__init__()
        # Initial normalization of inputs
        self.input_bn = nn.BatchNorm1d(input_dim)
        
        # Project to hidden dimension
        self.entry = nn.Sequential(
            nn.Linear(input_dim, hidden_dim, bias=False),
            nn.BatchNorm1d(hidden_dim),
            nn.ReLU(),
            nn.Dropout(dropout_p)
        )
        
        # Residual backbone
        layers = []
        for _ in range(num_blocks):
            layers.append(ResidualBlock(hidden_dim, dropout_p=0.3))
        self.blocks = nn.Sequential(*layers)
        
        # Classifier
        self.classifier = nn.Linear(hidden_dim, num_classes)

    def forward(self, x):
        x = self.input_bn(x)
        x = self.entry(x)
        x = self.blocks(x)
        return self.classifier(x)

class Solution:
    def solve(self, train_loader, val_loader, metadata: dict = None) -> torch.nn.Module:
        if metadata is None:
            metadata = {}
            
        input_dim = metadata.get("input_dim", 384)
        num_classes = metadata.get("num_classes", 128)
        param_limit = metadata.get("param_limit", 200000)
        device = metadata.get("device", "cpu")
        
        # 1. Architecture Optimization
        # We perform a greedy search to maximize model capacity (width and depth)
        # while strictly adhering to the parameter constraint.
        
        safety_margin = 100  # Ensure we are strictly under the limit
        effective_limit = param_limit - safety_margin
        
        best_config = (64, 1) # Fallback configuration
        
        # Iterate over preferred widths (descending)
        for width in [128, 112, 96, 64]:
            # Fixed costs:
            # 1. Input BN: 2 * input_dim
            # 2. Entry Proj: input_dim * width (weights) + 2 * width (BN params)
            # 3. Classifier: width * num_classes (weights) + num_classes (bias)
            cost_fixed = (2 * input_dim) + \
                         (input_dim * width + 2 * width) + \
                         (width * num_classes + num_classes)
            
            if cost_fixed >= effective_limit:
                continue
                
            # Block cost (ResidualBlock):
            # 2 x Linear(w, w, bias=False) -> 2 * w^2
            # 2 x BatchNorm(w) -> 2 * (2 * w) = 4 * w
            cost_per_block = 2 * (width * width) + 4 * width
            
            remaining_budget = effective_limit - cost_fixed
            max_blocks = int(remaining_budget // cost_per_block)
            
            # Prefer configurations with at least 2 blocks
            if max_blocks >= 2:
                best_config = (width, max_blocks)
                break
        
        hidden_dim, num_blocks = best_config
        
        # Double check exact parameter count
        def create_model():
            return OptimizedModel(input_dim, num_classes, hidden_dim, num_blocks)
            
        temp_model = create_model()
        current_params = sum(p.numel() for p in temp_model.parameters() if p.requires_grad)
        
        # Reduction loop if calculation was slightly off or margin insufficient
        while current_params > param_limit:
            num_blocks -= 1
            if num_blocks < 1:
                hidden_dim = 64 # Emergency fallback
                num_blocks = 1
            temp_model = create_model()
            current_params = sum(p.numel() for p in temp_model.parameters() if p.requires_grad)
            
        # 2. Training with Restarts
        # We train multiple models and select the best one based on validation accuracy
        # to handle the high variance from small dataset size.
        
        num_restarts = 3
        epochs = 60
        best_val_acc = -1.0
        best_state_dict = None
        
        for run in range(num_restarts):
            model = create_model().to(device)
            
            # Regularization is key for this small dataset
            optimizer = optim.AdamW(model.parameters(), lr=0.001, weight_decay=0.005)
            scheduler = optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=epochs)
            # Label smoothing helps with synthetic clusters
            criterion = nn.CrossEntropyLoss(label_smoothing=0.1)
            
            for epoch in range(epochs):
                model.train()
                for inputs, targets in train_loader:
                    inputs, targets = inputs.to(device), targets.to(device)
                    
                    # Mixup Augmentation
                    # Helps smooth decision boundaries for feature vectors
                    if np.random.random() < 0.4:
                        lam = np.random.beta(0.4, 0.4)
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
            
            val_acc = correct / total if total > 0 else 0.0
            
            if val_acc > best_val_acc:
                best_val_acc = val_acc
                best_state_dict = copy.deepcopy(model.state_dict())
        
        # Return best model
        final_model = create_model().to(device)
        if best_state_dict is not None:
            final_model.load_state_dict(best_state_dict)
            
        return final_model