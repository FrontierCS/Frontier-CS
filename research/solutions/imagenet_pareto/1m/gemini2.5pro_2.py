import torch
import torch.nn as nn
import torch.optim as optim
from copy import deepcopy
from typing import Dict, Optional

class ResidualBlock(nn.Module):
    """A residual block for an MLP with BatchNorm and Dropout."""
    def __init__(self, size: int, dropout_rate: float):
        super().__init__()
        self.fc1 = nn.Linear(size, size)
        self.bn1 = nn.BatchNorm1d(size)
        self.relu = nn.ReLU()
        self.dropout = nn.Dropout(dropout_rate)
        self.fc2 = nn.Linear(size, size)
        self.bn2 = nn.BatchNorm1d(size)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        residual = x
        out = self.relu(self.bn1(self.fc1(x)))
        out = self.dropout(out)
        out = self.bn2(self.fc2(out))
        out += residual
        out = self.relu(out)
        return out

class ResMLP(nn.Module):
    """
    A ResNet-style MLP designed to maximize parameter usage within the budget.
    This architecture uses residual connections to enable deeper networks.
    """
    def __init__(self, input_dim: int, num_classes: int, hidden_dim: int, num_blocks: int, dropout_rate: float):
        super().__init__()
        
        self.initial_layer = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.BatchNorm1d(hidden_dim),
            nn.ReLU(),
        )
        
        self.blocks = nn.Sequential(
            *[ResidualBlock(hidden_dim, dropout_rate) for _ in range(num_blocks)]
        )
        
        self.classifier = nn.Linear(hidden_dim, num_classes)
        self._initialize_weights()

    def _initialize_weights(self):
        for m in self.modules():
            if isinstance(m, nn.Linear):
                nn.init.kaiming_normal_(m.weight, mode='fan_in', nonlinearity='relu')
                if m.bias is not None:
                    nn.init.constant_(m.bias, 0)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self.initial_layer(x)
        x = self.blocks(x)
        x = self.classifier(x)
        return x

class Solution:
    def solve(self, train_loader: torch.utils.data.DataLoader, val_loader: torch.utils.data.DataLoader, metadata: Optional[Dict] = None) -> torch.nn.Module:
        """
        Train a model and return it.
        
        Args:
            train_loader: PyTorch DataLoader with training data
            val_loader: PyTorch DataLoader with validation data
            metadata: Dict with keys:
                - num_classes: int
                - input_dim: int
                - param_limit: int
                - baseline_accuracy: float
                - device: str
        
        Returns:
            Trained torch.nn.Module ready for evaluation
        """
        device = torch.device(metadata.get("device", "cpu"))
        input_dim = metadata["input_dim"]
        num_classes = metadata["num_classes"]

        # Hyperparameters carefully tuned to maximize accuracy under the 1M parameter constraint.
        # The architecture (ResMLP with HIDDEN_DIM=366 and NUM_BLOCKS=3) results in ~999k parameters.
        HIDDEN_DIM = 366
        NUM_BLOCKS = 3
        DROPOUT_RATE = 0.25
        LEARNING_RATE = 0.001
        WEIGHT_DECAY = 0.01
        NUM_EPOCHS = 350
        PATIENCE = 50
        LABEL_SMOOTHING = 0.1

        model = ResMLP(
            input_dim=input_dim,
            num_classes=num_classes,
            hidden_dim=HIDDEN_DIM,
            num_blocks=NUM_BLOCKS,
            dropout_rate=DROPOUT_RATE,
        ).to(device)

        optimizer = optim.AdamW(model.parameters(), lr=LEARNING_RATE, weight_decay=WEIGHT_DECAY)
        scheduler = optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=NUM_EPOCHS, eta_min=1e-6)
        criterion = nn.CrossEntropyLoss(label_smoothing=LABEL_SMOOTHING)
        
        best_val_acc = 0.0
        epochs_no_improve = 0
        best_model_state = None

        for _ in range(NUM_EPOCHS):
            model.train()
            for inputs, targets in train_loader:
                inputs, targets = inputs.to(device), targets.to(device)
                
                optimizer.zero_grad()
                outputs = model(inputs)
                loss = criterion(outputs, targets)
                loss.backward()
                optimizer.step()

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
            scheduler.step()

            if val_acc > best_val_acc:
                best_val_acc = val_acc
                epochs_no_improve = 0
                best_model_state = deepcopy(model.state_dict())
            else:
                epochs_no_improve += 1
            
            if epochs_no_improve >= PATIENCE:
                break
        
        if best_model_state:
            model.load_state_dict(best_model_state)
        
        return model