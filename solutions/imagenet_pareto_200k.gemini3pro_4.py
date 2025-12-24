import torch
import torch.nn as nn
import torch.optim as optim
import copy

class Solution:
    def solve(self, train_loader, val_loader, metadata: dict = None) -> torch.nn.Module:
        """
        Train a model on synthetic ImageNet-like data within 200k parameters.
        """
        # 1. Extract Metadata
        input_dim = metadata.get("input_dim", 384)
        num_classes = metadata.get("num_classes", 128)
        device = metadata.get("device", "cpu")
        PARAM_LIMIT = 200000

        # 2. Dynamic Architecture Configuration
        # Determine maximum hidden dimensions that fit within the parameter budget.
        # Architecture: Input -> H1 -> H2 -> Output
        # Constraint: H2 approx 2/3 of H1 for tapered bottleneck.
        
        best_h1 = 64
        # Search for optimal width
        for h1 in range(64, 4096, 8):
            h2 = int(h1 * 0.666)
            
            # Parameter Count Calculation
            # Layer 1: Linear(In, H1) + BN(H1)
            # Params = (In * H1 + H1) + (2 * H1)
            p1 = (input_dim * h1 + h1) + (2 * h1)
            
            # Layer 2: Linear(H1, H2) + BN(H2)
            # Params = (H1 * H2 + H2) + (2 * H2)
            p2 = (h1 * h2 + h2) + (2 * h2)
            
            # Layer 3: Linear(H2, Out) + Bias (No BN)
            # Params = (H2 * Out + Out)
            p3 = (h2 * num_classes + num_classes)
            
            total_params = p1 + p2 + p3
            
            if total_params > PARAM_LIMIT:
                break
            best_h1 = h1
            
        h1 = best_h1
        h2 = int(h1 * 0.666)
        
        # 3. Model Definition
        class OptimizedMLP(nn.Module):
            def __init__(self, in_d, h1, h2, out_d):
                super().__init__()
                self.net = nn.Sequential(
                    nn.Linear(in_d, h1),
                    nn.BatchNorm1d(h1),
                    nn.SiLU(),
                    nn.Dropout(0.25),
                    
                    nn.Linear(h1, h2),
                    nn.BatchNorm1d(h2),
                    nn.SiLU(),
                    nn.Dropout(0.25),
                    
                    nn.Linear(h2, out_d)
                )
                
            def forward(self, x):
                return self.net(x)

        model = OptimizedMLP(input_dim, h1, h2, num_classes).to(device)
        
        # 4. Training Strategy
        # Using OneCycleLR and AdamW for efficient convergence on small data
        epochs = 60
        criterion = nn.CrossEntropyLoss(label_smoothing=0.1)
        optimizer = optim.AdamW(model.parameters(), lr=0.002, weight_decay=0.02)
        
        # Calculate steps for scheduler
        try:
            steps_per_epoch = len(train_loader)
        except:
            steps_per_epoch = 64 # Fallback estimation
            
        scheduler = optim.lr_scheduler.OneCycleLR(
            optimizer,
            max_lr=0.002,
            epochs=epochs,
            steps_per_epoch=steps_per_epoch,
            pct_start=0.3,
            div_factor=25.0
        )
        
        best_acc = -1.0
        best_state = None
        
        # 5. Training Loop
        for epoch in range(epochs):
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
            if val_loader:
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
        
        # Return best performing model
        if best_state is not None:
            model.load_state_dict(best_state)
            
        return model
