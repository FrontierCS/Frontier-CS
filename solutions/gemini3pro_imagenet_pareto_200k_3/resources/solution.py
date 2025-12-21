import torch
import torch.nn as nn
import torch.optim as optim
import numpy as np

class Solution:
    def solve(self, train_loader, val_loader, metadata: dict) -> torch.nn.Module:
        """
        Trains a parameter-efficient neural network to maximize accuracy under 200k parameters.
        """
        # Extract metadata
        input_dim = metadata["input_dim"]
        num_classes = metadata["num_classes"]
        device = metadata.get("device", "cpu")
        
        # 1. Compute Data Statistics for Normalization
        # Iterate through training data once to compute mean and std
        all_features = []
        for inputs, _ in train_loader:
            all_features.append(inputs)
        all_features = torch.cat(all_features, dim=0)
        
        mean = torch.mean(all_features, dim=0)
        std = torch.std(all_features, dim=0)
        # Avoid division by zero for constant features
        std = torch.where(std < 1e-6, torch.ones_like(std), std)
        
        # 2. Initialize Model
        # Architecture designed to stay under 200,000 parameters
        # Hidden dim 248 results in approx 190,096 parameters
        hidden_dim = 248
        model = ResidualMLP(input_dim, hidden_dim, num_classes, mean, std)
        model = model.to(device)
        
        # 3. Training Setup
        epochs = 100
        # Label smoothing helps with generalization on small datasets
        criterion = nn.CrossEntropyLoss(label_smoothing=0.1)
        optimizer = optim.AdamW(model.parameters(), lr=0.001, weight_decay=0.01)
        
        # OneCycleLR scheduler for efficient training
        scheduler = optim.lr_scheduler.OneCycleLR(
            optimizer,
            max_lr=0.002,
            steps_per_epoch=len(train_loader),
            epochs=epochs,
            pct_start=0.3,
            div_factor=25.0,
            final_div_factor=1000.0
        )
        
        best_val_acc = 0.0
        best_state_dict = None
        
        # 4. Training Loop
        for epoch in range(epochs):
            model.train()
            for inputs, targets in train_loader:
                inputs, targets = inputs.to(device), targets.to(device)
                
                # Mixup Augmentation (p=0.5)
                # Helps improve robustness and generalization
                if np.random.random() < 0.5:
                    lam = np.random.beta(0.4, 0.4)
                    idx = torch.randperm(inputs.size(0), device=device)
                    mixed_inputs = lam * inputs + (1 - lam) * inputs[idx]
                    target_a, target_b = targets, targets[idx]
                    
                    outputs = model(mixed_inputs)
                    loss = lam * criterion(outputs, target_a) + (1 - lam) * criterion(outputs, target_b)
                else:
                    outputs = model(inputs)
                    loss = criterion(outputs, targets)
                
                optimizer.zero_grad()
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
            
            val_acc = correct / total if total > 0 else 0.0
            
            # Save best model state
            if val_acc >= best_val_acc:
                best_val_acc = val_acc
                # Store state dict on CPU to avoid memory issues
                best_state_dict = {k: v.cpu().clone() for k, v in model.state_dict().items()}
        
        # 5. Restore best model
        if best_state_dict is not None:
            model.load_state_dict(best_state_dict)
            
        return model

class ResidualMLP(nn.Module):
    def __init__(self, input_dim, hidden_dim, num_classes, mean, std):
        super().__init__()
        # Store normalization stats as buffers so they are saved with the model
        self.register_buffer('mean', mean)
        self.register_buffer('std', std)
        
        # Input processing block
        self.input_block = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.BatchNorm1d(hidden_dim),
            nn.SiLU(),
            nn.Dropout(0.25)
        )
        
        # Residual block to increase depth without vanishing gradients
        self.residual_block = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim),
            nn.BatchNorm1d(hidden_dim),
            nn.SiLU(),
            nn.Dropout(0.25)
        )
        
        # Output classification layer
        self.output_layer = nn.Linear(hidden_dim, num_classes)
        
        # Weight Initialization
        for m in self.modules():
            if isinstance(m, nn.Linear):
                nn.init.kaiming_normal_(m.weight, mode='fan_out', nonlinearity='relu')
                if m.bias is not None:
                    nn.init.zeros_(m.bias)
            elif isinstance(m, nn.BatchNorm1d):
                nn.init.ones_(m.weight)
                nn.init.zeros_(m.bias)

    def forward(self, x):
        # Normalize inputs using stored statistics
        x = (x - self.mean) / self.std
        
        # Network pass
        x = self.input_block(x)
        # Residual connection: y = x + f(x)
        x = x + self.residual_block(x)
        x = self.output_layer(x)
        return x
