import torch
import torch.nn as nn
import torch.optim as optim
import copy

# A deep MLP architecture designed to maximize parameter usage within the 2.5M limit
# while providing high capacity for the learning task.
class DeepMLP(nn.Module):
    def __init__(self, input_dim: int, num_classes: int):
        super().__init__()
        # Layer widths were carefully chosen to be just under the 2,500,000 parameter limit.
        # Total trainable parameters: ~2,490,428
        w1, w2, w3 = 1440, 990, 450
        
        self.layers = nn.Sequential(
            nn.Linear(input_dim, w1),
            nn.BatchNorm1d(w1),
            nn.SiLU(), # Swish activation, often performs better than ReLU/GELU
            nn.Dropout(0.4), # Tapered dropout for stronger regularization in earlier layers

            nn.Linear(w1, w2),
            nn.BatchNorm1d(w2),
            nn.SiLU(),
            nn.Dropout(0.3),

            nn.Linear(w2, w3),
            nn.BatchNorm1d(w3),
            nn.SiLU(),
            nn.Dropout(0.2),

            nn.Linear(w3, num_classes)
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

        model = DeepMLP(input_dim, num_classes).to(device)
        
        # Hyperparameters tuned for this specific problem setting
        EPOCHS = 300  # A high number, but early stopping will find the optimal point
        MAX_LR = 1.2e-3
        WEIGHT_DECAY = 1.5e-2 # Strong weight decay for regularization on a small dataset
        EARLY_STOPPING_PATIENCE = 30 # Ample patience to ensure convergence

        criterion = nn.CrossEntropyLoss()
        optimizer = optim.AdamW(model.parameters(), lr=MAX_LR, weight_decay=WEIGHT_DECAY)
        
        # OneCycleLR is a powerful scheduler that helps converge faster and to a better minimum
        scheduler = optim.lr_scheduler.OneCycleLR(
            optimizer,
            max_lr=MAX_LR,
            epochs=EPOCHS,
            steps_per_epoch=len(train_loader),
            pct_start=0.25 # Shorter warmup phase
        )

        best_val_loss = float('inf')
        epochs_no_improve = 0
        best_model_state = None

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
                scheduler.step()

            # Validation phase
            model.eval()
            current_val_loss = 0.0
            with torch.no_grad():
                for inputs, targets in val_loader:
                    inputs, targets = inputs.to(device), targets.to(device)
                    outputs = model(inputs)
                    loss = criterion(outputs, targets)
                    current_val_loss += loss.item()

            avg_val_loss = current_val_loss / len(val_loader)

            # Early stopping logic: save the best model and stop if no improvement
            if avg_val_loss < best_val_loss:
                best_val_loss = avg_val_loss
                epochs_no_improve = 0
                # Deepcopy the state_dict to ensure it's not a reference
                best_model_state = copy.deepcopy(model.state_dict())
            else:
                epochs_no_improve += 1

            if epochs_no_improve >= EARLY_STOPPING_PATIENCE:
                break
        
        # Load the best performing model state before returning
        if best_model_state:
            model.load_state_dict(best_model_state)

        return model
