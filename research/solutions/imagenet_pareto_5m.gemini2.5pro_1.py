import torch
import torch.nn as nn
import torch.optim as optim
import copy

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
                - param_limit: int (5,000,000)
                - baseline_accuracy: float (0.88)
                - train_samples: int
                - val_samples: int
                - test_samples: int
                - device: str ("cpu")
        
        Returns:
            Trained torch.nn.Module ready for evaluation
        """
        # 1. Setup Environment and Parameters from metadata
        device = torch.device(metadata.get("device", "cpu"))
        input_dim = metadata["input_dim"]
        num_classes = metadata["num_classes"]

        # 2. Model Architecture
        # Hidden dimension is carefully chosen to maximize parameters under the 5M limit,
        # accounting for both linear and batch normalization layers. This architecture
        # results in approximately 4,992,713 parameters.
        hidden_dim = 1455
        dropout_rate = 0.4

        class MLPModel(nn.Module):
            def __init__(self, input_dim, hidden_dim, num_classes, dropout_rate):
                super().__init__()
                self.layers = nn.Sequential(
                    nn.Linear(input_dim, hidden_dim),
                    nn.BatchNorm1d(hidden_dim),
                    nn.GELU(),
                    nn.Dropout(dropout_rate),
                    
                    nn.Linear(hidden_dim, hidden_dim),
                    nn.BatchNorm1d(hidden_dim),
                    nn.GELU(),
                    nn.Dropout(dropout_rate),
                    
                    nn.Linear(hidden_dim, hidden_dim),
                    nn.BatchNorm1d(hidden_dim),
                    nn.GELU(),
                    nn.Dropout(dropout_rate),
                    
                    nn.Linear(hidden_dim, num_classes)
                )
            
            def forward(self, x):
                return self.layers(x)

        model = MLPModel(input_dim, hidden_dim, num_classes, dropout_rate).to(device)

        # 3. Training Hyperparameters
        # A longer training schedule with early stopping is used to find the best model.
        epochs = 400
        patience = 50
        lr = 0.001
        weight_decay = 1e-4
        label_smoothing = 0.1

        # 4. Optimizer, Scheduler, and Loss Function
        optimizer = optim.AdamW(model.parameters(), lr=lr, weight_decay=weight_decay)
        scheduler = optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=epochs)
        criterion = nn.CrossEntropyLoss(label_smoothing=label_smoothing)

        # 5. Training Loop with Validation and Early Stopping
        best_val_acc = 0.0
        best_model_state = None
        epochs_no_improve = 0

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
            
            # Check for improvement and apply early stopping
            if total > 0:
                val_acc = correct / total
                if val_acc > best_val_acc:
                    best_val_acc = val_acc
                    # Save the state of the best model found so far
                    best_model_state = copy.deepcopy(model.state_dict())
                    epochs_no_improve = 0
                else:
                    epochs_no_improve += 1
                    if epochs_no_improve >= patience:
                        break
            else:
                epochs_no_improve += 1
                if epochs_no_improve >= patience:
                    break
            
            # Step the learning rate scheduler
            scheduler.step()

        # 6. Load the best model weights and return
        if best_model_state:
            model.load_state_dict(best_model_state)
            
        return model.eval()