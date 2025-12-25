import torch
import torch.nn as nn
import torch.optim as optim
import copy

class ResidualBlock(nn.Module):
    def __init__(self, dim, dropout=0.3):
        super(ResidualBlock, self).__init__()
        self.net = nn.Sequential(
            nn.Linear(dim, dim),
            nn.BatchNorm1d(dim),
            nn.ReLU(),
            nn.Dropout(dropout)
        )

    def forward(self, x):
        return x + self.net(x)

class ParetoModel(nn.Module):
    def __init__(self, input_dim, hidden_dim, num_classes, dropout=0.3):
        super(ParetoModel, self).__init__()
        self.input_proj = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.BatchNorm1d(hidden_dim),
            nn.ReLU(),
            nn.Dropout(dropout)
        )
        
        # 3 Residual Blocks with hidden_dim=1200 keeps total params just under 5M
        self.blocks = nn.ModuleList([
            ResidualBlock(hidden_dim, dropout),
            ResidualBlock(hidden_dim, dropout),
            ResidualBlock(hidden_dim, dropout)
        ])
        
        self.output_proj = nn.Linear(hidden_dim, num_classes)

    def forward(self, x):
        x = self.input_proj(x)
        for block in self.blocks:
            x = block(x)
        return self.output_proj(x)

class Solution:
    def solve(self, train_loader, val_loader, metadata: dict = None) -> torch.nn.Module:
        input_dim = metadata["input_dim"]
        num_classes = metadata["num_classes"]
        device = metadata.get("device", "cpu")
        
        # Configuration designed for < 5,000,000 params
        # Calculation:
        # Input Layer: 384*1200 + 1200 + 2*1200 (BN) = 464,400
        # 3 x ResBlocks: 3 * (1200*1200 + 1200 + 2*1200) = 4,330,800
        # Output Layer: 1200*128 + 128 = 153,728
        # Total: 4,948,928 parameters
        HIDDEN_DIM = 1200
        DROPOUT = 0.3
        EPOCHS = 100
        LR = 1e-3
        WEIGHT_DECAY = 1e-3
        
        model = ParetoModel(input_dim, HIDDEN_DIM, num_classes, DROPOUT).to(device)
        
        # Optimizer and Scheduler
        optimizer = optim.AdamW(model.parameters(), lr=LR, weight_decay=WEIGHT_DECAY)
        scheduler = optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=EPOCHS)
        criterion = nn.CrossEntropyLoss(label_smoothing=0.1)
        
        best_acc = 0.0
        best_model_wts = copy.deepcopy(model.state_dict())
        
        # Training Loop
        for epoch in range(EPOCHS):
            model.train()
            for inputs, targets in train_loader:
                inputs = inputs.to(device)
                targets = targets.to(device)
                
                # Noise Injection Augmentation
                # Adds robustness for synthetic feature vectors
                if epoch < int(EPOCHS * 0.8):
                    noise_scale = 0.02 * (1 - epoch / EPOCHS)
                    noise = torch.randn_like(inputs) * noise_scale
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
                    inputs = inputs.to(device)
                    targets = targets.to(device)
                    outputs = model(inputs)
                    _, preds = torch.max(outputs, 1)
                    correct += (preds == targets).sum().item()
                    total += targets.size(0)
            
            val_acc = correct / total
            
            if val_acc >= best_acc:
                best_acc = val_acc
                best_model_wts = copy.deepcopy(model.state_dict())
        
        # Load best model weights
        model.load_state_dict(best_model_wts)
        return model
