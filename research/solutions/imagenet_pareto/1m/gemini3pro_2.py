import torch
import torch.nn as nn
import torch.optim as optim
import copy

class ResidualBlock(nn.Module):
    def __init__(self, dim, dropout_rate=0.2):
        super().__init__()
        self.l1 = nn.Linear(dim, dim)
        self.bn1 = nn.BatchNorm1d(dim)
        self.act = nn.GELU()
        self.dropout = nn.Dropout(dropout_rate)
        self.l2 = nn.Linear(dim, dim)
        self.bn2 = nn.BatchNorm1d(dim)

    def forward(self, x):
        identity = x
        out = self.l1(x)
        out = self.bn1(out)
        out = self.act(out)
        out = self.dropout(out)
        out = self.l2(out)
        out = self.bn2(out)
        out += identity
        out = self.act(out)
        return out

class ResNetMLP(nn.Module):
    def __init__(self, input_dim, num_classes):
        super().__init__()
        # Architecture designed to maximize capacity within 1M parameter budget
        # H = 576 results in ~963,776 parameters
        # Calculation:
        # Input (384->576): 221,184
        # ResBlock (2x 576->576): 663,552
        # Output (576->128): 73,728
        # BN + Bias: ~5k
        # Total: ~964k < 1M limit
        self.hidden_dim = 576 
        
        self.input_proj = nn.Linear(input_dim, self.hidden_dim)
        self.bn_in = nn.BatchNorm1d(self.hidden_dim)
        self.act = nn.GELU()
        self.dropout = nn.Dropout(0.2)
        
        self.block = ResidualBlock(self.hidden_dim, dropout_rate=0.2)
        
        self.output = nn.Linear(self.hidden_dim, num_classes)
        
    def forward(self, x):
        x = self.input_proj(x)
        x = self.bn_in(x)
        x = self.act(x)
        x = self.dropout(x)
        x = self.block(x)
        x = self.output(x)
        return x

class Solution:
    def solve(self, train_loader, val_loader, metadata: dict = None) -> torch.nn.Module:
        """
        Train a model and return it.
        """
        input_dim = metadata["input_dim"]
        num_classes = metadata["num_classes"]
        device = metadata.get("device", "cpu")
        
        # Initialize model
        model = ResNetMLP(input_dim, num_classes).to(device)
        
        # Verify parameter count constraint
        param_count = sum(p.numel() for p in model.parameters() if p.requires_grad)
        if param_count > 1000000:
            # Emergency fallback to smaller model if somehow over limit
            # (Should not happen with H=576)
            model.hidden_dim = 512
            model.input_proj = nn.Linear(input_dim, 512).to(device)
            model.bn_in = nn.BatchNorm1d(512).to(device)
            model.block = ResidualBlock(512).to(device)
            model.output = nn.Linear(512, num_classes).to(device)

        # Optimization setup
        # High weight decay for regularization on small dataset
        optimizer = optim.AdamW(model.parameters(), lr=0.001, weight_decay=0.05)
        
        # Training parameters
        epochs = 100
        scheduler = optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=epochs, eta_min=1e-6)
        criterion = nn.CrossEntropyLoss(label_smoothing=0.1)
        
        best_acc = 0.0
        best_model_state = copy.deepcopy(model.state_dict())
        
        # Training loop
        for epoch in range(epochs):
            model.train()
            for inputs, targets in train_loader:
                inputs, targets = inputs.to(device), targets.to(device)
                
                # Noise injection for robustness (only in earlier epochs)
                if epoch < epochs * 0.8:
                    noise = torch.randn_like(inputs) * 0.05
                    inputs = inputs + noise
                
                optimizer.zero_grad()
                outputs = model(inputs)
                loss = criterion(outputs, targets)
                loss.backward()
                optimizer.step()
            
            scheduler.step()
            
            # Validation
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
                    best_model_state = copy.deepcopy(model.state_dict())
        
        # Return best model found
        model.load_state_dict(best_model_state)
        return model