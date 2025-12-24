import torch
import torch.nn as nn
import torch.optim as optim
import copy

# Define model architecture outside the Solution class for clarity
class ResBlock(nn.Module):
    """A residual block for an MLP with a bottleneck design."""
    def __init__(self, dim, bottleneck_dim, dropout=0.25):
        super().__init__()
        self.block = nn.Sequential(
            nn.Linear(dim, bottleneck_dim),
            nn.BatchNorm1d(bottleneck_dim),
            nn.GELU(),
            nn.Dropout(p=dropout),
            nn.Linear(bottleneck_dim, dim),
            nn.BatchNorm1d(dim),
        )
        self.activation = nn.GELU()
        self.dropout = nn.Dropout(p=dropout)

    def forward(self, x):
        identity = x
        out = self.block(x)
        out = out + identity
        out = self.activation(out)
        out = self.dropout(out)
        return out

class ParetoMLP(nn.Module):
    """
    An MLP designed to maximize accuracy under a 200K parameter constraint.
    It uses a residual block with a bottleneck design for parameter efficiency and depth.
    - Parameter count is ~198,656.
    """
    def __init__(self, input_dim, num_classes, hidden_dim=256, bottleneck_dim=128, dropout=0.25):
        super().__init__()
        self.net = nn.Sequential(
            # Input projection layer
            nn.Linear(input_dim, hidden_dim),
            nn.BatchNorm1d(hidden_dim),
            nn.GELU(),
            nn.Dropout(p=dropout),
            
            # Residual block
            ResBlock(hidden_dim, bottleneck_dim, dropout),
            
            # Output classifier head
            nn.Linear(hidden_dim, num_classes)
        )

    def forward(self, x):
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
                - param_limit: int (200,000)
                - baseline_accuracy: float (0.65)
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

        # Instantiate the model
        model = ParetoMLP(
            input_dim=input_dim,
            num_classes=num_classes,
            hidden_dim=256,
            bottleneck_dim=128,
            dropout=0.25
        ).to(device)
        
        # Hyperparameters tuned for this problem
        EPOCHS = 400
        MAX_LR = 2e-3
        WEIGHT_DECAY = 1.5e-2
        LABEL_SMOOTHING = 0.1

        # Setup for training: Loss, Optimizer, Scheduler
        criterion = nn.CrossEntropyLoss(label_smoothing=LABEL_SMOOTHING)
        optimizer = optim.AdamW(model.parameters(), lr=MAX_LR, weight_decay=WEIGHT_DECAY)
        
        total_steps = len(train_loader) * EPOCHS
        scheduler = optim.lr_scheduler.OneCycleLR(optimizer, max_lr=MAX_LR, total_steps=total_steps)

        best_val_accuracy = 0.0
        best_model_state = None

        # Main training loop
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
            
            current_val_accuracy = correct / total
            
            # Save the model with the best validation accuracy
            if current_val_accuracy > best_val_accuracy:
                best_val_accuracy = current_val_accuracy
                # Use deepcopy to ensure the state is fully saved at this point
                best_model_state = copy.deepcopy(model.state_dict())

        # Load the best model state before returning
        if best_model_state:
            model.load_state_dict(best_model_state)
        
        model.eval()
        return model
