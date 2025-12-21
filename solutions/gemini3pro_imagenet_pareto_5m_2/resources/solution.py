import torch
import torch.nn as nn
import torch.optim as optim
import copy

class ResBlock(nn.Module):
    def __init__(self, hidden_dim, dropout):
        super().__init__()
        self.ln1 = nn.LayerNorm(hidden_dim)
        self.linear1 = nn.Linear(hidden_dim, hidden_dim)
        self.act = nn.GELU()
        self.dropout1 = nn.Dropout(dropout)
        
        self.ln2 = nn.LayerNorm(hidden_dim)
        self.linear2 = nn.Linear(hidden_dim, hidden_dim)
        self.dropout2 = nn.Dropout(dropout)
        
    def forward(self, x):
        residual = x
        out = self.ln1(x)
        out = self.linear1(out)
        out = self.act(out)
        out = self.dropout1(out)
        
        out = self.ln2(out)
        out = self.linear2(out)
        out = self.act(out)
        out = self.dropout2(out)
        
        return residual + out

class MLPResNet(nn.Module):
    def __init__(self, input_dim, hidden_dim, num_classes, num_blocks, dropout):
        super().__init__()
        self.input_proj = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.LayerNorm(hidden_dim),
            nn.GELU(),
            nn.Dropout(dropout/2)
        )
        
        self.blocks = nn.ModuleList([
            ResBlock(hidden_dim, dropout) for _ in range(num_blocks)
        ])
        
        self.final_norm = nn.LayerNorm(hidden_dim)
        self.head = nn.Linear(hidden_dim, num_classes)
        
    def forward(self, x):
        x = self.input_proj(x)
        for block in self.blocks:
            x = block(x)
        x = self.final_norm(x)
        return self.head(x)

class Solution:
    def solve(self, train_loader, val_loader, metadata: dict = None) -> torch.nn.Module:
        input_dim = metadata.get("input_dim", 384)
        num_classes = metadata.get("num_classes", 128)
        param_limit = metadata.get("param_limit", 5000000)
        device = metadata.get("device", "cpu")
        
        # Architecture hyperparameters
        num_blocks = 6
        dropout = 0.2
        
        # Start with a safe estimate and maximize hidden_dim within budget
        # Calculation for quick estimation:
        # Params ~= 2*N*H^2 + (6N + 517)H + 128
        # For N=6, Target ~5M -> H ~ 620
        hidden_dim = 650 
        
        # Dynamically fit model to parameter constraint
        while True:
            model = MLPResNet(input_dim, hidden_dim, num_classes, num_blocks, dropout)
            params = sum(p.numel() for p in model.parameters() if p.requires_grad)
            if params <= param_limit:
                break
            hidden_dim -= 2  # Decrease width
            del model
            
        model = model.to(device)
        
        # Training Hyperparameters
        epochs = 60
        weight_decay = 0.02
        max_lr = 1e-3
        
        optimizer = optim.AdamW(model.parameters(), lr=max_lr, weight_decay=weight_decay)
        criterion = nn.CrossEntropyLoss(label_smoothing=0.1)
        
        steps_per_epoch = len(train_loader)
        scheduler = optim.lr_scheduler.OneCycleLR(
            optimizer,
            max_lr=max_lr,
            epochs=epochs,
            steps_per_epoch=steps_per_epoch,
            pct_start=0.2,
            div_factor=25.0,
            final_div_factor=1000.0
        )
        
        best_model_state = copy.deepcopy(model.state_dict())
        best_val_acc = -1.0
        
        # Training Loop
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
            
            val_acc = correct / total
            if val_acc > best_val_acc:
                best_val_acc = val_acc
                best_model_state = copy.deepcopy(model.state_dict())
        
        # Return best model found
        model.load_state_dict(best_model_state)
        return model
