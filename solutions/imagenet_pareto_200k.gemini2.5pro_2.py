import torch
import torch.nn as nn
import torch.optim as optim
from torch.optim.lr_scheduler import CosineAnnealingLR
import copy

class _ParetoMLP(nn.Module):
    def __init__(self, input_dim: int, num_classes: int, dropout_rate: float = 0.4):
        super().__init__()
        # This architecture is designed to stay under the 200k parameter limit
        # while providing sufficient capacity and strong regularization.
        #
        # Parameter Calculation:
        # Layer 1 (384 -> 256):
        #   - Linear: 384 * 256 + 256 = 98,560
        #   - BatchNorm1d: 2 * 256 = 512
        # Layer 2 (256 -> 256):
        #   - Linear: 256 * 256 + 256 = 65,792
        #   - BatchNorm1d: 2 * 256 = 512
        # Layer 3 (256 -> 128):
        #   - Linear: 256 * 128 + 128 = 32,896
        # Total Parameters = 98560 + 512 + 65792 + 512 + 32896 = 198,272
        # This is safely below the 200,000 limit.
        self.layers = nn.Sequential(
            nn.Linear(input_dim, 256),
            nn.BatchNorm1d(256),
            nn.ReLU(inplace=True),
            nn.Dropout(p=dropout_rate),

            nn.Linear(256, 256),
            nn.BatchNorm1d(256),
            nn.ReLU(inplace=True),
            nn.Dropout(p=dropout_rate),

            nn.Linear(256, num_classes)
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
                - num_classes: int
                - input_dim: int
                - param_limit: int
                - device: str
        
        Returns:
            Trained torch.nn.Module ready for evaluation
        """
        device = torch.device(metadata.get("device", "cpu"))
        input_dim = metadata["input_dim"]
        num_classes = metadata["num_classes"]

        model = _ParetoMLP(
            input_dim=input_dim,
            num_classes=num_classes,
            dropout_rate=0.4
        ).to(device)

        epochs = 250
        learning_rate = 1e-3
        weight_decay = 1e-4
        label_smoothing = 0.1
        early_stopping_patience = 30

        optimizer = optim.AdamW(model.parameters(), lr=learning_rate, weight_decay=weight_decay)
        scheduler = CosineAnnealingLR(optimizer, T_max=epochs, eta_min=1e-6)
        criterion = nn.CrossEntropyLoss(label_smoothing=label_smoothing)

        best_val_acc = 0.0
        best_model_state = None
        epochs_without_improvement = 0

        for epoch in range(epochs):
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

            # Update learning rate scheduler
            scheduler.step()

            # Early stopping logic
            if val_acc > best_val_acc:
                best_val_acc = val_acc
                best_model_state = copy.deepcopy(model.state_dict())
                epochs_without_improvement = 0
            else:
                epochs_without_improvement += 1
            
            if epochs_without_improvement >= early_stopping_patience:
                break

        # Load the best performing model state
        if best_model_state:
            model.load_state_dict(best_model_state)
            
        return model
