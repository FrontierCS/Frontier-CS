import torch
import torch.nn as nn
import torch.optim as optim
import math

class Solution:
    def solve(self, train_loader, val_loader, metadata: dict = None) -> torch.nn.Module:
        input_dim = metadata.get("input_dim", 384)
        num_classes = metadata.get("num_classes", 128)
        device = metadata.get("device", "cpu")
        
        # Calculate optimal hidden dimension to maximize parameters under 5M
        # Architecture: 4-layer MLP (3 hidden layers)
        # Structure: Input -> H -> H -> H -> Output
        # Parameters count formula:
        # Layers: (in*h + h) + (h*h + h) + (h*h + h) + (h*out + out)
        # BatchNorms (3 layers): 3 * (2*h) = 6h
        # Total P = 2*h^2 + h*(in + out + 9) + out
        
        target_params = 4980000  # Safe buffer below 5,000,000
        a = 2
        b = input_dim + num_classes + 9
        c = num_classes - target_params
        
        # Solve quadratic equation 2h^2 + bh + c = 0 for h
        hidden_dim = int((-b + math.sqrt(b**2 - 4*a*c)) / (2*a))
        
        class OptimizedMLP(nn.Module):
            def __init__(self, in_d, out_d, h_d):
                super().__init__()
                self.layers = nn.Sequential(
                    nn.Linear(in_d, h_d),
                    nn.BatchNorm1d(h_d),
                    nn.SiLU(),
                    nn.Dropout(0.25),
                    
                    nn.Linear(h_d, h_d),
                    nn.BatchNorm1d(h_d),
                    nn.SiLU(),
                    nn.Dropout(0.25),
                    
                    nn.Linear(h_d, h_d),
                    nn.BatchNorm1d(h_d),
                    nn.SiLU(),
                    nn.Dropout(0.25),
                    
                    nn.Linear(h_d, out_d)
                )
                
                # Weight initialization
                for m in self.modules():
                    if isinstance(m, nn.Linear):
                        nn.init.kaiming_normal_(m.weight, mode='fan_out', nonlinearity='relu')
                        if m.bias is not None:
                            nn.init.constant_(m.bias, 0)
                    elif isinstance(m, nn.BatchNorm1d):
                        nn.init.constant_(m.weight, 1)
                        nn.init.constant_(m.bias, 0)
            
            def forward(self, x):
                return self.layers(x)

        model = OptimizedMLP(input_dim, num_classes, hidden_dim).to(device)
        
        # Training configuration
        epochs = 80
        lr = 1e-3
        weight_decay = 0.02
        
        optimizer = optim.AdamW(model.parameters(), lr=lr, weight_decay=weight_decay)
        criterion = nn.CrossEntropyLoss(label_smoothing=0.1)
        
        try:
            steps_per_epoch = len(train_loader)
        except:
            steps_per_epoch = 100
            
        scheduler = optim.lr_scheduler.OneCycleLR(
            optimizer,
            max_lr=lr,
            epochs=epochs,
            steps_per_epoch=steps_per_epoch,
            pct_start=0.2,
            div_factor=10.0,
            final_div_factor=1000.0
        )
        
        best_acc = 0.0
        best_state = None
        
        # Training loop
        for epoch in range(epochs):
            model.train()
            for inputs, targets in train_loader:
                inputs, targets = inputs.to(device), targets.to(device)
                
                optimizer.zero_grad()
                outputs = model(inputs)
                loss = criterion(outputs, targets)
                loss.backward()
                
                # Gradient clipping for stability
                torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
                
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
                    correct += (predicted == targets).sum().item()
            
            acc = correct / total
            
            if acc >= best_acc:
                best_acc = acc
                # Save state to CPU
                best_state = {k: v.cpu().clone() for k, v in model.state_dict().items()}
        
        # Restore best model
        if best_state is not None:
            model.load_state_dict(best_state)
            
        return model