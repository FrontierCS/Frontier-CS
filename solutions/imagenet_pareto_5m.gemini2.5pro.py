import torch
import torch.nn as nn
import torch.optim as optim
from copy import deepcopy

class Solution:
    """
    Solution for the ImageNet Pareto Optimization problem (5M Parameter Variant).
    This solution implements a deep Multi-Layer Perceptron (MLP) with modern
    components like GELU activation, Batch Normalization, and Dropout.
    The training process uses the AdamW optimizer, Cosine Annealing learning
    rate schedule, and label smoothing to maximize generalization.
    Early stopping is employed to select the best model based on validation
    accuracy and prevent overfitting.
    """
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
                - baseline_accuracy: float
                - device: str
        
        Returns:
            Trained torch.nn.Module ready for evaluation
        """
        
        # For reproducibility
        torch.manual_seed(42)
        if torch.cuda.is_available():
            torch.cuda.manual_seed_all(42)

        # --- Hyperparameters and Setup ---
        device = torch.device(metadata.get("device", "cpu"))
        input_dim = metadata["input_dim"]
        num_classes = metadata["num_classes"]

        # Tuned hyperparameters
        HIDDEN_DIM = 1050
        NUM_HIDDEN_LAYERS = 4
        DROPOUT_RATE = 0.25
        
        EPOCHS = 250
        LEARNING_RATE = 3e-4
        WEIGHT_DECAY = 0.01
        LABEL_SMOOTHING = 0.1
        EARLY_STOPPING_PATIENCE = 30

        # --- Model Definition ---
        # A modular block for the MLP
        class Block(nn.Module):
            def __init__(self, dim, dropout_rate):
                super().__init__()
                self.layer = nn.Linear(dim, dim)
                self.bn = nn.BatchNorm1d(dim)
                self.act = nn.GELU()
                self.dropout = nn.Dropout(dropout_rate)

            def forward(self, x):
                x = self.layer(x)
                x = self.bn(x)
                x = self.act(x)
                x = self.dropout(x)
                return x

        # The main model architecture
        class CustomMLP(nn.Module):
            def __init__(self, input_dim, num_classes, hidden_dim, num_hidden_layers, dropout_rate):
                super().__init__()
                
                layers = [
                    nn.Linear(input_dim, hidden_dim),
                    nn.BatchNorm1d(hidden_dim),
                    nn.GELU(),
                    nn.Dropout(dropout_rate)
                ]
                
                for _ in range(num_hidden_layers):
                    layers.append(Block(hidden_dim, dropout_rate))
                    
                layers.append(nn.Linear(hidden_dim, num_classes))
                
                self.net = nn.Sequential(*layers)

            def forward(self, x):
                return self.net(x)

        model = CustomMLP(
            input_dim=input_dim,
            num_classes=num_classes,
            hidden_dim=HIDDEN_DIM,
            num_hidden_layers=NUM_HIDDEN_LAYERS,
            dropout_rate=DROPOUT_RATE
        ).to(device)

        # --- Training Setup ---
        optimizer = optim.AdamW(model.parameters(), lr=LEARNING_RATE, weight_decay=WEIGHT_DECAY)
        criterion = nn.CrossEntropyLoss(label_smoothing=LABEL_SMOOTHING)
        scheduler = optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=EPOCHS)

        # --- Training Loop with Early Stopping ---
        best_val_acc = -1.0
        best_model_state = None
        epochs_no_improve = 0

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

            # Check for improvement and implement early stopping
            if val_acc > best_val_acc:
                best_val_acc = val_acc
                best_model_state = deepcopy(model.state_dict())
                epochs_no_improve = 0
            else:
                epochs_no_improve += 1

            if epochs_no_improve >= EARLY_STOPPING_PATIENCE:
                break
            
            scheduler.step()
        
        # Load the best performing model state
        if best_model_state:
            model.load_state_dict(best_model_state)

        # Set model to evaluation mode before returning
        model.eval()
        
        return model
