import torch
import torch.nn as nn
import torch.optim as optim
import numpy as np
import copy

class ParetoNetwork(nn.Module):
    def __init__(self, input_dim, hidden_dim, num_classes, mean, std):
        super().__init__()
        # Register normalization buffers
        self.register_buffer('mean', mean)
        self.register_buffer('std', std)
        
        # Block 1: Projection + Norm + Act + Dropout
        self.block1 = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.BatchNorm1d(hidden_dim),
            nn.GELU(),
            nn.Dropout(0.3)
        )
        
        # Block 2: Hidden + Norm + Act + Dropout (Residual Candidate)
        self.block2 = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim),
            nn.BatchNorm1d(hidden_dim),
            nn.GELU(),
            nn.Dropout(0.3)
        )
        
        # Output Head
        self.head = nn.Linear(hidden_dim, num_classes)
        
    def forward(self, x):
        # Normalize inputs
        x = (x - self.mean) / self.std
        
        # Forward pass with residual connection on the hidden block
        x = self.block1(x)
        identity = x
        x = self.block2(x)
        x = x + identity
        
        return self.head(x)

class Solution:
    def solve(self, train_loader, val_loader, metadata: dict = None) -> torch.nn.Module:
        # Extract metadata
        input_dim = metadata.get("input_dim", 384)
        num_classes = metadata.get("num_classes", 128)
        device = metadata.get("device", "cpu")
        
        # 1. Calculate Dataset Statistics for Normalization
        # Load all training data to compute precise mean/std
        all_x = []
        for x, _ in train_loader:
            all_x.append(x)
        all_x = torch.cat(all_x, dim=0)
        mean = all_x.mean(dim=0)
        std = all_x.std(dim=0) + 1e-6 # Avoid division by zero
        
        # 2. Dynamic Architecture Sizing
        # Calculate maximum hidden dimension 'h' that fits within parameter budget
        # Model structure params:
        # L1: input*h + h
        # BN1: 2*h
        # L2: h*h + h
        # BN2: 2*h
        # Head: h*output + output
        # Total = h^2 + h*(input + output + 6) + output
        
        limit = 995000 # Target slightly under 1M to be safe (Constraint is 1,000,000)
        a = 1
        b = input_dim + num_classes + 6
        c = num_classes - limit
        
        # Quadratic formula: h = (-b + sqrt(b^2 - 4ac)) / 2a
        delta = b**2 - 4*a*c
        hidden_dim = int((-b + delta**0.5) / (2*a))
        
        # Ensure even dimension for potential memory alignment benefits
        if hidden_dim % 2 != 0:
            hidden_dim -= 1
            
        # 3. Initialize Model
        model = ParetoNetwork(input_dim, hidden_dim, num_classes, mean, std).to(device)
        
        # 4. Training Setup
        optimizer = optim.AdamW(model.parameters(), lr=1e-3, weight_decay=1e-2)
        epochs = 60
        scheduler = optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=epochs)
        criterion = nn.CrossEntropyLoss()
        
        best_acc = 0.0
        best_model_state = copy.deepcopy(model.state_dict())
        
        # 5. Training Loop
        for epoch in range(epochs):
            model.train()
            for x, y in train_loader:
                x, y = x.to(device), y.to(device)
                
                # Mixup Augmentation
                alpha = 0.4
                if alpha > 0:
                    lam = np.random.beta(alpha, alpha)
                else:
                    lam = 1
                
                batch_size = x.size(0)
                index = torch.randperm(batch_size).to(device)
                
                mixed_x = lam * x + (1 - lam) * x[index]
                y_a, y_b = y, y[index]
                
                optimizer.zero_grad()
                out = model(mixed_x)
                loss = lam * criterion(out, y_a) + (1 - lam) * criterion(out, y_b)
                
                loss.backward()
                optimizer.step()
            
            scheduler.step()
            
            # Validation
            val_acc = self.evaluate(model, val_loader, device)
            
            # Checkpoint best model
            if val_acc > best_acc:
                best_acc = val_acc
                best_model_state = copy.deepcopy(model.state_dict())
        
        # Restore best model
        model.load_state_dict(best_model_state)
        return model

    def evaluate(self, model, loader, device):
        model.eval()
        correct = 0
        total = 0
        with torch.no_grad():
            for x, y in loader:
                x, y = x.to(device), y.to(device)
                out = model(x)
                pred = out.argmax(dim=1)
                correct += (pred == y).sum().item()
                total += y.size(0)
        return correct / total if total > 0 else 0