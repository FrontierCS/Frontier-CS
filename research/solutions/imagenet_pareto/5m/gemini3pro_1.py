import torch
import torch.nn as nn
import torch.optim as optim
import numpy as np
import copy
import random

class ResBlock(nn.Module):
    def __init__(self, dim, dropout=0.0):
        super().__init__()
        self.norm = nn.LayerNorm(dim)
        self.fc1 = nn.Linear(dim, dim)
        self.act = nn.GELU()
        self.drop1 = nn.Dropout(dropout)
        self.fc2 = nn.Linear(dim, dim)
        self.drop2 = nn.Dropout(dropout)

    def forward(self, x):
        input = x
        x = self.norm(x)
        x = self.fc1(x)
        x = self.act(x)
        x = self.drop1(x)
        x = self.fc2(x)
        x = self.drop2(x)
        return input + x

class Model(nn.Module):
    def __init__(self, input_dim, num_classes, width, dropout=0.0):
        super().__init__()
        self.stem = nn.Sequential(
            nn.LayerNorm(input_dim),
            nn.Linear(input_dim, width),
            nn.GELU(),
            nn.Dropout(dropout)
        )
        self.layer1 = ResBlock(width, dropout)
        self.layer2 = ResBlock(width, dropout)
        self.head = nn.Sequential(
            nn.LayerNorm(width),
            nn.Linear(width, num_classes)
        )

    def forward(self, x):
        x = self.stem(x)
        x = self.layer1(x)
        x = self.layer2(x)
        return self.head(x)

class Solution:
    def solve(self, train_loader, val_loader, metadata: dict = None) -> torch.nn.Module:
        metadata = metadata or {}
        
        # Set seeds for reproducibility
        seed = 42
        random.seed(seed)
        np.random.seed(seed)
        torch.manual_seed(seed)
        
        input_dim = metadata.get("input_dim", 384)
        num_classes = metadata.get("num_classes", 128)
        param_limit = metadata.get("param_limit", 5000000)
        device = metadata.get("device", "cpu")
        
        # Dynamically determine the maximum width that fits within the parameter budget
        # We start with a good estimate and decrease if necessary
        width = 1056 
        while True:
            # Check parameter count with dummy model
            m = Model(input_dim, num_classes, width, dropout=0.0)
            p_count = sum(p.numel() for p in m.parameters() if p.requires_grad)
            
            # Leave a small buffer to be safe
            if p_count <= param_limit - 5000:
                break
            width -= 8  # Decrease width in steps
            
        # Instantiate the final model with regularization
        # High dropout is used because the dataset is small (2048 samples) relative to params (~5M)
        model = Model(input_dim, num_classes, width, dropout=0.5).to(device)
        
        # Optimization setup
        # AdamW with weight decay for regularization
        optimizer = optim.AdamW(model.parameters(), lr=1e-3, weight_decay=0.05)
        
        # Training configuration
        epochs = 120
        steps_per_epoch = len(train_loader)
        
        # OneCycleLR for efficient convergence
        scheduler = optim.lr_scheduler.OneCycleLR(
            optimizer, 
            max_lr=1e-3, 
            epochs=epochs, 
            steps_per_epoch=steps_per_epoch,
            pct_start=0.3
        )
        
        # Label smoothing helps with generalization on small datasets
        criterion = nn.CrossEntropyLoss(label_smoothing=0.1)
        
        best_acc = 0.0
        best_model_state = copy.deepcopy(model.state_dict())
        
        # Training loop
        for epoch in range(epochs):
            model.train()
            for inputs, targets in train_loader:
                inputs, targets = inputs.to(device), targets.to(device)
                
                # Mixup augmentation
                alpha = 0.4
                lam = np.random.beta(alpha, alpha) if alpha > 0 else 1.0
                
                batch_size = inputs.size(0)
                index = torch.randperm(batch_size).to(device)
                
                mixed_inputs = lam * inputs + (1 - lam) * inputs[index, :]
                y_a, y_b = targets, targets[index]
                
                optimizer.zero_grad()
                outputs = model(mixed_inputs)
                loss = lam * criterion(outputs, y_a) + (1 - lam) * criterion(outputs, y_b)
                
                loss.backward()
                nn.utils.clip_grad_norm_(model.parameters(), 1.0)
                optimizer.step()
                scheduler.step()
            
            # Validation loop
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
            
            acc = correct / total if total > 0 else 0
            
            # Save best model
            if acc >= best_acc:
                best_acc = acc
                best_model_state = copy.deepcopy(model.state_dict())
        
        # Return the best performing model
        model.load_state_dict(best_model_state)
        return model