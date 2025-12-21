import torch
import torch.nn as nn
import torch.optim as optim
from torch.optim.lr_scheduler import CosineAnnealingLR
import copy

# --- Model Definition ---

class ResidualBlock(nn.Module):
    """A residual block for an MLP."""
    def __init__(self, size: int, dropout_p: float):
        super().__init__()
        self.fc1 = nn.Linear(size, size)
        self.bn1 = nn.BatchNorm1d(size)
        self.act = nn.GELU()
        self.dropout = nn.Dropout(dropout_p)
        self.fc2 = nn.Linear(size, size)
        self.bn2 = nn.BatchNorm1d(size)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        residual = x
        out = self.fc1(x)
        out = self.bn1(out)
        out = self.act(out)
        out = self.dropout(out)
        out = self.fc2(out)
        out = self.bn2(out)
        out += residual
        out = self.act(out)
        return out

class ParetoNet(nn.Module):
    """A deep MLP with residual connections optimized for the parameter budget."""
    def __init__(self, input_dim: int, num_classes: int, hidden_dim: int, num_blocks: int, dropout_p: float):
        super().__init__()
        
        self.input_proj = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.BatchNorm1d(hidden_dim),
            nn.GELU()
        )
        
        self.residual_blocks = nn.Sequential(
            *[ResidualBlock(size=hidden_dim, dropout_p=dropout_p) for _ in range(num_blocks)]
        )
        
        self.output_proj = nn.Linear(hidden_dim, num_classes)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self.input_proj(x)
        x = self.residual_blocks(x)
        x = self.output_proj(x)
        return x

# --- Main Solution Class ---

class Solution:
    def solve(self, train_loader, val_loader, metadata: dict = None) -> torch.nn.Module:
        """
        Train a model and return it.
        
        Args:
            train_loader: PyTorch DataLoader with training data
            val_loader: PyTorch DataLoader with validation data
            metadata: Dict with keys including num_classes, input_dim, device, etc.
        
        Returns:
            Trained torch.nn.Module ready for evaluation
        """
        device = torch.device(metadata.get("device", "cpu"))
        input_dim = metadata["input_dim"]
        num_classes = metadata["num_classes"]

        # --- Hyperparameters ---
        HIDDEN_DIM = 727
        NUM_BLOCKS = 2
        DROPOUT_P = 0.25
        LEARNING_RATE = 1e-3
        WEIGHT_DECAY = 1e-2
        EPOCHS = 600
        PATIENCE = 75
        LABEL_SMOOTHING = 0.1

        # --- Model Initialization ---
        model = ParetoNet(
            input_dim=input_dim,
            num_classes=num_classes,
            hidden_dim=HIDDEN_DIM,
            num_blocks=NUM_BLOCKS,
            dropout_p=DROPOUT_P
        ).to(device)

        # --- Training Setup ---
        criterion = nn.CrossEntropyLoss(label_smoothing=LABEL_SMOOTHING)
        optimizer = optim.AdamW(model.parameters(), lr=LEARNING_RATE, weight_decay=WEIGHT_DECAY)
        scheduler = CosineAnnealingLR(optimizer, T_max=EPOCHS, eta_min=1e-6)

        best_acc = 0.0
        epochs_no_improve = 0
        best_model_wts = copy.deepcopy(model.state_dict())

        # --- Training Loop ---
        for _ in range(EPOCHS):
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

            val_acc = correct / total if total > 0 else 0.0
            scheduler.step()

            # Early stopping logic
            if val_acc > best_acc:
                best_acc = val_acc
                epochs_no_improve = 0
                best_model_wts = copy.deepcopy(model.state_dict())
            else:
                epochs_no_improve += 1

            if epochs_no_improve >= PATIENCE:
                break
        
        # Load best model weights before returning
        if best_model_wts:
            model.load_state_dict(best_model_wts)

        return model
