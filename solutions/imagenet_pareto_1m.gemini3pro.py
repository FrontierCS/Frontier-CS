import torch
import torch.nn as nn
import torch.optim as optim
import copy

class ResidualBlock(nn.Module):
    def __init__(self, hidden_dim, dropout_rate):
        super(ResidualBlock, self).__init__()
        self.block = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim),
            nn.BatchNorm1d(hidden_dim),
            nn.GELU(),
            nn.Dropout(dropout_rate)
        )

    def forward(self, x):
        return x + self.block(x)

class Model(nn.Module):
    def __init__(self, input_dim, num_classes):
        super(Model, self).__init__()
        # Architecture configured to maximize capacity within 1M parameter budget
        # Calculation:
        # Input BN: 2 * 384 = 768
        # Stem: 384 * 576 + 576 + 2 * 576 = 222,912
        # ResBlock 1: 576 * 576 + 576 + 2 * 576 = 333,504
        # ResBlock 2: 576 * 576 + 576 + 2 * 576 = 333,504
        # Head: 576 * 128 + 128 = 73,856
        # Total: ~964,544 parameters (Safe under 1,000,000 limit)
        self.hidden_dim = 576
        
        self.input_bn = nn.BatchNorm1d(input_dim)
        
        self.stem = nn.Sequential(
            nn.Linear(input_dim, self.hidden_dim),
            nn.BatchNorm1d(self.hidden_dim),
            nn.GELU(),
            nn.Dropout(0.2)
        )
        
        self.res1 = ResidualBlock(self.hidden_dim, dropout_rate=0.25)
        self.res2 = ResidualBlock(self.hidden_dim, dropout_rate=0.25)
        
        self.head = nn.Linear(self.hidden_dim, num_classes)

    def forward(self, x):
        x = self.input_bn(x)
        x = self.stem(x)
        x = self.res1(x)
        x = self.res2(x)
        return self.head(x)

class Solution:
    def solve(self, train_loader, val_loader, metadata: dict = None) -> torch.nn.Module:
        """
        Train a model on the provided data within 1M parameter budget.
        """
        input_dim = metadata.get("input_dim", 384)
        num_classes = metadata.get("num_classes", 128)
        device = metadata.get("device", "cpu")
        
        model = Model(input_dim, num_classes).to(device)
        
        # Verify parameter count constraint
        param_count = sum(p.numel() for p in model.parameters() if p.requires_grad)
        if param_count > 1000000:
            raise ValueError(f"Model exceeds parameter limit: {param_count}")

        # Optimization setup
        # Using AdamW with weight decay for regularization on small dataset
        optimizer = optim.AdamW(model.parameters(), lr=1e-3, weight_decay=0.02)
        
        # Label smoothing helps prevent overfitting on small datasets
        criterion = nn.CrossEntropyLoss(label_smoothing=0.1)
        
        epochs = 55
        # OneCycleLR typically converges faster and reaches better optima than CosineAnnealing alone
        scheduler = optim.lr_scheduler.OneCycleLR(
            optimizer, 
            max_lr=1e-3, 
            epochs=epochs, 
            steps_per_epoch=len(train_loader),
            pct_start=0.3
        )
        
        best_acc = 0.0
        best_weights = copy.deepcopy(model.state_dict())
        
        # Training loop
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
            
            # Save best model
            if acc >= best_acc:
                best_acc = acc
                best_weights = copy.deepcopy(model.state_dict())
        
        # Restore best performing model
        model.load_state_dict(best_weights)
        return model
