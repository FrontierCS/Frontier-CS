import torch
import torch.nn as nn
import torch.optim as optim
import copy
import numpy as np

class ResBlock(nn.Module):
    def __init__(self, dim, dropout_rate=0.1):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(dim, dim),
            nn.BatchNorm1d(dim),
            nn.GELU(),
            nn.Dropout(dropout_rate),
            nn.Linear(dim, dim),
            nn.BatchNorm1d(dim),
            nn.GELU(),
            nn.Dropout(dropout_rate)
        )
        
    def forward(self, x):
        return x + self.net(x)

class BaseNetwork(nn.Module):
    def __init__(self, input_dim, num_classes, hidden_dim=720, dropout_rate=0.2):
        super().__init__()
        # Architecture designed to fit 2 models within 5M parameters
        # Hidden dim 720 -> ~2.45M params per model -> ~4.9M total for ensemble
        
        self.input_proj = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.BatchNorm1d(hidden_dim),
            nn.GELU(),
            nn.Dropout(dropout_rate)
        )
        
        self.blocks = nn.Sequential(
            ResBlock(hidden_dim, dropout_rate),
            ResBlock(hidden_dim, dropout_rate)
        )
        
        self.head = nn.Linear(hidden_dim, num_classes)
        
    def forward(self, x):
        x = self.input_proj(x)
        x = self.blocks(x)
        return self.head(x)

class Ensemble(nn.Module):
    def __init__(self, models):
        super().__init__()
        self.models = nn.ModuleList(models)
        
    def forward(self, x):
        outputs = [m(x) for m in self.models]
        return torch.stack(outputs).mean(dim=0)

class Solution:
    def solve(self, train_loader, val_loader, metadata: dict = None) -> torch.nn.Module:
        """
        Train a model and return it.
        Strategy: Ensemble of 2 Residual MLPs to maximize accuracy within 5M parameter budget.
        """
        input_dim = metadata["input_dim"]
        num_classes = metadata["num_classes"]
        device = metadata.get("device", "cpu")
        
        # Configuration
        # H=720 results in ~2.45M params per model. 2 models = ~4.9M.
        hidden_dim = 720 
        dropout = 0.25
        num_models = 2
        epochs = 50
        learning_rate = 0.001
        
        trained_models = []
        
        for i in range(num_models):
            # Initialize model
            model = BaseNetwork(input_dim, num_classes, hidden_dim, dropout).to(device)
            
            optimizer = optim.AdamW(model.parameters(), lr=learning_rate, weight_decay=0.01)
            criterion = nn.CrossEntropyLoss()
            
            scheduler = optim.lr_scheduler.OneCycleLR(
                optimizer, 
                max_lr=learning_rate, 
                epochs=epochs, 
                steps_per_epoch=len(train_loader)
            )
            
            best_val_acc = 0.0
            best_model_state = copy.deepcopy(model.state_dict())
            
            for epoch in range(epochs):
                model.train()
                for inputs, targets in train_loader:
                    inputs, targets = inputs.to(device), targets.to(device)
                    
                    # Mixup Augmentation
                    if np.random.random() < 0.6: 
                        lam = np.random.beta(1.0, 1.0)
                        index = torch.randperm(inputs.size(0)).to(device)
                        mixed_inputs = lam * inputs + (1 - lam) * inputs[index]
                        target_a, target_b = targets, targets[index]
                        
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
                        _, predicted = outputs.max(1)
                        total += targets.size(0)
                        correct += predicted.eq(targets).sum().item()
                
                acc = correct / total
                if acc > best_val_acc:
                    best_val_acc = acc
                    best_model_state = copy.deepcopy(model.state_dict())
            
            # Load best state for this model
            model.load_state_dict(best_model_state)
            # Move to cpu to save GPU memory if applicable during next training, 
            # though env is CPU-only, this is good practice.
            # We will move back to device at the end if needed, but Ensemble handles it.
            trained_models.append(model)
            
        # Create Ensemble
        ensemble = Ensemble(trained_models).to(device)
        return ensemble