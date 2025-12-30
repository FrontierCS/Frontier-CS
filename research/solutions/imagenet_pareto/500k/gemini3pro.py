import torch
import torch.nn as nn
import torch.optim as optim
import numpy as np
import math
import random

# Define model components
class ResidualBlock(nn.Module):
    def __init__(self, dim, dropout_rate=0.2):
        super(ResidualBlock, self).__init__()
        self.block = nn.Sequential(
            nn.Linear(dim, dim),
            nn.BatchNorm1d(dim),
            nn.ReLU(),
            nn.Dropout(dropout_rate),
            nn.Linear(dim, dim),
            nn.BatchNorm1d(dim),
            nn.Dropout(dropout_rate)
        )
        self.relu = nn.ReLU()

    def forward(self, x):
        identity = x
        out = self.block(x)
        return self.relu(identity + out)

class AdaptiveMLP(nn.Module):
    def __init__(self, input_dim, num_classes, hidden_dim):
        super(AdaptiveMLP, self).__init__()
        # Initial normalization of raw features
        self.input_norm = nn.BatchNorm1d(input_dim)
        
        # Projection to hidden dimension
        self.entry = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.BatchNorm1d(hidden_dim),
            nn.ReLU(),
            nn.Dropout(0.25)
        )
        
        # Deep processing with residual connection
        self.res_block = ResidualBlock(hidden_dim, dropout_rate=0.25)
        
        # Classification head
        self.classifier = nn.Linear(hidden_dim, num_classes)

    def forward(self, x):
        x = self.input_norm(x)
        x = self.entry(x)
        x = self.res_block(x)
        x = self.classifier(x)
        return x

class Solution:
    def solve(self, train_loader, val_loader, metadata: dict = None) -> torch.nn.Module:
        # Set seeds for reproducibility
        torch.manual_seed(42)
        np.random.seed(42)
        random.seed(42)
        
        # Extract metadata
        input_dim = metadata.get("input_dim", 384)
        num_classes = metadata.get("num_classes", 128)
        param_limit = metadata.get("param_limit", 500000)
        device = metadata.get("device", "cpu")
        
        # Dynamic Architecture Sizing
        # We model the parameter count as a function of hidden_dim (H)
        # Params breakdown:
        # Input BN: 2*Input
        # Entry Layer: H*Input + H + 2*H (Linear + Bias + BN) = H*Input + 3H
        # ResBlock: 2*(H^2 + H + 2H) = 2*H^2 + 6H
        # Classifier: H*Classes + Classes
        # Total = 2*H^2 + H*(Input + Classes + 9) + (2*Input + Classes)
        
        a = 2
        b = input_dim + num_classes + 9
        c_val = (2 * input_dim + num_classes) - param_limit
        
        # Quadratic formula: (-b + sqrt(b^2 - 4ac)) / 2a
        delta = b**2 - 4*a*c_val
        if delta < 0:
            hidden_dim = 128 # Fallback safe value
        else:
            hidden_dim = int((-b + math.sqrt(delta)) / (2*a))
            
        # Verify strict compliance and adjust downward if floating point errors occurred
        while True:
            total_params = 2*(hidden_dim**2) + hidden_dim*(input_dim + num_classes + 9) + (2*input_dim + num_classes)
            if total_params <= param_limit:
                break
            hidden_dim -= 1
            
        # Initialize model
        model = AdaptiveMLP(input_dim, num_classes, hidden_dim).to(device)
        
        # Optimization setup
        # Using AdamW with weight decay for regularization on small dataset
        optimizer = optim.AdamW(model.parameters(), lr=0.001, weight_decay=0.02)
        
        # Label smoothing helps with calibration and generalization
        criterion = nn.CrossEntropyLoss(label_smoothing=0.1)
        
        # Train for sufficient epochs given small dataset size
        epochs = 100
        scheduler = optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=epochs)
        
        best_val_acc = -1.0
        best_model_state = None
        
        # Mixup parameters
        use_mixup = True
        mixup_alpha = 0.4
        
        for epoch in range(epochs):
            model.train()
            for inputs, targets in train_loader:
                inputs, targets = inputs.to(device), targets.to(device)
                
                optimizer.zero_grad()
                
                # Apply Mixup Augmentation (turn off near end of training for fine-tuning)
                if use_mixup and epoch < epochs - 15:
                    # Sample lambda from Beta distribution
                    lam = np.random.beta(mixup_alpha, mixup_alpha)
                    
                    # Permute indices for mixing
                    index = torch.randperm(inputs.size(0)).to(device)
                    
                    mixed_inputs = lam * inputs + (1 - lam) * inputs[index]
                    target_a, target_b = targets, targets[index]
                    
                    outputs = model(mixed_inputs)
                    loss = lam * criterion(outputs, target_a) + (1 - lam) * criterion(outputs, target_b)
                else:
                    outputs = model(inputs)
                    loss = criterion(outputs, targets)
                
                loss.backward()
                optimizer.step()
            
            scheduler.step()
            
            # Validation Step
            if epoch % 1 == 0: 
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
                
                val_acc = correct / total if total > 0 else 0.0
                
                # Save best model
                if val_acc > best_val_acc:
                    best_val_acc = val_acc
                    # Deep copy the state dict to preserve best weights
                    best_model_state = {k: v.clone() for k, v in model.state_dict().items()}
        
        # Restore best model
        if best_model_state is not None:
            model.load_state_dict(best_model_state)
            
        return model