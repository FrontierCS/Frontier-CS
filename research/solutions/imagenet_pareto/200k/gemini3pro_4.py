import torch
import torch.nn as nn
import torch.optim as optim
import copy

class Solution:
    def solve(self, train_loader, val_loader, metadata: dict = None) -> torch.nn.Module:
        """
        Train a model on synthetic ImageNet-like data within 200k parameters.
        """
        # Extract metadata
        input_dim = metadata.get("input_dim", 384)
        num_classes = metadata.get("num_classes", 128)
        device = metadata.get("device", "cpu")
        param_limit = metadata.get("param_limit", 200000)
        
        # Define optimized model architecture
        # We aim for ~199k parameters to maximize capacity within the budget.
        # Architecture: BN -> Linear(256) -> BN -> GELU -> Dropout -> Linear(256) -> BN -> GELU -> Dropout -> Linear(128)
        # Parameter Calculation for 384 -> 128:
        # Input BN (384): 2 * 384 = 768
        # L1 (384->256): 384 * 256 + 256 = 98,560
        # BN1 (256): 2 * 256 = 512
        # L2 (256->256): 256 * 256 + 256 = 65,792
        # BN2 (256): 2 * 256 = 512
        # L3 (256->128): 256 * 128 + 128 = 32,896
        # Total: 199,040 parameters
        
        class OptimalNet(nn.Module):
            def __init__(self, in_dim, n_classes):
                super().__init__()
                self.input_norm = nn.BatchNorm1d(in_dim)
                
                self.layer1 = nn.Sequential(
                    nn.Linear(in_dim, 256),
                    nn.BatchNorm1d(256),
                    nn.GELU(),
                    nn.Dropout(0.4)
                )
                
                self.layer2 = nn.Sequential(
                    nn.Linear(256, 256),
                    nn.BatchNorm1d(256),
                    nn.GELU(),
                    nn.Dropout(0.4)
                )
                
                self.output = nn.Linear(256, n_classes)

            def forward(self, x):
                x = self.input_norm(x)
                x = self.layer1(x)
                x = self.layer2(x)
                return self.output(x)

        # Initialize model
        model = OptimalNet(input_dim, num_classes).to(device)
        
        # Hard constraint check
        current_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
        
        if current_params > param_limit:
            # Fallback to a smaller safe architecture if dimensions differ or overhead exists
            class SafeNet(nn.Module):
                def __init__(self, in_dim, n_classes):
                    super().__init__()
                    # Reduced width to 192 to safely stay under budget
                    hidden = 192
                    self.net = nn.Sequential(
                        nn.BatchNorm1d(in_dim),
                        nn.Linear(in_dim, hidden),
                        nn.BatchNorm1d(hidden),
                        nn.ReLU(),
                        nn.Dropout(0.3),
                        nn.Linear(hidden, hidden),
                        nn.BatchNorm1d(hidden),
                        nn.ReLU(),
                        nn.Dropout(0.3),
                        nn.Linear(hidden, n_classes)
                    )
                def forward(self, x):
                    return self.net(x)
            
            model = SafeNet(input_dim, num_classes).to(device)

        # Training Configuration
        # Label smoothing helps with the small dataset size (16 samples/class)
        criterion = nn.CrossEntropyLoss(label_smoothing=0.1)
        # AdamW with weight decay for regularization
        optimizer = optim.AdamW(model.parameters(), lr=1e-3, weight_decay=0.02)
        
        epochs = 60
        # Determine steps for scheduler
        steps_per_epoch = len(train_loader) if hasattr(train_loader, '__len__') else 64
        
        # OneCycleLR provides fast convergence
        scheduler = optim.lr_scheduler.OneCycleLR(
            optimizer, 
            max_lr=2e-3, 
            epochs=epochs, 
            steps_per_epoch=steps_per_epoch,
            pct_start=0.3
        )
        
        best_state = copy.deepcopy(model.state_dict())
        best_acc = 0.0
        
        for epoch in range(epochs):
            model.train()
            for inputs, targets in train_loader:
                inputs, targets = inputs.to(device), targets.to(device)
                
                # Noise injection regularization (active for first 70% of training)
                # Adds robustness to feature variations
                if epoch < int(epochs * 0.7):
                    noise = torch.randn_like(inputs) * 0.05
                    inputs = inputs + noise
                
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
                    _, preds = torch.max(outputs, 1)
                    correct += (preds == targets).sum().item()
                    total += targets.size(0)
            
            acc = correct / total if total > 0 else 0.0
            
            # Save best model
            if acc >= best_acc:
                best_acc = acc
                best_state = copy.deepcopy(model.state_dict())
        
        # Load best weights before returning
        model.load_state_dict(best_state)
        return model