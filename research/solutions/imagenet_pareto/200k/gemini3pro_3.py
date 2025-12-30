import torch
import torch.nn as nn
import torch.optim as optim
import numpy as np

class AdaptiveMLP(nn.Module):
    def __init__(self, input_dim, num_classes):
        super(AdaptiveMLP, self).__init__()
        
        # Architecture designed to maximize capacity within 200,000 parameter budget
        # Budget calculation:
        # L1 (384 -> 320): 384*320 (w) + 320*2 (bn) = 122,880 + 640 = 123,520
        # L2 (320 -> 160): 320*160 (w) + 160*2 (bn) = 51,200 + 320 = 51,520
        # L3 (160 -> 128): 160*128 (w) + 128 (b)   = 20,480 + 128 = 20,608
        # Total: ~195,648 parameters (< 200,000 constraint)
        
        self.features = nn.Sequential(
            nn.Linear(input_dim, 320, bias=False),
            nn.BatchNorm1d(320),
            nn.ReLU(),
            nn.Dropout(0.3),
            
            nn.Linear(320, 160, bias=False),
            nn.BatchNorm1d(160),
            nn.ReLU(),
            nn.Dropout(0.3)
        )
        
        self.classifier = nn.Linear(160, num_classes)
        
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
        x = self.features(x)
        x = self.classifier(x)
        return x

class Solution:
    def solve(self, train_loader, val_loader, metadata: dict = None) -> torch.nn.Module:
        """
        Train a model and return it.
        """
        # Extract metadata
        input_dim = metadata.get("input_dim", 384)
        num_classes = metadata.get("num_classes", 128)
        device = metadata.get("device", "cpu")
        
        # Instantiate model
        model = AdaptiveMLP(input_dim, num_classes).to(device)
        
        # Optimization setup
        # AdamW with Cosine Annealing is robust for small/synthetic datasets
        optimizer = optim.AdamW(model.parameters(), lr=0.002, weight_decay=0.01)
        
        epochs = 75
        scheduler = optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=epochs, eta_min=1e-5)
        
        # Loss with label smoothing for regularization
        criterion = nn.CrossEntropyLoss(label_smoothing=0.1)
        
        best_acc = 0.0
        best_state = model.state_dict()
        
        # Training loop
        for epoch in range(epochs):
            model.train()
            for inputs, targets in train_loader:
                inputs, targets = inputs.to(device), targets.to(device)
                
                # Mixup augmentation
                # Helps significantly with small datasets (2048 samples) and prevents overfitting
                if np.random.random() < 0.6:
                    alpha = 0.4
                    lam = np.random.beta(alpha, alpha)
                    index = torch.randperm(inputs.size(0)).to(device)
                    
                    mixed_inputs = lam * inputs + (1 - lam) * inputs[index]
                    y_a, y_b = targets, targets[index]
                    
                    outputs = model(mixed_inputs)
                    loss = lam * criterion(outputs, y_a) + (1 - lam) * criterion(outputs, y_b)
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
                    _, predicted = torch.max(outputs.data, 1)
                    total += targets.size(0)
                    correct += (predicted == targets).sum().item()
            
            val_acc = correct / total
            
            # Checkpoint best model
            if val_acc > best_acc:
                best_acc = val_acc
                # Save state to CPU to avoid memory issues if on GPU (though this env is CPU)
                best_state = {k: v.cpu() for k, v in model.state_dict().items()}
        
        # Restore best model
        model.load_state_dict(best_state)
        model.to(device)
        
        return model