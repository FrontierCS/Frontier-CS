import torch
import torch.nn as nn
import torch.optim as optim
from copy import deepcopy

class ResidualBlock(nn.Module):
    """A residual block for an MLP."""
    def __init__(self, size: int, dropout_p: float):
        super().__init__()
        self.block = nn.Sequential(
            nn.Linear(size, size),
            nn.BatchNorm1d(size),
            nn.ReLU(inplace=True),
            nn.Dropout(p=dropout_p),
            nn.Linear(size, size),
            nn.BatchNorm1d(size),
        )
        self.relu = nn.ReLU(inplace=True)
        self.dropout = nn.Dropout(p=dropout_p)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        residual = x
        out = self.block(x)
        out += residual
        out = self.relu(out)
        out = self.dropout(out)
        return out

class ParetoResMLP(nn.Module):
    """A ResNet-style MLP designed for the Pareto optimization problem."""
    def __init__(self, input_dim: int, num_classes: int, hidden_dim: int, num_blocks: int, dropout_p: float):
        super().__init__()
        
        # Parameter count for (input_dim=384, hidden_dim=600, num_blocks=3, num_classes=128):
        # Input layer: (384*600+600) + (2*600) = 232,200
        # 3x ResBlocks: 3 * (2*(600*600+600) + 2*(2*600)) = 3 * 723,600 = 2,170,800
        # Output layer: 600*128+128 = 76,928
        # Total = 232,200 + 2,170,800 + 76,928 = 2,479,928 < 2,500,000

        self.input_layer = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.BatchNorm1d(hidden_dim),
            nn.ReLU(inplace=True),
            nn.Dropout(p=dropout_p)
        )
        
        self.residual_layers = nn.Sequential(
            *[ResidualBlock(hidden_dim, dropout_p) for _ in range(num_blocks)]
        )
        
        self.output_layer = nn.Linear(hidden_dim, num_classes)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self.input_layer(x)
        x = self.residual_layers(x)
        x = self.output_layer(x)
        return x

class Solution:
    def solve(self, train_loader, val_loader, metadata: dict = None) -> torch.nn.Module:
        """
        Train a model and return it.
        
        Args:
            train_loader: PyTorch DataLoader with training data
            val_loader: PyTorch DataLoader with validation data
            metadata: Dict with keys:
                - num_classes: int (128)
                - input_dim: int (384)
                - param_limit: int (2,500,000)
                - baseline_accuracy: float (0.85)
                - train_samples: int
                - val_samples: int
                - test_samples: int
                - device: str ("cpu")
        
        Returns:
            Trained torch.nn.Module ready for evaluation
        """
        device = torch.device(metadata.get("device", "cpu"))
        input_dim = metadata["input_dim"]
        num_classes = metadata["num_classes"]

        # --- Hyperparameters ---
        HIDDEN_DIM = 600
        NUM_BLOCKS = 3
        DROPOUT_P = 0.3
        
        NUM_EPOCHS = 250
        MAX_LR = 2e-3
        WEIGHT_DECAY = 5e-5

        # --- Model Initialization ---
        model = ParetoResMLP(
            input_dim=input_dim,
            num_classes=num_classes,
            hidden_dim=HIDDEN_DIM,
            num_blocks=NUM_BLOCKS,
            dropout_p=DROPOUT_P
        )
        model.to(device)

        # --- Training Setup ---
        criterion = nn.CrossEntropyLoss()
        optimizer = optim.AdamW(model.parameters(), lr=MAX_LR, weight_decay=WEIGHT_DECAY)
        
        scheduler = optim.lr_scheduler.OneCycleLR(
            optimizer, 
            max_lr=MAX_LR, 
            epochs=NUM_EPOCHS, 
            steps_per_epoch=len(train_loader)
        )

        # --- Training Loop ---
        best_val_acc = -1.0
        best_model_state = None

        for epoch in range(NUM_EPOCHS):
            # Training phase
            model.train()
            for inputs, targets in train_loader:
                inputs, targets = inputs.to(device), targets.to(device)
                
                optimizer.zero_grad()
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
                best_model_state = deepcopy(model.state_dict())
        
        # --- Finalization ---
        if best_model_state:
            model.load_state_dict(best_model_state)
            
        return model