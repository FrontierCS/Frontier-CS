import torch
import torch.nn as nn
import torch.optim as optim

class CustomModel(nn.Module):
    """
    A custom MLP architecture designed to maximize parameter usage under the 1M limit.
    With hidden_dim=588, the total parameter count is 997,964.
    The architecture uses standard blocks of Linear -> BatchNorm -> GELU -> Dropout.
    """
    def __init__(self, input_dim: int, num_classes: int, hidden_dim: int = 588, dropout1: float = 0.2, dropout2: float = 0.4):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.BatchNorm1d(hidden_dim),
            nn.GELU(),
            nn.Dropout(dropout1),

            nn.Linear(hidden_dim, hidden_dim),
            nn.BatchNorm1d(hidden_dim),
            nn.GELU(),
            nn.Dropout(dropout2),

            nn.Linear(hidden_dim, hidden_dim),
            nn.BatchNorm1d(hidden_dim),
            nn.GELU(),
            nn.Dropout(dropout2),

            nn.Linear(hidden_dim, num_classes)
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x)


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
                - param_limit: int (1,000,000)
                - baseline_accuracy: float (0.8)
                - train_samples: int
                - val_samples: int
                - test_samples: int
                - device: str ("cpu")
        
        Returns:
            Trained torch.nn.Module ready for evaluation
        """
        device = metadata.get("device", "cpu")
        num_classes = metadata["num_classes"]
        input_dim = metadata["input_dim"]

        # Model architecture carefully designed to stay just under 1,000,000 parameters.
        # A hidden dimension of 588 results in a parameter count of 997,964.
        model = CustomModel(
            input_dim=input_dim,
            num_classes=num_classes,
            hidden_dim=588,
            dropout1=0.2,
            dropout2=0.4
        ).to(device)

        # Hyperparameters chosen for robust training on a CPU within the time limit.
        EPOCHS = 350
        LEARNING_RATE = 1e-3
        WEIGHT_DECAY = 1e-4
        LABEL_SMOOTHING = 0.1

        # Optimizer with weight decay, a scheduler for learning rate decay, and a loss function with label smoothing.
        optimizer = optim.AdamW(
            model.parameters(),
            lr=LEARNING_RATE,
            weight_decay=WEIGHT_DECAY
        )
        scheduler = optim.lr_scheduler.CosineAnnealingLR(
            optimizer,
            T_max=EPOCHS,
            eta_min=1e-6
        )
        criterion = nn.CrossEntropyLoss(label_smoothing=LABEL_SMOOTHING)

        # Training loop.
        # The model is trained for a fixed number of epochs, which is a robust strategy
        # when combined with a cosine annealing learning rate scheduler.
        # The validation loader is not used for early stopping to allow the model to train for the full duration.
        for epoch in range(EPOCHS):
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
