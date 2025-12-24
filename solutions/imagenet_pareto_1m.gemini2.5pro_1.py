import torch
import torch.nn as nn
import torch.optim as optim
from torch.optim.lr_scheduler import CosineAnnealingLR
import copy

class Net(nn.Module):
    def __init__(self, input_dim: int, num_classes: int):
        super().__init__()
        # This architecture is designed to be close to the 1,000,000 parameter limit.
        # L1 (384 -> 1200): 384 * 1200 + 1200 = 462,000
        # BN1 (1200): 2 * 1200 = 2,400
        # L2 (1200 -> 402): 1200 * 402 + 402 = 482,802
        # BN2 (402): 2 * 402 = 804
        # L3 (402 -> 128): 402 * 128 + 128 = 51,584
        # Total parameters: 462000 + 2400 + 482802 + 804 + 51584 = 999,590
        self.layers = nn.Sequential(
            nn.Linear(input_dim, 1200),
            nn.BatchNorm1d(1200),
            nn.ReLU(inplace=True),
            nn.Dropout(0.4),

            nn.Linear(1200, 402),
            nn.BatchNorm1d(402),
            nn.ReLU(inplace=True),
            nn.Dropout(0.2),

            nn.Linear(402, num_classes)
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
        input_dim = metadata["input_dim"]
        num_classes = metadata["num_classes"]

        model = Net(input_dim, num_classes).to(device)

        # Hyperparameters chosen for robust training on a small dataset
        EPOCHS = 350
        LEARNING_RATE = 0.001
        WEIGHT_DECAY = 1e-5
        PATIENCE = 40  # Patience for early stopping

        optimizer = optim.AdamW(model.parameters(), lr=LEARNING_RATE, weight_decay=WEIGHT_DECAY)
        criterion = nn.CrossEntropyLoss()
        scheduler = CosineAnnealingLR(optimizer, T_max=EPOCHS, eta_min=0)

        best_val_loss = float('inf')
        epochs_without_improvement = 0
        best_model_state_dict = None

        for epoch in range(EPOCHS):
            # Training phase
            model.train()
            for inputs, targets in train_loader:
                inputs, targets = inputs.to(device), targets.to(device)
                
                optimizer.zero_grad()
                outputs = model(inputs)
                loss = criterion(outputs, targets)
                loss.backward()
                optimizer.step()

            # Validation phase
            model.eval()
            current_val_loss = 0.0
            with torch.no_grad():
                for inputs, targets in val_loader:
                    inputs, targets = inputs.to(device), targets.to(device)
                    outputs = model(inputs)
                    loss = criterion(outputs, targets)
                    current_val_loss += loss.item()
            
            current_val_loss /= len(val_loader)
            
            scheduler.step()

            # Early stopping and model checkpointing
            if current_val_loss < best_val_loss:
                best_val_loss = current_val_loss
                epochs_without_improvement = 0
                # Use deepcopy to ensure the state is fully independent
                best_model_state_dict = copy.deepcopy(model.state_dict())
            else:
                epochs_without_improvement += 1
            
            if epochs_without_improvement >= PATIENCE:
                break
        
        # Load the best model weights found during training
        if best_model_state_dict is not None:
            model.load_state_dict(best_model_state_dict)
            
        return model
