import torch
import torch.nn as nn
import torch.optim as optim
import numpy as np
import copy

class Solution:
    def solve(self, train_loader, val_loader, metadata: dict = None) -> torch.nn.Module:
        """
        Train a model and return it.
        """
        # Handle metadata
        metadata = metadata or {}
        input_dim = metadata.get("input_dim", 384)
        num_classes = metadata.get("num_classes", 128)
        param_limit = metadata.get("param_limit", 2500000)
        device = metadata.get("device", "cpu")
        
        # Hyperparameters
        # To maximize accuracy within 2.5M parameters, we use a Residual MLP.
        # Calculation for H=524 with 4 blocks (2 layers each):
        # Embed: 384*524 + 524 + BN params ~= 203k
        # Blocks: 4 * (2 * (524*524 + 524 + BN)) ~= 4 * 552k = 2.2M
        # Head: 524*128 + 128 ~= 67k
        # Total ~= 2.47M < 2.5M.
        hidden_dim = 524
        num_blocks = 4
        dropout_rate = 0.2
        epochs = 120
        learning_rate = 1e-3
        weight_decay = 1e-2
        mixup_alpha = 0.2

        class ResBlock(nn.Module):
            def __init__(self, dim, drop):
                super().__init__()
                self.net = nn.Sequential(
                    nn.Linear(dim, dim),
                    nn.BatchNorm1d(dim),
                    nn.ReLU(),
                    nn.Dropout(drop),
                    nn.Linear(dim, dim),
                    nn.BatchNorm1d(dim),
                    nn.ReLU(),
                    nn.Dropout(drop)
                )
            
            def forward(self, x):
                return x + self.net(x)

        class ResMLP(nn.Module):
            def __init__(self, in_dim, h_dim, out_dim, blocks, drop):
                super().__init__()
                self.embedding = nn.Sequential(
                    nn.Linear(in_dim, h_dim),
                    nn.BatchNorm1d(h_dim),
                    nn.ReLU(),
                    nn.Dropout(drop)
                )
                self.layers = nn.ModuleList([ResBlock(h_dim, drop) for _ in range(blocks)])
                self.head = nn.Linear(h_dim, out_dim)
            
            def forward(self, x):
                x = self.embedding(x)
                for layer in self.layers:
                    x = layer(x)
                return self.head(x)

        # Initialize model
        model = ResMLP(input_dim, hidden_dim, num_classes, num_blocks, dropout_rate)
        model = model.to(device)

        # Check parameter count constraint
        current_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
        if current_params > param_limit:
            # Fallback to a slightly smaller width if calculation exceeds limit
            hidden_dim = 512
            model = ResMLP(input_dim, hidden_dim, num_classes, num_blocks, dropout_rate)
            model = model.to(device)

        # Setup Training
        optimizer = optim.AdamW(model.parameters(), lr=learning_rate, weight_decay=weight_decay)
        criterion = nn.CrossEntropyLoss()
        
        # OneCycleLR is efficient for convergence
        total_steps = epochs * len(train_loader)
        scheduler = optim.lr_scheduler.OneCycleLR(
            optimizer, max_lr=learning_rate, total_steps=total_steps, pct_start=0.3
        )
        
        best_val_acc = 0.0
        best_model_state = copy.deepcopy(model.state_dict())
        
        # Training Loop
        for epoch in range(epochs):
            model.train()
            for inputs, targets in train_loader:
                inputs, targets = inputs.to(device), targets.to(device)
                
                optimizer.zero_grad()
                
                # Mixup Augmentation
                if mixup_alpha > 0:
                    lam = np.random.beta(mixup_alpha, mixup_alpha)
                    indices = torch.randperm(inputs.size(0)).to(device)
                    mixed_inputs = lam * inputs + (1 - lam) * inputs[indices]
                    targets_a, targets_b = targets, targets[indices]
                    
                    outputs = model(mixed_inputs)
                    loss = lam * criterion(outputs, targets_a) + (1 - lam) * criterion(outputs, targets_b)
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
                    _, predicted = torch.max(outputs, 1)
                    total += targets.size(0)
                    correct += (predicted == targets).sum().item()
            
            val_acc = correct / total if total > 0 else 0
            
            if val_acc > best_val_acc:
                best_val_acc = val_acc
                best_model_state = copy.deepcopy(model.state_dict())
        
        # Load best model
        model.load_state_dict(best_model_state)
        return model