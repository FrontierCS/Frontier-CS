import torch
import torch.nn as nn
import torch.optim as optim
import numpy as np
import random
import math

class Solution:
    def solve(self, train_loader, val_loader, metadata: dict = None) -> torch.nn.Module:
        """
        Train a model on synthetic ImageNet features within 1M parameter budget.
        Strategy: Wide Residual MLP with Mixup, Label Smoothing, and OneCycleLR.
        """
        # Extract metadata
        input_dim = metadata.get("input_dim", 384)
        num_classes = metadata.get("num_classes", 128)
        param_limit = metadata.get("param_limit", 1000000)
        device = metadata.get("device", "cpu")
        
        # Set seeds for reproducibility
        torch.manual_seed(42)
        np.random.seed(42)
        random.seed(42)
        if torch.cuda.is_available():
            torch.cuda.manual_seed(42)
        
        # --- Architecture Design ---
        # We use a Residual MLP: Input -> Proj -> ResBlock -> Head
        # Structure:
        # 1. Stem: Linear(In, H) + BN + GELU
        # 2. ResBlock: Linear(H, H) + BN + GELU + Dropout (Skip connection added)
        # 3. Head: Linear(H, Out)
        #
        # Parameter Calculation:
        # Stem: In*H (weights) + 2*H (BN)
        # Body: H*H (weights) + 2*H (BN)
        # Head: H*Out (weights) + Out (bias)
        # Total ~= H^2 + (In + Out + 4)*H + Out
        
        # Calculate maximum Hidden Dim (H) to satisfy param_limit
        # Quadratic eq: H^2 + b*H + c = 0
        target_budget = param_limit - 2000  # Safety buffer
        a = 1.0
        b = input_dim + num_classes + 4.0
        c = num_classes - target_budget
        
        # Quadratic formula: (-b + sqrt(b^2 - 4ac)) / 2a
        discriminant = b**2 - 4*a*c
        hidden_dim = int((-b + math.sqrt(discriminant)) / (2*a))
        
        class ResMLP(nn.Module):
            def __init__(self, in_d, h_d, out_d):
                super().__init__()
                self.stem = nn.Sequential(
                    nn.Linear(in_d, h_d, bias=False),
                    nn.BatchNorm1d(h_d),
                    nn.GELU(),
                    nn.Dropout(0.2)
                )
                
                self.body = nn.Sequential(
                    nn.Linear(h_d, h_d, bias=False),
                    nn.BatchNorm1d(h_d),
                    nn.GELU(),
                    nn.Dropout(0.3)
                )
                
                self.head = nn.Linear(h_d, out_d)
                
            def forward(self, x):
                x = self.stem(x)
                # Residual connection
                identity = x
                out = self.body(x)
                x = out + identity
                x = self.head(x)
                return x

        model = ResMLP(input_dim, hidden_dim, num_classes).to(device)
        
        # Verify parameter count
        param_count = sum(p.numel() for p in model.parameters() if p.requires_grad)
        if param_count > param_limit:
            # Fallback (should not happen with calculation)
            model = ResMLP(input_dim, hidden_dim - 10, num_classes).to(device)

        # --- Training Setup ---
        # Heavy regularization for small dataset
        optimizer = optim.AdamW(model.parameters(), lr=1e-3, weight_decay=0.05)
        
        epochs = 120
        # OneCycleLR for super-convergence
        scheduler = optim.lr_scheduler.OneCycleLR(
            optimizer,
            max_lr=2e-3,
            epochs=epochs,
            steps_per_epoch=len(train_loader),
            pct_start=0.3,
            div_factor=25.0,
            final_div_factor=1000.0
        )
        
        # Label Smoothing to prevent overfitting on noisy labels
        criterion = nn.CrossEntropyLoss(label_smoothing=0.1)
        
        best_val_acc = 0.0
        best_model_state = None
        
        # --- Training Loop ---
        for epoch in range(epochs):
            model.train()
            for inputs, targets in train_loader:
                inputs, targets = inputs.to(device), targets.to(device)
                
                # Mixup Augmentation
                # Using Beta(0.4, 0.4) promotes mixing without being too uniform
                if random.random() < 0.6:
                    lam = np.random.beta(0.4, 0.4)
                    index = torch.randperm(inputs.size(0)).to(device)
                    
                    mixed_inputs = lam * inputs + (1 - lam) * inputs[index]
                    
                    outputs = model(mixed_inputs)
                    loss = lam * criterion(outputs, targets) + (1 - lam) * criterion(outputs, targets[index])
                else:
                    outputs = model(inputs)
                    loss = criterion(outputs, targets)
                
                optimizer.zero_grad()
                loss.backward()
                optimizer.step()
                scheduler.step()
            
            # --- Validation ---
            # Save best model based on validation accuracy
            # Check more frequently towards end of training
            if epoch >= (epochs - 40) or epoch % 10 == 0:
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
                
                val_acc = correct / total
                if val_acc >= best_val_acc:
                    best_val_acc = val_acc
                    best_model_state = model.state_dict()
        
        # Load best performing model
        if best_model_state is not None:
            model.load_state_dict(best_model_state)
            
        return model