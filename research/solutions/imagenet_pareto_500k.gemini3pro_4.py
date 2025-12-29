import torch
import torch.nn as nn
import torch.optim as optim
import copy

class ResidualBlock(nn.Module):
    def __init__(self, input_dim, hidden_dim, dropout=0.2):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.BatchNorm1d(hidden_dim),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim, input_dim),
            nn.BatchNorm1d(input_dim),
            nn.GELU(),
            nn.Dropout(dropout)
        )

    def forward(self, x):
        return x + self.net(x)

class ParetoModel(nn.Module):
    def __init__(self, input_dim, num_classes, hidden_dim, num_blocks, dropout=0.2):
        super().__init__()
        # Normalization for input features
        self.input_bn = nn.BatchNorm1d(input_dim)
        
        # Stack of residual bottleneck blocks
        layers = []
        for _ in range(num_blocks):
            layers.append(ResidualBlock(input_dim, hidden_dim, dropout))
        self.blocks = nn.Sequential(*layers)
        
        # Final classifier
        self.classifier = nn.Linear(input_dim, num_classes)

    def forward(self, x):
        x = self.input_bn(x)
        x = self.blocks(x)
        return self.classifier(x)

class Solution:
    def solve(self, train_loader, val_loader, metadata: dict = None) -> torch.nn.Module:
        """
        Train a model and return it.
        """
        # Default metadata if None
        if metadata is None:
            metadata = {}
            
        input_dim = metadata.get("input_dim", 384)
        num_classes = metadata.get("num_classes", 128)
        param_limit = metadata.get("param_limit", 500000)
        device = metadata.get("device", "cpu")
        
        # Architecture hyperparameters
        num_blocks = 3
        
        # Calculate maximum hidden dimension to fit within parameter budget
        # Params breakdown:
        # 1. Input BN: 2 * input_dim
        # 2. Classifier: input_dim * num_classes + num_classes
        # 3. Per Block:
        #    - Linear1: input_dim * hidden + hidden
        #    - BN1: 2 * hidden
        #    - Linear2: hidden * input_dim + input_dim
        #    - BN2: 2 * input_dim
        #    Total Per Block = 2*input_dim*hidden + 3*hidden + 3*input_dim
        
        base_cost = (2 * input_dim) + (input_dim * num_classes + num_classes)
        safety_margin = 2000 # Ensure we are strictly under
        available_budget = param_limit - base_cost - safety_margin
        
        # Cost = num_blocks * (hidden * (2*input_dim + 3) + 3*input_dim)
        # available - num_blocks * 3 * input_dim = hidden * num_blocks * (2*input_dim + 3)
        
        term_independent = num_blocks * 3 * input_dim
        coeff_hidden = num_blocks * (2 * input_dim + 3)
        
        hidden_dim = int((available_budget - term_independent) // coeff_hidden)
        
        # Instantiate model
        model = ParetoModel(input_dim, num_classes, hidden_dim, num_blocks).to(device)
        
        # Verification of parameter count
        current_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
        if current_params > param_limit:
            # Emergency reduction if calculation was off
            hidden_dim -= 10
            model = ParetoModel(input_dim, num_classes, hidden_dim, num_blocks).to(device)
            
        # Training Configuration
        epochs = 150 # Sufficient for small dataset on CPU
        optimizer = optim.AdamW(model.parameters(), lr=0.001, weight_decay=0.01)
        scheduler = optim.lr_scheduler.OneCycleLR(
            optimizer, 
            max_lr=0.001, 
            epochs=epochs, 
            steps_per_epoch=len(train_loader)
        )
        criterion = nn.CrossEntropyLoss(label_smoothing=0.1)
        
        best_acc = 0.0
        best_model_state = copy.deepcopy(model.state_dict())
        
        # Training Loop
        for epoch in range(epochs):
            model.train()
            for inputs, targets in train_loader:
                inputs, targets = inputs.to(device), targets.to(device)
                
                # Input noise injection for robustness (only first 80% epochs)
                if epoch < int(epochs * 0.8):
                    noise = torch.randn_like(inputs) * 0.05
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
                    inputs, targets = inputs.to(device), targets.to(device)
                    outputs = model(inputs)
                    _, predicted = torch.max(outputs.data, 1)
                    total += targets.size(0)
                    correct += (predicted == targets).sum().item()
            
            val_acc = correct / total
            if val_acc > best_acc:
                best_acc = val_acc
                best_model_state = copy.deepcopy(model.state_dict())
        
        # Load best model
        model.load_state_dict(best_model_state)
        return model