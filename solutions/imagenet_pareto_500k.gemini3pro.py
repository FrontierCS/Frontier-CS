import torch
import torch.nn as nn
import torch.optim as optim
import numpy as np

class ResidualBlock(nn.Module):
    def __init__(self, dim, dropout_rate=0.3):
        super(ResidualBlock, self).__init__()
        self.net = nn.Sequential(
            nn.Linear(dim, dim),
            nn.BatchNorm1d(dim),
            nn.SiLU(),
            nn.Dropout(dropout_rate)
        )
        
    def forward(self, x):
        return x + self.net(x)

class Net(nn.Module):
    def __init__(self, input_dim, num_classes):
        super(Net, self).__init__()
        self.hidden_dim = 384
        
        # Calculate parameters to ensure strict adherence to 500k limit
        # Input BN: 384*2 = 768
        # L1 (In->H): 384*384 + 384 = 147840
        # BN1: 768
        # L2 (H->H): 147840
        # BN2: 768
        # L3 (H->H): 147840
        # BN3: 768
        # Out (H->C): 384*128 + 128 = 49280
        # Total: 495,872 < 500,000
        
        self.input_bn = nn.BatchNorm1d(input_dim)
        
        # Layer 1: Projection + Activation
        self.l1 = nn.Linear(input_dim, self.hidden_dim)
        self.bn1 = nn.BatchNorm1d(self.hidden_dim)
        self.act1 = nn.SiLU()
        self.drop1 = nn.Dropout(0.3)
        
        # Layer 2: Residual Block
        self.l2 = ResidualBlock(self.hidden_dim, dropout_rate=0.3)
        
        # Layer 3: Residual Block
        self.l3 = ResidualBlock(self.hidden_dim, dropout_rate=0.3)
        
        # Output Layer
        self.out = nn.Linear(self.hidden_dim, num_classes)
        
    def forward(self, x):
        x = self.input_bn(x)
        
        x = self.l1(x)
        x = self.bn1(x)
        x = self.act1(x)
        x = self.drop1(x)
        
        x = self.l2(x)
        x = self.l3(x)
        
        return self.out(x)

class Solution:
    def solve(self, train_loader, val_loader, metadata: dict = None) -> torch.nn.Module:
        # Extract metadata
        input_dim = metadata.get("input_dim", 384)
        num_classes = metadata.get("num_classes", 128)
        device = metadata.get("device", "cpu")
        
        # Initialize model
        model = Net(input_dim, num_classes).to(device)
        
        # Verify parameter constraint
        param_count = sum(p.numel() for p in model.parameters() if p.requires_grad)
        if param_count > 500000:
            # Fallback to a smaller model if budget exceeded (should not happen with 384/128)
            # This is a safety mechanism
            model = nn.Sequential(
                nn.Linear(input_dim, 256),
                nn.ReLU(),
                nn.Linear(256, 256),
                nn.ReLU(),
                nn.Linear(256, num_classes)
            ).to(device)
        
        # Hyperparameters
        epochs = 120
        lr = 2e-3
        weight_decay = 1e-4
        
        # Optimizer and Scheduler
        optimizer = optim.AdamW(model.parameters(), lr=lr, weight_decay=weight_decay)
        scheduler = optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=epochs, eta_min=1e-6)
        criterion = nn.CrossEntropyLoss(label_smoothing=0.1)
        
        # Training state
        best_acc = 0.0
        best_state = None
        alpha = 0.4  # Mixup alpha
        
        for epoch in range(epochs):
            model.train()
            for inputs, targets in train_loader:
                inputs, targets = inputs.to(device), targets.to(device)
                optimizer.zero_grad()
                
                # Mixup Augmentation
                if alpha > 0 and np.random.random() < 0.7:
                    lam = np.random.beta(alpha, alpha)
                    index = torch.randperm(inputs.size(0)).to(device)
                    mixed_inputs = lam * inputs + (1 - lam) * inputs[index]
                    y_a, y_b = targets, targets[index]
                    
                    outputs = model(mixed_inputs)
                    loss = lam * criterion(outputs, y_a) + (1 - lam) * criterion(outputs, y_b)
                else:
                    outputs = model(inputs)
                    loss = criterion(outputs, targets)
                
                loss.backward()
                optimizer.step()
            
            scheduler.step()
            
            # Validation
            # Validate frequently to catch peak performance on small dataset
            if epoch % 2 == 0 or epoch > epochs - 20:
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
                
                acc = correct / total
                if acc >= best_acc:
                    best_acc = acc
                    best_state = {k: v.cpu().clone() for k, v in model.state_dict().items()}
        
        # Restore best model
        if best_state is not None:
            model.load_state_dict(best_state)
            
        return model
