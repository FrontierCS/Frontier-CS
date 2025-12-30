import torch
import torch.nn as nn
import torch.optim as optim
import numpy as np
import random

# Set seeds for reproducibility
torch.manual_seed(42)
np.random.seed(42)
random.seed(42)

class ResBlock(nn.Module):
    """
    Residual Block: x + Dropout(GELU(BN(Linear(x))))
    """
    def __init__(self, dim, dropout=0.2):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(dim, dim),
            nn.BatchNorm1d(dim),
            nn.GELU(),
            nn.Dropout(dropout)
        )

    def forward(self, x):
        return x + self.net(x)

class Model(nn.Module):
    def __init__(self, input_dim, num_classes, hidden_dim=1048, dropout=0.3):
        super().__init__()
        
        # Input Projection
        self.input_net = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.BatchNorm1d(hidden_dim),
            nn.GELU()
        )
        
        # 4 Residual Blocks
        # Hidden dim 1048 allows 4 blocks within 5M budget
        # Calculation:
        # Input: ~0.4M
        # Blocks: 4 * (~1.1M) = ~4.4M
        # Head: ~0.13M
        # Total: ~4.95M < 5.00M
        self.blocks = nn.ModuleList([
            ResBlock(hidden_dim, dropout) for _ in range(4)
        ])
        
        # Classification Head
        self.head = nn.Linear(hidden_dim, num_classes)

    def forward(self, x):
        x = self.input_net(x)
        for block in self.blocks:
            x = block(x)
        return self.head(x)

class Solution:
    def solve(self, train_loader, val_loader, metadata: dict = None) -> torch.nn.Module:
        """
        Train a model for ImageNet-like synthetic data within 5M parameter budget.
        """
        # Metadata extraction
        input_dim = metadata.get("input_dim", 384)
        num_classes = metadata.get("num_classes", 128)
        device = metadata.get("device", "cpu")
        
        # Hyperparameters
        # We maximize width (1048) to utilize the parameter budget effectively
        HIDDEN_DIM = 1048
        EPOCHS = 60
        LR = 1e-3
        WD = 2e-2
        DROPOUT = 0.3
        
        # Model Initialization
        model = Model(input_dim, num_classes, HIDDEN_DIM, DROPOUT).to(device)
        
        # Strict Parameter Count Verification
        param_count = sum(p.numel() for p in model.parameters() if p.requires_grad)
        
        # Fallback if calculation is slightly off or requirements change
        if param_count > 5000000:
            HIDDEN_DIM = 1024 # Safe fallback
            model = Model(input_dim, num_classes, HIDDEN_DIM, DROPOUT).to(device)
        
        # Optimizer Setup
        optimizer = optim.AdamW(model.parameters(), lr=LR, weight_decay=WD)
        
        # Scheduler Setup (OneCycle is efficient for fixed epoch training)
        try:
            steps_per_epoch = len(train_loader)
        except:
            steps_per_epoch = 2048 // 64 # Estimate if len not available
            
        scheduler = optim.lr_scheduler.OneCycleLR(
            optimizer,
            max_lr=LR,
            epochs=EPOCHS,
            steps_per_epoch=steps_per_epoch,
            pct_start=0.3
        )
        
        # Loss function with Label Smoothing for regularization
        criterion = nn.CrossEntropyLoss(label_smoothing=0.1)
        
        # Training State
        best_acc = 0.0
        best_state = None
        
        # Training Loop
        for epoch in range(EPOCHS):
            model.train()
            
            for inputs, targets in train_loader:
                inputs, targets = inputs.to(device), targets.to(device)
                
                optimizer.zero_grad()
                
                # Mixup Augmentation
                # Critical for small data regimes (2048 samples)
                # We disable mixup in the last few epochs for clean convergence
                if epoch < EPOCHS - 10:
                    alpha = 0.4
                    lam = np.random.beta(alpha, alpha)
                    idx = torch.randperm(inputs.size(0)).to(device)
                    mixed_input = lam * inputs + (1 - lam) * inputs[idx]
                    
                    outputs = model(mixed_input)
                    loss = lam * criterion(outputs, targets) + (1 - lam) * criterion(outputs, targets[idx])
                else:
                    outputs = model(inputs)
                    loss = criterion(outputs, targets)
                
                loss.backward()
                nn.utils.clip_grad_norm_(model.parameters(), 1.0)
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
                    _, predicted = outputs.max(1)
                    total += targets.size(0)
                    correct += predicted.eq(targets).sum().item()
            
            acc = correct / total
            
            # Checkpoint best model
            if acc > best_acc:
                best_acc = acc
                # Save state (clone tensors to ensure persistence)
                best_state = {k: v.clone() for k, v in model.state_dict().items()}
        
        # Restore best performing model
        if best_state is not None:
            model.load_state_dict(best_state)
            
        return model