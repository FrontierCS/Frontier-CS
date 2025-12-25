import torch
import torch.nn as nn
import torch.optim as optim
from torch.optim.lr_scheduler import CosineAnnealingLR

class ResBlock(nn.Module):
    """A residual block for an MLP."""
    def __init__(self, dim: int, dropout_p: float = 0.3):
        super().__init__()
        self.block = nn.Sequential(
            nn.Linear(dim, dim),
            nn.BatchNorm1d(dim),
            nn.GELU(),
            nn.Dropout(p=dropout_p),
            nn.Linear(dim, dim),
            nn.BatchNorm1d(dim),
        )
        self.activation = nn.GELU()

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        identity = x
        out = self.block(x)
        out += identity
        out = self.activation(out)
        return out

class ResNetMLP(nn.Module):
    """A ResNet-style MLP designed to maximize capacity within the parameter limit."""
    def __init__(self, input_dim: int, num_classes: int, hidden_dim: int, num_blocks: int, dropout_p: float = 0.3):
        super().__init__()
        self.initial_block = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.BatchNorm1d(hidden_dim),
            nn.GELU(),
            nn.Dropout(p=dropout_p)
        )
        
        self.res_blocks = nn.Sequential(
            *[ResBlock(hidden_dim, dropout_p) for _ in range(num_blocks)]
        )
        
        self.classifier = nn.Linear(hidden_dim, num_classes)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self.initial_block(x)
        x = self.res_blocks(x)
        x = self.classifier(x)
        return x

class Solution:
    def solve(self, train_loader: torch.utils.data.DataLoader, 
              val_loader: torch.utils.data.DataLoader, 
              metadata: dict = None) -> torch.nn.Module:
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

        # Model architecture parameters are tuned to maximize parameter count under the 2.5M limit.
        # hidden_dim=727, num_blocks=2 yields approximately 2,497,373 parameters.
        hidden_dim = 727
        num_blocks = 2
        dropout_p = 0.3

        model = ResNetMLP(
            input_dim=input_dim,
            num_classes=num_classes,
            hidden_dim=hidden_dim,
            num_blocks=num_blocks,
            dropout_p=dropout_p
        ).to(device)
        
        # Training hyperparameters
        # A longer training schedule with cosine annealing helps find a better minimum.
        # AdamW, weight decay, and label smoothing are used for regularization.
        epochs = 400
        learning_rate = 1e-3
        weight_decay = 1e-4
        label_smoothing = 0.1

        criterion = nn.CrossEntropyLoss(label_smoothing=label_smoothing)
        optimizer = optim.AdamW(model.parameters(), lr=learning_rate, weight_decay=weight_decay)
        scheduler = CosineAnnealingLR(optimizer, T_max=epochs, eta_min=1e-6)

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

        model.eval()
        return model
