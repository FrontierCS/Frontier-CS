import torch
import torch.nn as nn
import torch.optim as optim
from copy import deepcopy

class ParetoMLP(nn.Module):
    """
    A Multi-Layer Perceptron designed to maximize parameter usage under a 1M limit.
    Architecture:
        - Input (384) -> Linear(1024) -> BN -> GELU -> Dropout
        - -> Linear(520) -> BN -> GELU -> Dropout
        - -> Linear(128) -> Output
    Parameter Count: ~997,016
    """
    def __init__(self, input_dim: int, num_classes: int):
        super().__init__()
        self.layers = nn.Sequential(
            nn.Linear(input_dim, 1024),
            nn.BatchNorm1d(1024),
            nn.GELU(),
            nn.Dropout(0.4),

            nn.Linear(1024, 520),
            nn.BatchNorm1d(520),
            nn.GELU(),
            nn.Dropout(0.3),

            nn.Linear(520, num_classes)
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
                - device: str ("cpu")
        
        Returns:
            Trained torch.nn.Module ready for evaluation
        """
        device = torch.device(metadata.get("device", "cpu"))
        input_dim = metadata["input_dim"]
        num_classes = metadata["num_classes"]

        model = ParetoMLP(input_dim=input_dim, num_classes=num_classes).to(device)

        # Training Hyperparameters
        NUM_EPOCHS = 400
        MAX_LR = 2e-3
        WEIGHT_DECAY = 0.05
        PATIENCE = 50

        criterion = nn.CrossEntropyLoss()
        optimizer = optim.AdamW(model.parameters(), lr=MAX_LR, weight_decay=WEIGHT_DECAY)
        
        scheduler = optim.lr_scheduler.OneCycleLR(
            optimizer,
            max_lr=MAX_LR,
            epochs=NUM_EPOCHS,
            steps_per_epoch=len(train_loader)
        )

        best_val_acc = 0.0
        epochs_no_improve = 0
        best_model_state = None

        for epoch in range(NUM_EPOCHS):
            # Training Phase
            model.train()
            for inputs, targets in train_loader:
                inputs, targets = inputs.to(device), targets.to(device)

                optimizer.zero_grad()
                outputs = model(inputs)
                loss = criterion(outputs, targets)
                loss.backward()
                optimizer.step()
                scheduler.step()

            # Validation Phase
            model.eval()
            val_correct = 0
            val_total = 0
            with torch.no_grad():
                for inputs, targets in val_loader:
                    inputs, targets = inputs.to(device), targets.to(device)
                    outputs = model(inputs)
                    _, predicted = torch.max(outputs.data, 1)
                    val_total += targets.size(0)
                    val_correct += (predicted == targets).sum().item()

            current_val_acc = val_correct / val_total

            # Early Stopping and Best Model Checkpointing
            if current_val_acc > best_val_acc:
                best_val_acc = current_val_acc
                best_model_state = deepcopy(model.state_dict())
                epochs_no_improve = 0
            else:
                epochs_no_improve += 1

            if epochs_no_improve >= PATIENCE:
                break

        # Load the best model state found during validation
        if best_model_state:
            model.load_state_dict(best_model_state)

        return model