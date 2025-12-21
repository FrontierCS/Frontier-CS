import torch
import torch.nn as nn
import torch.optim as optim
import numpy as np

class ResidualBlock(nn.Module):
    def __init__(self, hidden_dim, dropout_rate):
        super().__init__()
        self.ln1 = nn.LayerNorm(hidden_dim)
        self.fc1 = nn.Linear(hidden_dim, hidden_dim)
        self.gelu = nn.GELU()
        self.dropout1 = nn.Dropout(dropout_rate)
        self.ln2 = nn.LayerNorm(hidden_dim)
        self.fc2 = nn.Linear(hidden_dim, hidden_dim)
        self.dropout2 = nn.Dropout(dropout_rate)
        
    def forward(self, x):
        residual = x
        x = self.ln1(x)
        x = self.fc1(x)
        x = self.gelu(x)
        x = self.dropout1(x)
        x = self.ln2(x)
        x = self.fc2(x)
        x = self.gelu(x)
        x = self.dropout2(x)
        return residual + x

class ParetoModel(nn.Module):
    def __init__(self, input_dim, num_classes, hidden_dim, num_blocks, dropout_rate):
        super().__init__()
        self.input_proj = nn.Linear(input_dim, hidden_dim)
        self.blocks = nn.ModuleList([
            ResidualBlock(hidden_dim, dropout_rate) for _ in range(num_blocks)
        ])
        self.norm = nn.LayerNorm(hidden_dim)
        self.output_head = nn.Linear(hidden_dim, num_classes)
        
    def forward(self, x):
        x = self.input_proj(x)
        for block in self.blocks:
            x = block(x)
        x = self.norm(x)
        x = self.output_head(x)
        return x

class Solution:
    def solve(self, train_loader, val_loader, metadata: dict = None) -> torch.nn.Module:
        """
        Train a model and return it.
        """
        # Extract metadata with defaults
        input_dim = metadata.get("input_dim", 384)
        num_classes = metadata.get("num_classes", 128)
        param_limit = metadata.get("param_limit", 2500000)
        device = metadata.get("device", "cpu")
        
        # Configuration
        # We use a Residual MLP architecture.
        # We need to maximize hidden_dim 'h' such that total params <= param_limit.
        num_blocks = 3
        dropout_rate = 0.25
        
        # Function to calculate parameters for a given hidden dimension
        def count_params(h, k):
            # Per ResidualBlock:
            # 2 * LayerNorm(h) -> 2 * 2h = 4h
            # 2 * Linear(h, h) -> 2 * (h*h + h) = 2h^2 + 2h
            # Block total = 2h^2 + 6h
            block_params = 2*(h*h + h) + 4*h
            
            # Total Model:
            # Input Projection: input_dim*h + h
            # K Blocks: k * block_params
            # Final Norm: 2h
            # Output Head: h*num_classes + num_classes
            total = (input_dim*h + h) + k*block_params + 2*h + (h*num_classes + num_classes)
            return total

        # Search for maximum valid hidden_dim
        # Start conservative and increment
        hidden_dim = 128
        while True:
            next_h = hidden_dim + 8  # Keep dimensions multiples of 8 for efficiency
            if count_params(next_h, num_blocks) > param_limit:
                break
            hidden_dim = next_h
            
        # Instantiate model
        model = ParetoModel(input_dim, num_classes, hidden_dim, num_blocks, dropout_rate)
        model = model.to(device)
        
        # Training Hyperparameters
        optimizer = optim.AdamW(model.parameters(), lr=1e-3, weight_decay=0.02)
        criterion = nn.CrossEntropyLoss(label_smoothing=0.1)
        epochs = 75
        
        # Learning Rate Scheduler
        scheduler = optim.lr_scheduler.OneCycleLR(
            optimizer,
            max_lr=1e-3,
            epochs=epochs,
            steps_per_epoch=len(train_loader),
            pct_start=0.15,
            div_factor=25.0,
            final_div_factor=1000.0
        )
        
        best_state = None
        best_val_acc = -1.0
        
        # Training Loop
        for epoch in range(epochs):
            model.train()
            for inputs, targets in train_loader:
                inputs, targets = inputs.to(device), targets.to(device)
                
                # Mixup Augmentation
                # Apply mixup with some probability to improve generalization
                if np.random.random() < 0.6: 
                    lam = np.random.beta(0.4, 0.4)
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
                    preds = outputs.argmax(dim=1)
                    correct += (preds == targets).sum().item()
                    total += targets.size(0)
            
            val_acc = correct / total
            
            # Save best model
            if val_acc > best_val_acc:
                best_val_acc = val_acc
                # Clone state dict to CPU to save memory and ensure device independence
                best_state = {k: v.cpu().clone() for k, v in model.state_dict().items()}
        
        # Load the best performing model weights
        if best_state is not None:
            model.load_state_dict(best_state)
            
        return model
