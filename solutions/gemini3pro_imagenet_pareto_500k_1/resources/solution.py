import torch
import torch.nn as nn
import torch.optim as optim
import numpy as np
import copy

class ResBlock(nn.Module):
    def __init__(self, dim, dropout=0.0):
        super().__init__()
        self.block = nn.Sequential(
            nn.Linear(dim, dim),
            nn.BatchNorm1d(dim),
            nn.GELU(),
            nn.Dropout(dropout)
        )

    def forward(self, x):
        return x + self.block(x)

class ParetoModel(nn.Module):
    def __init__(self, input_dim, num_classes, hidden_dim=265, num_blocks=5, dropout=0.3):
        super().__init__()
        self.input_proj = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.BatchNorm1d(hidden_dim),
            nn.GELU(),
            nn.Dropout(dropout/2)
        )
        
        self.blocks = nn.ModuleList([
            ResBlock(hidden_dim, dropout) for _ in range(num_blocks)
        ])
        
        self.norm = nn.BatchNorm1d(hidden_dim)
        self.head = nn.Linear(hidden_dim, num_classes)

    def forward(self, x):
        x = self.input_proj(x)
        for block in self.blocks:
            x = block(x)
        x = self.norm(x)
        return self.head(x)

class Solution:
    def solve(self, train_loader, val_loader, metadata: dict = None) -> torch.nn.Module:
        input_dim = metadata["input_dim"]
        num_classes = metadata["num_classes"]
        device = metadata.get("device", "cpu")
        
        # Configuration designed to stay just under 500k parameters
        # hidden_dim 265 with 5 blocks results in approx 492k parameters
        hidden_dim = 265
        num_blocks = 5
        dropout = 0.3
        epochs = 80
        lr = 0.003
        weight_decay = 0.02
        
        model = ParetoModel(input_dim, num_classes, hidden_dim, num_blocks, dropout).to(device)
        
        # Constraint Enforcement: Ensure strictly < 500,000 parameters
        param_limit = 500000
        current_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
        
        while current_params > param_limit:
            hidden_dim -= 2
            model = ParetoModel(input_dim, num_classes, hidden_dim, num_blocks, dropout).to(device)
            current_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
            
        optimizer = optim.AdamW(model.parameters(), lr=lr, weight_decay=weight_decay)
        criterion = nn.CrossEntropyLoss(label_smoothing=0.1)
        
        scheduler = optim.lr_scheduler.OneCycleLR(
            optimizer,
            max_lr=lr,
            epochs=epochs,
            steps_per_epoch=len(train_loader),
            pct_start=0.3,
            div_factor=25.0,
            final_div_factor=1000.0
        )
        
        best_acc = -1.0
        best_model_state = copy.deepcopy(model.state_dict())
        
        for epoch in range(epochs):
            model.train()
            for inputs, targets in train_loader:
                inputs, targets = inputs.to(device), targets.to(device)
                
                # Mixup Augmentation
                if np.random.random() < 0.6:
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
            if acc > best_acc:
                best_acc = acc
                best_model_state = copy.deepcopy(model.state_dict())
        
        model.load_state_dict(best_model_state)
        return model
