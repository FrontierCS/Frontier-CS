import torch
import torch.nn as nn
import torch.optim as optim
import copy

class ResidualBlock(nn.Module):
    """
    A residual block for an MLP with BatchNorm and Dropout.
    """
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
        out = self.fc1(x)
        out = self.bn1(out)
        out = self.relu(out)
        out = self.dropout(out)
        out = self.fc2(out)
        out = self.bn2(out)
        out += residual
        out = self.relu(out)
        return out

class ResNetMLP(nn.Module):
    """
    A ResNet-style MLP designed to maximize parameter usage within a budget.
    """
    def __init__(self, input_dim: int, num_classes: int, hidden_dim: int, num_blocks: int, dropout_rate: float):
        super().__init__()
        self.input_layer = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.BatchNorm1d(hidden_dim),
            nn.ReLU(),
            nn.Dropout(dropout_rate)
        )
        
        res_layers = []
        for _ in range(num_blocks):
            res_layers.append(ResidualBlock(hidden_dim, dropout_rate))
        self.res_layers = nn.Sequential(*res_layers)
        
        self.output_layer = nn.Linear(hidden_dim, num_classes)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self.input_layer(x)
        x = self.res_layers(x)
        x = self.output_layer(x)
        return x

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

        # --- Hyperparameters ---
        # Architecture tuned to be just under 2.5M parameters
        HIDDEN_DIM = 602
        NUM_BLOCKS = 3
        DROPOUT_RATE = 0.25
        
        # Training hyperparameters
        LEARNING_RATE = 0.001
        WEIGHT_DECAY = 0.01
        EPOCHS = 350
        PATIENCE = 40
        LABEL_SMOOTHING = 0.1

        # --- Model Definition ---
        model = ResNetMLP(
            input_dim=input_dim,
            num_classes=num_classes,
            hidden_dim=HIDDEN_DIM,
            num_blocks=NUM_BLOCKS,
            dropout_rate=DROPOUT_RATE
        )
        model.to(device)

        # --- Optimizer, Scheduler, Loss ---
        optimizer = optim.AdamW(model.parameters(), lr=LEARNING_RATE, weight_decay=WEIGHT_DECAY)
        scheduler = optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=EPOCHS)
        criterion = nn.CrossEntropyLoss(label_smoothing=LABEL_SMOOTHING)

        # --- Training Loop with Early Stopping ---
        best_val_acc = -1.0
        epochs_no_improve = 0
        best_model_state = copy.deepcopy(model.state_dict())

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
            
            scheduler.step()

            # Check for improvement and save the best model
            if current_val_acc > best_val_acc:
                best_val_acc = current_val_acc
                epochs_no_improve = 0
                best_model_state = copy.deepcopy(model.state_dict())
            else:
                epochs_no_improve += 1
            
            if epochs_no_improve >= PATIENCE:
                break
        
        model.load_state_dict(best_model_state)
        return model