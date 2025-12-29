import torch
import torch.nn as nn
import torch.optim as optim
import numpy as np
import math

class DynamicModel(nn.Module):
    def __init__(self, input_dim, hidden_dim, num_classes, mean, std):
        super().__init__()
        self.hidden_dim = hidden_dim
        self.register_buffer('mean', mean)
        self.register_buffer('std', std)
        
        self.net = nn.Sequential(
            nn.Linear(input_dim, hidden_dim, bias=False),
            nn.BatchNorm1d(hidden_dim),
            nn.SiLU(),
            nn.Dropout(0.3),
            nn.Linear(hidden_dim, hidden_dim, bias=False),
            nn.BatchNorm1d(hidden_dim),
            nn.SiLU(),
            nn.Dropout(0.3),
            nn.Linear(hidden_dim, num_classes)
        )
        
    def forward(self, x):
        # Input normalization
        x = (x - self.mean) / (self.std + 1e-6)
        return self.net(x)

class Solution:
    def solve(self, train_loader, val_loader, metadata: dict = None) -> torch.nn.Module:
        # Handle metadata defaults
        if metadata is None:
            metadata = {}
        input_dim = metadata.get("input_dim", 384)
        num_classes = metadata.get("num_classes", 128)
        param_limit = metadata.get("param_limit", 200000)
        device = metadata.get("device", "cpu")
        
        # Calculate maximum hidden dimension to stay within parameter budget
        # Architecture:
        # L1: Linear(in, h, bias=False) + BN(h)
        # L2: Linear(h, h, bias=False) + BN(h)
        # L3: Linear(h, out, bias=True)
        # Params = h*in + 2h + h*h + 2h + h*out + out
        #        = h^2 + h(in + out + 4) + out
        # We solve: h^2 + b*h + c = 0 for h
        
        a = 1
        b = input_dim + num_classes + 4
        c = num_classes - param_limit
        
        delta = b*b - 4*a*c
        if delta < 0:
            hidden_dim = 64 # Fallback
        else:
            h_float = (-b + math.sqrt(delta)) / (2*a)
            hidden_dim = int(math.floor(h_float)) - 1 # -1 for safety margin
            
        # Compute dataset statistics for normalization
        all_x = []
        for x, _ in train_loader:
            all_x.append(x)
            
        if all_x:
            all_x = torch.cat(all_x, dim=0)
            mean = all_x.mean(dim=0)
            std = all_x.std(dim=0)
        else:
            mean = torch.zeros(input_dim)
            std = torch.ones(input_dim)
            
        # Training configuration
        num_candidates = 3  # Train multiple candidates and pick best
        epochs = 50
        best_overall_acc = -1.0
        best_overall_model = None
        
        for run in range(num_candidates):
            model = DynamicModel(input_dim, hidden_dim, num_classes, mean, std).to(device)
            
            optimizer = optim.AdamW(model.parameters(), lr=1e-3, weight_decay=1e-3)
            scheduler = optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=epochs)
            criterion = nn.CrossEntropyLoss(label_smoothing=0.1)
            
            best_run_acc = 0.0
            best_run_state = None
            
            for epoch in range(epochs):
                model.train()
                for x, y in train_loader:
                    x, y = x.to(device), y.to(device)
                    
                    # Mixup augmentation
                    alpha = 0.4
                    lam = np.random.beta(alpha, alpha)
                    idx = torch.randperm(x.size(0)).to(device)
                    mixed_x = lam * x + (1 - lam) * x[idx]
                    y_a, y_b = y, y[idx]
                    
                    optimizer.zero_grad()
                    outputs = model(mixed_x)
                    loss = lam * criterion(outputs, y_a) + (1 - lam) * criterion(outputs, y_b)
                    loss.backward()
                    optimizer.step()
                
                scheduler.step()
                
                # Validation
                model.eval()
                correct = 0
                total = 0
                with torch.no_grad():
                    for x, y in val_loader:
                        x, y = x.to(device), y.to(device)
                        outputs = model(x)
                        pred = outputs.argmax(dim=1)
                        correct += (pred == y).sum().item()
                        total += y.size(0)
                
                acc = correct / total if total > 0 else 0
                
                if acc > best_run_acc:
                    best_run_acc = acc
                    best_run_state = model.state_dict()
            
            # Select best model across runs
            if best_run_acc > best_overall_acc:
                best_overall_acc = best_run_acc
                # Create fresh instance to avoid reference issues
                best_overall_model = DynamicModel(input_dim, hidden_dim, num_classes, mean, std).to(device)
                best_overall_model.load_state_dict(best_run_state)
        
        return best_overall_model