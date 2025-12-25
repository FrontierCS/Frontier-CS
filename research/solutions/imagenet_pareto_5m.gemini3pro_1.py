import torch
import torch.nn as nn
import torch.optim as optim
import numpy as np

class ResidualBlock(nn.Module):
    def __init__(self, dim, dropout=0.2):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(dim, dim),
            nn.BatchNorm1d(dim),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(dim, dim),
            nn.BatchNorm1d(dim),
            nn.GELU(),
            nn.Dropout(dropout)
        )

    def forward(self, x):
        return x + self.net(x)

class SubModel(nn.Module):
    def __init__(self, input_dim, num_classes, hidden_dim=512, dropout=0.2):
        super().__init__()
        self.stem = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.BatchNorm1d(hidden_dim),
            nn.GELU(),
            nn.Dropout(dropout)
        )
        self.blocks = nn.Sequential(
            ResidualBlock(hidden_dim, dropout),
            ResidualBlock(hidden_dim, dropout)
        )
        self.head_pre = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim),
            nn.BatchNorm1d(hidden_dim),
            nn.GELU(),
            nn.Dropout(dropout)
        )
        self.head = nn.Linear(hidden_dim, num_classes)

    def forward(self, x):
        x = self.stem(x)
        x = self.blocks(x)
        x = self.head_pre(x)
        return self.head(x)

class Ensemble(nn.Module):
    def __init__(self, models):
        super().__init__()
        self.models = nn.ModuleList(models)
    
    def forward(self, x):
        outputs = [m(x) for m in self.models]
        return torch.stack(outputs).mean(dim=0)

class Solution:
    def solve(self, train_loader, val_loader, metadata: dict = None) -> torch.nn.Module:
        input_dim = metadata["input_dim"]
        num_classes = metadata["num_classes"]
        device = metadata.get("device", "cpu")
        
        # Architecture parameters
        hidden_dim = 512
        dropout = 0.2
        
        # Calculate parameter count for a single sub-model to determine ensemble size
        dummy_model = SubModel(input_dim, num_classes, hidden_dim, dropout)
        param_count_per_model = sum(p.numel() for p in dummy_model.parameters() if p.requires_grad)
        
        # Param budget is 5,000,000. Leave a small safety margin.
        max_params = 4990000 
        num_models = int(max_params // param_count_per_model)
        
        # Ensure at least one model if specs are weird, though budget violation would occur
        if num_models < 1:
            num_models = 1
            
        trained_models = []
        
        # Training Hyperparameters
        epochs = 85
        lr = 1e-3
        weight_decay = 2e-2
        mixup_prob = 0.6
        mixup_alpha = 0.4
        
        for i in range(num_models):
            model = SubModel(input_dim, num_classes, hidden_dim, dropout).to(device)
            model.train()
            
            optimizer = optim.AdamW(model.parameters(), lr=lr, weight_decay=weight_decay)
            
            total_steps = epochs * len(train_loader)
            scheduler = optim.lr_scheduler.OneCycleLR(
                optimizer,
                max_lr=lr,
                total_steps=total_steps,
                pct_start=0.3
            )
            
            criterion = nn.CrossEntropyLoss(label_smoothing=0.1)
            
            for epoch in range(epochs):
                for inputs, targets in train_loader:
                    inputs, targets = inputs.to(device), targets.to(device)
                    
                    # Mixup Augmentation
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
            
            model.eval()
            trained_models.append(model)
            
        return Ensemble(trained_models)
