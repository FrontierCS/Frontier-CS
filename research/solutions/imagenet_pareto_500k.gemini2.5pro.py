import torch
import torch.nn as nn
import torch.optim as optim
from copy import deepcopy

# It's good practice to define the model architecture outside the main solve function
# for clarity and reusability.
class CustomMLP(nn.Module):
    """
    A custom Multi-Layer Perceptron designed to maximize capacity under the 500k parameter limit.
    This architecture uses two hidden layers, batch normalization, and dropout for regularization.
    The hidden layer sizes (480) were chosen to bring the parameter count close to the limit.
    
    Calculation:
    - Layer 1: (384 * 480 + 480) + 2*480 (BN) = 184800 + 960 = 185760
    - Layer 2: (480 * 480 + 480) + 2*480 (BN) = 230400 + 960 = 231360
    - Layer 3: (480 * 128 + 128) = 61440 + 128 = 61568
    - Total: 185760 + 231360 + 61568 = 478688 parameters.
    This is safely under the 500,000 limit.
    """
    def __init__(self, input_dim: int, num_classes: int):
        super(CustomMLP, self).__init__()
        
        hidden_dim1 = 480
        hidden_dim2 = 480
        dropout_rate = 0.3

        self.layers = nn.Sequential(
            nn.Linear(input_dim, hidden_dim1),
            nn.BatchNorm1d(hidden_dim1),
            nn.ReLU(inplace=True),
            nn.Dropout(p=dropout_rate),
            
            nn.Linear(hidden_dim1, hidden_dim2),
            nn.BatchNorm1d(hidden_dim2),
            nn.ReLU(inplace=True),
            nn.Dropout(p=dropout_rate),
            
            nn.Linear(hidden_dim2, num_classes)
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.layers(x)

class Solution:
    """
    This solution trains a custom MLP model on the provided data.
    """
    def solve(self, train_loader, val_loader, metadata: dict = None) -> torch.nn.Module:
        """
        Train a model and return it.
        
        Args:
            train_loader: PyTorch DataLoader with training data
            val_loader: PyTorch DataLoader with validation data
            metadata: Dict with keys including num_classes, input_dim, and device
        
        Returns:
            Trained torch.nn.Module ready for evaluation
        """
        # Extract metadata
        device = metadata.get("device", "cpu")
        input_dim = metadata["input_dim"]
        num_classes = metadata["num_classes"]

        # Instantiate the model and move it to the specified device
        model = CustomMLP(input_dim=input_dim, num_classes=num_classes)
        model.to(device)

        # Hyperparameters chosen for robust training
        # With a small dataset, a higher number of epochs is feasible and beneficial.
        epochs = 250
        learning_rate = 1e-3
        weight_decay = 1e-4
        label_smoothing = 0.1

        # Optimizer: AdamW is a robust choice that often outperforms standard Adam.
        optimizer = optim.AdamW(model.parameters(), lr=learning_rate, weight_decay=weight_decay)

        # Loss Function: CrossEntropyLoss with label smoothing for regularization.
        criterion = nn.CrossEntropyLoss(label_smoothing=label_smoothing)

        # Scheduler: CosineAnnealingLR helps in converging to a better minimum by
        # gradually decreasing the learning rate.
        scheduler = optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=epochs, eta_min=1e-6)

        best_val_accuracy = 0.0
        best_model_state = None

        # Training and validation loop
        for epoch in range(epochs):
            # --- Training Phase ---
            model.train()
            for inputs, targets in train_loader:
                inputs, targets = inputs.to(device), targets.to(device)
                
                optimizer.zero_grad()
                outputs = model(inputs)
                loss = criterion(outputs, targets)
                loss.backward()
                optimizer.step()

            # --- Validation Phase ---
            model.eval()
            total_correct = 0
            total_samples = 0
            with torch.no_grad():
                for inputs, targets in val_loader:
                    inputs, targets = inputs.to(device), targets.to(device)
                    outputs = model(inputs)
                    _, predicted = torch.max(outputs.data, 1)
                    total_samples += targets.size(0)
                    total_correct += (predicted == targets).sum().item()
            
            current_val_accuracy = total_correct / total_samples
            
            # Save the state of the model that has the best validation accuracy so far
            if current_val_accuracy > best_val_accuracy:
                best_val_accuracy = current_val_accuracy
                best_model_state = deepcopy(model.state_dict())
            
            # Step the learning rate scheduler
            scheduler.step()

        # Load the best model state found during training before returning
        if best_model_state:
            model.load_state_dict(best_model_state)
            
        return model
