import torch
import torch.nn as nn
import torch.optim as optim

class Solution:
    """
    Solution for the ImageNet Pareto Optimization problem (500K variant).
    This solution uses a Multi-Layer Perceptron (MLP) architecture carefully
    designed to stay under the 500,000 parameter limit while maximizing capacity.
    The training strategy employs modern techniques for fast convergence and
    good generalization, including AdamW optimizer, OneCycleLR scheduler,
    label smoothing, and early stopping.
    """
    
    class _CustomModel(nn.Module):
        """
        A custom MLP model with configurable hidden layers, batch normalization,
        GELU activation, and dropout for regularization.
        """
        def __init__(self, input_dim: int, num_classes: int, hidden_dims: list, dropout_p: float):
            super().__init__()
            layers = []
            current_dim = input_dim
            for h_dim in hidden_dims:
                layers.append(nn.Linear(current_dim, h_dim))
                layers.append(nn.BatchNorm1d(h_dim))
                layers.append(nn.GELU())
                layers.append(nn.Dropout(dropout_p))
                current_dim = h_dim
            
            layers.append(nn.Linear(current_dim, num_classes))
            self.net = nn.Sequential(*layers)

        def forward(self, x: torch.Tensor) -> torch.Tensor:
            return self.net(x)

    def solve(self, train_loader, val_loader, metadata: dict = None) -> torch.nn.Module:
        """
        Trains and returns a model for the given task.
        
        Args:
            train_loader: DataLoader for the training set.
            val_loader: DataLoader for the validation set.
            metadata: A dictionary containing problem-specific details.
        
        Returns:
            A trained PyTorch model.
        """
        device = torch.device(metadata.get("device", "cpu"))
        input_dim = metadata["input_dim"]
        num_classes = metadata["num_classes"]

        # --- Hyperparameters ---
        # Architecture: 3 hidden layers, designed to be close to the 500K param limit.
        # Calculated params: ~477,608
        HIDDEN_DIMS = [480, 360, 240] 
        # Regularization
        DROPOUT_P = 0.3
        LABEL_SMOOTHING = 0.1
        WEIGHT_DECAY = 1e-2
        # Optimizer & Scheduler
        LEARNING_RATE = 1.2e-3
        EPOCHS = 350
        # Early Stopping
        PATIENCE = 40

        # --- Model Initialization ---
        model = self._CustomModel(
            input_dim=input_dim,
            num_classes=num_classes,
            hidden_dims=HIDDEN_DIMS,
            dropout_p=DROPOUT_P,
        ).to(device)

        # --- Training Setup ---
        criterion = nn.CrossEntropyLoss(label_smoothing=LABEL_SMOOTHING)
        optimizer = optim.AdamW(
            model.parameters(), lr=LEARNING_RATE, weight_decay=WEIGHT_DECAY
        )
        # OneCycleLR is highly effective for fast convergence.
        scheduler = optim.lr_scheduler.OneCycleLR(
            optimizer,
            max_lr=LEARNING_RATE,
            epochs=EPOCHS,
            steps_per_epoch=len(train_loader),
            pct_start=0.3  # Spend 30% of time warming up
        )

        # --- Training Loop with Early Stopping ---
        best_val_acc = 0.0
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
                scheduler.step()

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

            val_acc = val_correct / val_total

            # Check for improvement and save the best model
            if val_acc > best_val_acc:
                best_val_acc = val_acc
                # Save the model state to CPU memory to be safe
                best_model_state = {k: v.cpu().clone() for k, v in model.state_dict().items()}
                epochs_no_improve = 0
            else:
                epochs_no_improve += 1
                if epochs_no_improve >= PATIENCE:
                    break
        
        # Load the best performing model state
        if best_model_state:
            model.load_state_dict(best_model_state)
            model.to(device)
        
        return model
