import torch
import torch.nn as nn
import torch.optim as optim
from copy import deepcopy

# Helper Model Classes

class ResBlock(nn.Module):
    """
    A residual block for an MLP.
    Structure: x -> Linear -> BN -> GELU -> Dropout -> Linear -> BN -> Dropout -> + x -> GELU
    """
    def __init__(self, dim, hidden_dim_multiplier=4, dropout=0.2):
        super().__init__()
        hidden_dim = int(dim * hidden_dim_multiplier)
        self.block = nn.Sequential(
            nn.Linear(dim, hidden_dim),
            nn.BatchNorm1d(hidden_dim),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim, dim),
            nn.BatchNorm1d(dim),
            nn.Dropout(dropout)
        )
        self.activation = nn.GELU()

    def forward(self, x):
        return self.activation(x + self.block(x))


class ResNetMLP(nn.Module):
    """
    A ResNet-style MLP architecture.
    """
    def __init__(self, input_dim, num_classes, hidden_dim=160, num_blocks=2, dropout=0.2):
        super().__init__()
        self.input_proj = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.BatchNorm1d(hidden_dim),
            nn.GELU()
        )
        
        self.blocks = nn.Sequential(
            *[ResBlock(hidden_dim, dropout=dropout) for _ in range(num_blocks)]
        )
        
        self.head = nn.Linear(hidden_dim, num_classes)

        # Initialize weights
        self.apply(self._init_weights)

    def _init_weights(self, m):
        if isinstance(m, nn.Linear):
            nn.init.kaiming_normal_(m.weight, mode='fan_in', nonlinearity='relu')
            if m.bias is not None:
                nn.init.zeros_(m.bias)

    def forward(self, x):
        x = self.input_proj(x)
        x = self.blocks(x)
        x = self.head(x)
        return x


class Solution:
    def solve(self, train_loader, val_loader, metadata: dict = None) -> torch.nn.Module:
        """
        Train a model and return it.
        """
        # 1. Setup
        device = torch.device(metadata.get("device", "cpu"))
        input_dim = metadata["input_dim"]
        num_classes = metadata["num_classes"]
        param_limit = metadata["param_limit"]

        # 2. Model Initialization
        # This architecture is designed to be close to the 500k parameter limit
        # hidden_dim=160, num_blocks=2 results in ~497k parameters
        model = ResNetMLP(
            input_dim=input_dim,
            num_classes=num_classes,
            hidden_dim=160,
            num_blocks=2,
            dropout=0.25
        ).to(device)

        # Verify parameter count
        param_count = sum(p.numel() for p in model.parameters() if p.requires_grad)
        if param_count > param_limit:
            # This should not happen with the current architecture, but as a safeguard
            raise ValueError(f"Model exceeds parameter limit: {param_count} > {param_limit}")

        # 3. Training Hyperparameters
        EPOCHS = 450
        MAX_LR = 2e-3
        WEIGHT_DECAY = 0.02
        LABEL_SMOOTHING = 0.1

        # 4. Training Setup
        criterion = nn.CrossEntropyLoss(label_smoothing=LABEL_SMOOTHING)
        optimizer = optim.AdamW(model.parameters(), lr=MAX_LR, weight_decay=WEIGHT_DECAY)
        scheduler = optim.lr_scheduler.OneCycleLR(
            optimizer,
            max_lr=MAX_LR,
            steps_per_epoch=len(train_loader),
            epochs=EPOCHS,
            pct_start=0.1
        )

        # 5. Training Loop
        best_val_acc = 0.0
        best_model_state = None

        for epoch in range(EPOCHS):
            # Training phase
            model.train()
            for inputs, targets in train_loader:
                inputs, targets = inputs.to(device), targets.to(device)

                optimizer.zero_grad(set_to_none=True)
                
                outputs = model(inputs)
                loss = criterion(outputs, targets)
                
                loss.backward()
                optimizer.step()
                scheduler.step()

            # Validation phase
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
            if val_acc > best_val_acc:
                best_val_acc = val_acc
                # Use deepcopy to ensure the state is fully independent
                best_model_state = deepcopy(model.state_dict())

        # 6. Load best model and return
        if best_model_state:
            model.load_state_dict(best_model_state)

        return model.to("cpu")
