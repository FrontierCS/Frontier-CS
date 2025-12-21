import torch
import torch.nn as nn
import torch.optim as optim
import math
import copy

class ResBlock(nn.Module):
    def __init__(self, dim, dropout=0.1):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(dim, dim),
            nn.BatchNorm1d(dim),
            nn.ReLU(),
            nn.Dropout(dropout)
        )
        
    def forward(self, x):
        return x + self.net(x)

class ParetoNet(nn.Module):
    def __init__(self, input_dim, hidden_dim, num_classes):
        super().__init__()
        # Stem layer
        self.stem = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.BatchNorm1d(hidden_dim),
            nn.ReLU(),
            nn.Dropout(0.1)
        )
        # Body - 2 Residual blocks
        self.body = nn.Sequential(
            ResBlock(hidden_dim, dropout=0.2),
            ResBlock(hidden_dim, dropout=0.2)
        )
        # Classification Head
        self.head = nn.Linear(hidden_dim, num_classes)
        
    def forward(self, x):
        x = self.stem(x)
        x = self.body(x)
        return self.head(x)

class Solution:
    def solve(self, train_loader, val_loader, metadata: dict = None) -> torch.nn.Module:
        """
        Train a model within 500k parameter budget.
        Strategy: Maximize width within a 3-hidden-layer Residual MLP structure.
        """
        if metadata is None:
            metadata = {}
            
        input_dim = metadata.get("input_dim", 384)
        num_classes = metadata.get("num_classes", 128)
        param_limit = metadata.get("param_limit", 500000)
        device = metadata.get("device", "cpu")
        
        # --- Dynamic Architecture Sizing ---
        # We aim to fill the parameter budget as much as possible to maximize capacity.
        # Architecture: Stem(In->H) -> ResBlock(H->H) -> ResBlock(H->H) -> Head(H->Out)
        # Parameter Count Calculation:
        # 1. Stem: Linear(I,H) + BN(H) -> (I*H + H) + (2*H) = I*H + 3H
        # 2. ResBlock (x2): 2 * [Linear(H,H) + BN(H)] -> 2 * [(H^2 + H) + 2H] = 2H^2 + 6H
        # 3. Head: Linear(H,O) -> H*O + O
        # Total P(H) = 2H^2 + (I + O + 9)H + O
        
        target_params = param_limit - 2000  # Safety buffer
        
        # Solving Quadratic Equation: 2H^2 + bH + c = 0
        a = 2
        b_coef = input_dim + num_classes + 9
        c_coef = num_classes - target_params
        
        # Quadratic formula: (-b + sqrt(b^2 - 4ac)) / 2a
        delta = b_coef**2 - 4 * a * c_coef
        width = int((-b_coef + math.sqrt(delta)) / (2 * a))
        
        # Initialize model
        model = ParetoNet(input_dim, width, num_classes).to(device)
        
        # Strict constraint verification and adjustment
        while True:
            total_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
            if total_params <= param_limit:
                break
            width -= 1
            model = ParetoNet(input_dim, width, num_classes).to(device)
            
        # --- Training Configuration ---
        # 120 epochs fits easily within 1 hour on CPU for this model size
        epochs = 120
        optimizer = optim.AdamW(model.parameters(), lr=0.001, weight_decay=0.02)
        scheduler = optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=epochs)
        criterion = nn.CrossEntropyLoss(label_smoothing=0.1)
        
        best_acc = -1.0
        best_weights = copy.deepcopy(model.state_dict())
        
        # --- Training Loop ---
        for epoch in range(epochs):
            model.train()
            for inputs, targets in train_loader:
                inputs, targets = inputs.to(device), targets.to(device)
                
                # Data Augmentation: Gaussian Noise Injection
                # Helps prevent overfitting on small dataset (2048 samples)
                if epoch < epochs * 0.8:
                    noise = torch.randn_like(inputs) * 0.03
                    inputs = inputs + noise
                
                optimizer.zero_grad()
                outputs = model(inputs)
                loss = criterion(outputs, targets)
                loss.backward()
                optimizer.step()
            
            scheduler.step()
            
            # Validation logic to save best model
            # Validate more frequently towards end of training
            if epoch % 5 == 0 or epoch >= epochs - 15:
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
                
                acc = correct / total if total > 0 else 0
                if acc > best_acc:
                    best_acc = acc
                    best_weights = copy.deepcopy(model.state_dict())
        
        # Return best model found
        model.load_state_dict(best_weights)
        return model
