import torch
import torch.nn as nn
import torch.optim as optim
import math
import copy

class ResidualBlock(nn.Module):
    def __init__(self, dim, dropout_rate):
        super().__init__()
        self.linear = nn.Linear(dim, dim)
        self.bn = nn.BatchNorm1d(dim)
        self.relu = nn.ReLU()
        self.dropout = nn.Dropout(dropout_rate)

    def forward(self, x):
        residual = x
        out = self.linear(x)
        out = self.bn(out)
        out = self.relu(out)
        out = self.dropout(out)
        return out + residual

class Net(nn.Module):
    def __init__(self, input_dim, num_classes, hidden_dim, dropout_rate):
        super().__init__()
        # Initial projection
        self.input_layer = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.BatchNorm1d(hidden_dim),
            nn.ReLU(),
            nn.Dropout(dropout_rate)
        )
        
        # Residual processing
        self.res1 = ResidualBlock(hidden_dim, dropout_rate)
        self.res2 = ResidualBlock(hidden_dim, dropout_rate)
        
        # Classification head
        self.output_layer = nn.Linear(hidden_dim, num_classes)

    def forward(self, x):
        x = self.input_layer(x)
        x = self.res1(x)
        x = self.res2(x)
        x = self.output_layer(x)
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
        param_limit = metadata.get("param_limit", 1000000)
        
        # Dynamic architecture sizing to maximize capacity within budget
        # Parameter count formula approximation:
        # Layer0: hidden*(input + 1) + 2*hidden (BN) -> hidden*(input + 3)
        # Res1: hidden*(hidden + 1) + 2*hidden (BN) -> hidden*(hidden + 3)
        # Res2: hidden*(hidden + 1) + 2*hidden (BN) -> hidden*(hidden + 3)
        # Head: num_classes*(hidden + 1)
        # Total ≈ 2*hidden^2 + hidden*(input + num_classes + 9) + num_classes
        
        a = 2
        b = input_dim + num_classes + 9
        c = num_classes - param_limit
        
        # Quadratic formula: ax^2 + bx + c = 0
        discriminant = b**2 - 4*a*c
        max_hidden = int((-b + math.sqrt(discriminant)) / (2*a))
        
        # Use a safe margin to ensure we are strictly under the limit
        hidden_dim = max_hidden - 2
        
        # Hyperparameters
        dropout_rate = 0.45  # High dropout for small dataset/noise
        learning_rate = 0.001
        weight_decay = 0.02
        epochs = 75
        
        # Initialize model
        model = Net(input_dim, num_classes, hidden_dim, dropout_rate)
        model = model.to(device)
        
        # Strict parameter limit enforcement
        current_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
        if current_params > param_limit:
            # Reduce width if calculation was off
            ratio = (param_limit / current_params) ** 0.5
            hidden_dim = int(hidden_dim * ratio * 0.95)
            model = Net(input_dim, num_classes, hidden_dim, dropout_rate)
            model = model.to(device)
            
        # Optimization setup
        optimizer = optim.AdamW(model.parameters(), lr=learning_rate, weight_decay=weight_decay)
        criterion = nn.CrossEntropyLoss(label_smoothing=0.1)
        
        # Learning rate scheduler
        steps_per_epoch = len(train_loader)
        scheduler = optim.lr_scheduler.OneCycleLR(
            optimizer,
            max_lr=learning_rate * 2,
            epochs=epochs,
            steps_per_epoch=steps_per_epoch
        )
        
        best_acc = 0.0
        best_model_state = copy.deepcopy(model.state_dict())
        
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
                    preds = outputs.argmax(dim=1)
                    correct += (preds == targets).sum().item()
                    total += targets.size(0)
            
            acc = correct / total
            if acc >= best_acc:
                best_acc = acc
                best_model_state = copy.deepcopy(model.state_dict())
        
        # Return best model
        model.load_state_dict(best_model_state)
        return model
