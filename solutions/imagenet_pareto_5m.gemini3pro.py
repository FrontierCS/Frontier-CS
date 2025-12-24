import torch
import torch.nn as nn
import torch.optim as optim
import math

class Solution:
    def solve(self, train_loader, val_loader, metadata: dict = None) -> torch.nn.Module:
        # Extract metadata constraints
        input_dim = metadata.get("input_dim", 384)
        num_classes = metadata.get("num_classes", 128)
        param_limit = metadata.get("param_limit", 5000000)
        device = torch.device(metadata.get("device", "cpu"))
        
        # Calculate maximum hidden dimension to fit within parameter budget
        # Architecture: Stem(In->H) -> ResBlock(H->H) -> ResBlock(H->H) -> Head(H->Out)
        # Major Weights: (In*H) + (H*H) + (H*H) + (H*Out)
        # Equation: 2*H^2 + (In + Out)*H - Target = 0
        
        target_params = int(param_limit * 0.96) # Leave 4% buffer for biases, BN, etc.
        a = 2
        b = input_dim + num_classes
        c = -target_params
        
        # Quadratic formula to find H
        discriminant = b**2 - 4*a*c
        hidden_dim = int((-b + math.sqrt(discriminant)) / (2*a))
        
        # Ensure hidden_dim is even and reasonable
        hidden_dim = (hidden_dim // 2) * 2

        # Define Model Architecture
        class ResBlock(nn.Module):
            def __init__(self, dim, dropout_rate=0.4):
                super().__init__()
                self.net = nn.Sequential(
                    nn.Linear(dim, dim),
                    nn.BatchNorm1d(dim),
                    nn.GELU(),
                    nn.Dropout(dropout_rate)
                )

            def forward(self, x):
                return x + self.net(x)

        class ResidualMLP(nn.Module):
            def __init__(self, in_d, h_d, out_d, dropout_rate=0.4):
                super().__init__()
                self.stem = nn.Sequential(
                    nn.Linear(in_d, h_d),
                    nn.BatchNorm1d(h_d),
                    nn.GELU(),
                    nn.Dropout(dropout_rate)
                )
                
                self.layer1 = ResBlock(h_d, dropout_rate)
                self.layer2 = ResBlock(h_d, dropout_rate)
                
                self.head = nn.Linear(h_d, out_d)

            def forward(self, x):
                x = self.stem(x)
                x = self.layer1(x)
                x = self.layer2(x)
                return self.head(x)

        # Instantiate Model
        model = ResidualMLP(input_dim, hidden_dim, num_classes)
        model = model.to(device)
        
        # Verify parameter count safety
        current_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
        while current_params > param_limit:
            hidden_dim -= 32
            model = ResidualMLP(input_dim, hidden_dim, num_classes).to(device)
            current_params = sum(p.numel() for p in model.parameters() if p.requires_grad)

        # Training Configuration
        # Small dataset (2048) + Large Model (5M) requires strong regularization
        epochs = 100
        optimizer = optim.AdamW(model.parameters(), lr=1e-3, weight_decay=0.05)
        criterion = nn.CrossEntropyLoss(label_smoothing=0.1)
        
        # Scheduler
        steps_per_epoch = len(train_loader)
        scheduler = optim.lr_scheduler.OneCycleLR(
            optimizer,
            max_lr=1e-3,
            epochs=epochs,
            steps_per_epoch=steps_per_epoch,
            pct_start=0.3
        )

        best_val_acc = -1.0
        best_model_state = None

        # Training Loop
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
            
            # Validate
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
            
            # Save best model
            if val_acc >= best_val_acc:
                best_val_acc = val_acc
                best_model_state = {k: v.cpu() for k, v in model.state_dict().items()}

        # Restore best model
        if best_model_state is not None:
            model.load_state_dict(best_model_state)
            
        return model
