import torch
import torch.nn as nn
import torch.optim as optim
from torch.optim.lr_scheduler import OneCycleLR

class _CustomMLP(nn.Module):
    """
    A custom MLP architecture designed to maximize capacity under the 200K parameter limit.
    This architecture uses ~198,272 parameters.
    It employs modern blocks: Linear -> BatchNorm -> GELU -> Dropout for regularization and stability.
    """
    def __init__(self, input_dim: int, num_classes: int, hidden_dim: int = 256, dropout_rate: float = 0.4):
        super().__init__()
        self.layers = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.BatchNorm1d(hidden_dim),
            nn.GELU(),
            nn.Dropout(dropout_rate),
            
            nn.Linear(hidden_dim, hidden_dim),
            nn.BatchNorm1d(hidden_dim),
            nn.GELU(),
            nn.Dropout(dropout_rate),

            nn.Linear(hidden_dim, num_classes)
        )
    
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.layers(x)

class Solution:
    def solve(self, train_loader, val_loader, metadata: dict = None) -> torch.nn.Module:
        """
        Train a model and return it.
        
        Args:
            train_loader: PyTorch DataLoader with training data
            val_loader: PyTorch DataLoader with validation data
            metadata: Dict with problem-specific information
        
        Returns:
            Trained torch.nn.Module ready for evaluation
        """
        device = torch.device(metadata.get("device", "cpu"))
        input_dim = metadata["input_dim"]
        num_classes = metadata["num_classes"]

        model = _CustomMLP(
            input_dim=input_dim,
            num_classes=num_classes
        ).to(device)

        # Hyperparameters are tuned for strong regularization on a small dataset
        # to combat overfitting and maximize generalization.
        epochs = 200
        max_lr = 1.2e-3
        weight_decay = 0.05
        label_smoothing = 0.1

        # Loss function with Label Smoothing to prevent over-confidence
        criterion = nn.CrossEntropyLoss(label_smoothing=label_smoothing)
        
        # AdamW optimizer is a robust choice that decouples weight decay
        optimizer = optim.AdamW(model.parameters(), lr=max_lr, weight_decay=weight_decay)
        
        # OneCycleLR scheduler for fast convergence and regularization effects
        total_steps = len(train_loader) * epochs
        scheduler = OneCycleLR(
            optimizer, 
            max_lr=max_lr, 
            total_steps=total_steps,
            pct_start=0.25,
            anneal_strategy='cos',
            div_factor=25.0,
            final_div_factor=1e4
        )

        # Training loop
        model.train()
        for epoch in range(epochs):
            for inputs, targets in train_loader:
                inputs, targets = inputs.to(device), targets.to(device)
                
                # Forward pass
                outputs = model(inputs)
                loss = criterion(outputs, targets)
                
                # Backward pass and optimization
                optimizer.zero_grad(set_to_none=True)
                loss.backward()
                optimizer.step()
                scheduler.step()
        
        model.eval()
        return model
