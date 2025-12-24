import torch
import torch.nn as nn
import torch.optim as optim
import math
import copy

class Solution:
    def solve(self, train_loader, val_loader, metadata: dict = None) -> torch.nn.Module:
        """
        Solves the ImageNet Pareto Optimization problem by training a neural network
        within the 500k parameter budget.
        """
        # 1. Parse Metadata
        input_dim = metadata.get("input_dim", 384)
        num_classes = metadata.get("num_classes", 128)
        param_limit = metadata.get("param_limit", 500000)
        device = metadata.get("device", "cpu")

        # 2. Dynamic Architecture Design
        # We design a 2-hidden-layer MLP with Residual connections.
        # Structure: 
        #   L1: Linear(In, H) + BN + ReLU + Drop
        #   L2: Linear(H, H) + BN + ReLU + Drop + Residual(L1_out)
        #   L3: Linear(H, Out)
        #
        # Parameter Calculation (ignoring biases in hidden layers where BN is used):
        #   L1: In*H (weights) + 2*H (BN scale/shift)
        #   L2: H*H (weights) + 2*H (BN scale/shift)
        #   L3: H*Out (weights) + Out (bias)
        # Total = H^2 + H*(In + Out + 4) + Out
        
        # Solving for H: H^2 + bH + c = 0
        b = input_dim + num_classes + 4
        c = num_classes - param_limit
        
        # Quadratic formula: (-b + sqrt(b^2 - 4ac)) / 2
        discriminant = b**2 - 4 * c
        h_max = int((-b + math.sqrt(discriminant)) / 2)
        
        # Set hidden dimension
        hidden_dim = h_max

        # 3. Model Definition
        class ResMLP(nn.Module):
            def __init__(self, in_d, h_d, out_d):
                super(ResMLP, self).__init__()
                # Layer 1
                self.l1 = nn.Linear(in_d, h_d, bias=False)
                self.bn1 = nn.BatchNorm1d(h_d)
                self.act1 = nn.ReLU()
                self.drop1 = nn.Dropout(0.3)
                
                # Layer 2 (Residual Block)
                self.l2 = nn.Linear(h_d, h_d, bias=False)
                self.bn2 = nn.BatchNorm1d(h_d)
                self.act2 = nn.ReLU()
                self.drop2 = nn.Dropout(0.3)
                
                # Output
                self.head = nn.Linear(h_d, out_d)
                
            def forward(self, x):
                # Block 1
                x = self.l1(x)
                x = self.bn1(x)
                x = self.act1(x)
                x = self.drop1(x)
                
                # Block 2 with Residual
                identity = x
                out = self.l2(x)
                out = self.bn2(out)
                out = self.act2(out)
                out = self.drop2(out)
                out = out + identity  # Residual connection
                
                # Classification
                return self.head(out)

        # Instantiate
        model = ResMLP(input_dim, hidden_dim, num_classes).to(device)
        
        # 4. Strict Parameter Budget Enforcement
        def get_param_count(m):
            return sum(p.numel() for p in m.parameters() if p.requires_grad)

        while get_param_count(model) > param_limit:
            hidden_dim -= 1
            model = ResMLP(input_dim, hidden_dim, num_classes).to(device)

        # 5. Training Setup
        # Using AdamW with Weight Decay for regularization
        # Using Label Smoothing to prevent overfitting on small dataset
        criterion = nn.CrossEntropyLoss(label_smoothing=0.1)
        optimizer = optim.AdamW(model.parameters(), lr=0.001, weight_decay=0.01)
        
        epochs = 60
        # OneCycleLR scheduler for fast convergence
        scheduler = optim.lr_scheduler.OneCycleLR(
            optimizer,
            max_lr=0.001,
            epochs=epochs,
            steps_per_epoch=len(train_loader),
            pct_start=0.3
        )

        best_acc = 0.0
        best_weights = copy.deepcopy(model.state_dict())

        # 6. Training Loop
        for epoch in range(epochs):
            # Train
            model.train()
            for inputs, targets in train_loader:
                inputs, targets = inputs.to(device), targets.to(device)
                
                optimizer.zero_grad()
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
            
            val_acc = correct / total
            
            # Checkpoint
            if val_acc >= best_acc:
                best_acc = val_acc
                best_weights = copy.deepcopy(model.state_dict())

        # 7. Finalize
        model.load_state_dict(best_weights)
        return model
