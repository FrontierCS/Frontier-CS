import torch
import torch.nn as nn
import torch.optim as optim
import numpy as np
import copy

class ResidualBlock(nn.Module):
    def __init__(self, dim, dropout=0.2):
        super().__init__()
        self.linear1 = nn.Linear(dim, dim)
        self.bn1 = nn.BatchNorm1d(dim)
        self.act1 = nn.ReLU()
        self.drop1 = nn.Dropout(dropout)
        
        self.linear2 = nn.Linear(dim, dim)
        self.bn2 = nn.BatchNorm1d(dim)
        self.act2 = nn.ReLU()
        self.drop2 = nn.Dropout(dropout)

    def forward(self, x):
        identity = x
        out = self.linear1(x)
        out = self.bn1(out)
        out = self.act1(out)
        out = self.drop1(out)
        
        out = self.linear2(out)
        out = self.bn2(out)
        
        out += identity
        out = self.act2(out)
        out = self.drop2(out)
        return out

class ResMLP(nn.Module):
    def __init__(self, input_dim, num_classes, hidden_dim=740, num_blocks=4, dropout=0.2):
        super().__init__()
        # Initial normalization of raw feature inputs
        self.input_bn = nn.BatchNorm1d(input_dim)
        
        # Projection to hidden dimension
        self.proj = nn.Linear(input_dim, hidden_dim)
        self.proj_bn = nn.BatchNorm1d(hidden_dim)
        self.proj_act = nn.ReLU()
        self.proj_drop = nn.Dropout(dropout)
        
        # Deep Residual Blocks
        self.blocks = nn.ModuleList([
            ResidualBlock(hidden_dim, dropout) for _ in range(num_blocks)
        ])
        
        # Classification Head
        self.head = nn.Linear(hidden_dim, num_classes)

    def forward(self, x):
        x = self.input_bn(x)
        x = self.proj(x)
        x = self.proj_bn(x)
        x = self.proj_act(x)
        x = self.proj_drop(x)
        
        for block in self.blocks:
            x = block(x)
            
        x = self.head(x)
        return x

class Solution:
    def solve(self, train_loader, val_loader, metadata: dict = None) -> torch.nn.Module:
        # Extract metadata
        input_dim = metadata.get("input_dim", 384)
        num_classes = metadata.get("num_classes", 128)
        device = metadata.get("device", "cpu")
        param_limit = metadata.get("param_limit", 5000000)
        
        # Hyperparameters
        # Architecture tuned to stay just under 5M params with width 740 and 4 blocks
        HIDDEN_DIM = 740 
        NUM_BLOCKS = 4
        DROPOUT = 0.2
        EPOCHS = 70
        LR = 1e-3
        WEIGHT_DECAY = 1e-2
        LABEL_SMOOTHING = 0.1
        
        # Initialize model
        model = ResMLP(input_dim, num_classes, HIDDEN_DIM, NUM_BLOCKS, DROPOUT).to(device)
        
        # Check parameter constraint and adjust if necessary (safety fallback)
        param_count = sum(p.numel() for p in model.parameters() if p.requires_grad)
        if param_count > param_limit:
            # Fallback to smaller width if calculation fails
            model = ResMLP(input_dim, num_classes, hidden_dim=600, num_blocks=NUM_BLOCKS, dropout=DROPOUT).to(device)
            
        # Optimization setup
        optimizer = optim.AdamW(model.parameters(), lr=LR, weight_decay=WEIGHT_DECAY)
        scheduler = optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=EPOCHS)
        criterion = nn.CrossEntropyLoss(label_smoothing=LABEL_SMOOTHING)
        
        best_acc = 0.0
        best_model_state = copy.deepcopy(model.state_dict())
        
        # Training loop
        for epoch in range(EPOCHS):
            model.train()
            for inputs, targets in train_loader:
                inputs, targets = inputs.to(device), targets.to(device)
                
                optimizer.zero_grad()
                
                # Mixup Augmentation (critical for small dataset generalization)
                if np.random.random() < 0.7:  # 70% chance to apply mixup
                    lam = np.random.beta(0.4, 0.4)
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
                    _, predicted = torch.max(outputs.data, 1)
                    total += targets.size(0)
                    correct += (predicted == targets).sum().item()
            
            val_acc = correct / total
            
            # Checkpoint best model
            if val_acc >= best_acc:
                best_acc = val_acc
                best_model_state = copy.deepcopy(model.state_dict())
        
        # Return best model
        model.load_state_dict(best_model_state)
        return model
