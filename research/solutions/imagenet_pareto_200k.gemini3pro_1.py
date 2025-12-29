import torch
import torch.nn as nn
import torch.optim as optim
import numpy as np
import copy

class Network(nn.Module):
    def __init__(self, input_dim, hidden_dim, num_classes):
        super(Network, self).__init__()
        # Architecture designed to maximize parameter usage within 200k limit
        # Input: 384, Hidden: 256, Output: 128
        # Params: (384*256+256) + 2*256 + (256*256+256) + 2*256 + (256*128+128)
        #       = 98,560 + 512 + 65,792 + 512 + 32,896 = 198,272
        self.features = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.BatchNorm1d(hidden_dim),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(hidden_dim, hidden_dim),
            nn.BatchNorm1d(hidden_dim),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(hidden_dim, num_classes)
        )

    def forward(self, x):
        return self.features(x)

class Solution:
    def solve(self, train_loader, val_loader, metadata: dict = None) -> torch.nn.Module:
        """
        Train a model and return it.
        """
        # Extract metadata
        input_dim = metadata.get("input_dim", 384)
        num_classes = metadata.get("num_classes", 128)
        device = metadata.get("device", "cpu")
        
        # Define hyperparams
        hidden_dim = 256  # Fits within 200k budget
        epochs = 100
        lr = 0.001
        weight_decay = 1e-4
        mixup_alpha = 0.4
        
        # Initialize model
        model = Network(input_dim, hidden_dim, num_classes).to(device)
        
        # Setup optimizer and loss
        optimizer = optim.AdamW(model.parameters(), lr=lr, weight_decay=weight_decay)
        scheduler = optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=epochs)
        criterion = nn.CrossEntropyLoss(label_smoothing=0.1)
        
        best_val_acc = -1.0
        best_model_wts = copy.deepcopy(model.state_dict())
        
        for epoch in range(epochs):
            # Training Phase
            model.train()
            for inputs, targets in train_loader:
                inputs = inputs.to(device)
                targets = targets.to(device)
                
                optimizer.zero_grad()
                
                # Mixup Augmentation
                if mixup_alpha > 0:
                    lam = np.random.beta(mixup_alpha, mixup_alpha)
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
            
            # Validation Phase
            model.eval()
            correct = 0
            total = 0
            with torch.no_grad():
                for inputs, targets in val_loader:
                    inputs = inputs.to(device)
                    targets = targets.to(device)
                    
                    outputs = model(inputs)
                    _, preds = torch.max(outputs, 1)
                    
                    correct += (preds == targets).sum().item()
                    total += targets.size(0)
            
            val_acc = correct / total if total > 0 else 0.0
            
            # Checkpoint best model
            if val_acc >= best_val_acc:
                best_val_acc = val_acc
                best_model_wts = copy.deepcopy(model.state_dict())
            
            scheduler.step()
        
        # Load best weights before returning
        model.load_state_dict(best_model_wts)
        return model