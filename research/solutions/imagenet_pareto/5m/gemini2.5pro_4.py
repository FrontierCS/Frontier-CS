import torch
import torch.nn as nn
import torch.optim as optim
from tqdm import tqdm

class ResBlock(nn.Module):
    """
    A residual block for an MLP, featuring two linear layers,
    batch normalization, GELU activation, and dropout.
    """
    def __init__(self, dim, dropout_rate=0.2):
        super().__init__()
        self.block = nn.Sequential(
            nn.Linear(dim, dim),
            nn.BatchNorm1d(dim),
            nn.GELU(),
            nn.Dropout(p=dropout_rate),
            nn.Linear(dim, dim),
            nn.BatchNorm1d(dim),
            nn.Dropout(p=dropout_rate)
        )
        self.activation = nn.GELU()

    def forward(self, x):
        identity = x
        out = self.block(x)
        out += identity
        out = self.activation(out)
        return out

class ParetoMLP(nn.Module):
    """
    A deep MLP with residual connections optimized for the parameter budget.
    """
    def __init__(self, input_dim, num_classes, hidden_dim, n_blocks, dropout_rate):
        super().__init__()
        
        self.input_layer = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.BatchNorm1d(hidden_dim),
            nn.GELU()
        )
        
        blocks = [ResBlock(hidden_dim, dropout_rate) for _ in range(n_blocks)]
        self.blocks = nn.Sequential(*blocks)
        
        self.output_layer = nn.Linear(hidden_dim, num_classes)

        self._initialize_weights()

    def _initialize_weights(self):
        for m in self.modules():
            if isinstance(m, nn.Linear):
                nn.init.kaiming_normal_(m.weight, mode='fan_in', nonlinearity='relu')
                if m.bias is not None:
                    nn.init.constant_(m.bias, 0)

    def forward(self, x):
        x = self.input_layer(x)
        x = self.blocks(x)
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
                - param_limit: int (5,000,000)
                - baseline_accuracy: float (0.88)
                - train_samples: int
                - val_samples: int
                - test_samples: int
                - device: str ("cpu")
        
        Returns:
            Trained torch.nn.Module ready for evaluation
        """
        device = metadata.get("device", "cpu")
        input_dim = metadata["input_dim"]
        num_classes = metadata["num_classes"]
        
        # --- Hyperparameters ---
        # Architecture tuned to be just under 5M parameters (~4.985M)
        HIDDEN_DIM = 622
        N_BLOCKS = 6
        
        # Training regimen
        N_EPOCHS = 500
        MAX_LR = 1.2e-3
        WEIGHT_DECAY = 0.01
        DROPOUT_RATE = 0.2
        LABEL_SMOOTHING = 0.1

        # --- Model Initialization ---
        model = ParetoMLP(
            input_dim=input_dim,
            num_classes=num_classes,
            hidden_dim=HIDDEN_DIM,
            n_blocks=N_BLOCKS,
            dropout_rate=DROPOUT_RATE
        ).to(device)

        # --- Training Setup ---
        criterion = nn.CrossEntropyLoss(label_smoothing=LABEL_SMOOTHING)
        optimizer = optim.AdamW(model.parameters(), lr=MAX_LR, weight_decay=WEIGHT_DECAY)
        
        total_steps = N_EPOCHS * len(train_loader)
        scheduler = optim.lr_scheduler.OneCycleLR(
            optimizer, 
            max_lr=MAX_LR, 
            total_steps=total_steps,
            pct_start=0.1
        )

        # --- Training Loop ---
        model.train()
        for epoch in range(N_EPOCHS):
            for inputs, targets in train_loader:
                inputs, targets = inputs.to(device), targets.to(device)
                
                optimizer.zero_grad()
                outputs = model(inputs)
                loss = criterion(outputs, targets)
                loss.backward()
                optimizer.step()
                scheduler.step()

        return model