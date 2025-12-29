import torch
import torch.nn as nn
import torch.optim as optim
from copy import deepcopy

class Solution:
    """
    Solution class for the ImageNet Pareto Optimization problem.
    """
    
    class _Net(nn.Module):
        """
        A custom neural network designed to maximize accuracy under a 200k parameter budget.
        It features a residual connection, BatchNorm, GELU activation, and Dropout for regularization.
        """
        def __init__(self, input_dim: int, num_classes: int, hidden_dim: int = 257, dropout_p: float = 0.4):
            super().__init__()
            
            # Entry block to project input to hidden dimension
            self.entry_block = nn.Sequential(
                nn.Linear(input_dim, hidden_dim),
                nn.BatchNorm1d(hidden_dim),
                nn.GELU()
            )
            
            # Residual block
            self.residual_block = nn.Sequential(
                nn.Linear(hidden_dim, hidden_dim),
                nn.BatchNorm1d(hidden_dim),
                nn.GELU(),
                nn.Dropout(dropout_p)
            )
            
            # Final output layer
            self.output_layer = nn.Linear(hidden_dim, num_classes)

            # Parameter check (h=257):
            # entry_block: (384*257 + 257) + 2*257 = 99459
            # residual_block: (257*257 + 257) + 2*257 = 66820
            # output_layer: 257*128 + 128 = 33024
            # Total: 99459 + 66820 + 33024 = 199303 < 200000

        def forward(self, x: torch.Tensor) -> torch.Tensor:
            x_main = self.entry_block(x)
            x_res = self.residual_block(x_main)
            # Add residual connection
            out = x_main + x_res
            out = self.output_layer(out)
            return out

    def solve(self, train_loader, val_loader, metadata: dict = None) -> torch.nn.Module:
        """
        Trains a model and returns it.

        Args:
            train_loader: PyTorch DataLoader with training data.
            val_loader: PyTorch DataLoader with validation data.
            metadata: Dictionary with problem-specific information.

        Returns:
            A trained torch.nn.Module ready for evaluation.
        """
        device = torch.device(metadata.get("device", "cpu"))
        input_dim = metadata["input_dim"]
        num_classes = metadata["num_classes"]

        # Hyperparameters tuned for this specific problem
        HIDDEN_DIM = 257
        DROPOUT_P = 0.4
        NUM_EPOCHS = 250
        MAX_LR = 5e-3
        WEIGHT_DECAY = 1e-2
        PATIENCE = 20

        model = self._Net(
            input_dim=input_dim,
            num_classes=num_classes,
            hidden_dim=HIDDEN_DIM,
            dropout_p=DROPOUT_P
        ).to(device)

        optimizer = optim.AdamW(model.parameters(), lr=MAX_LR, weight_decay=WEIGHT_DECAY)
        criterion = nn.CrossEntropyLoss()
        
        # OneCycleLR is a powerful scheduler that often leads to faster convergence and better results
        scheduler = optim.lr_scheduler.OneCycleLR(
            optimizer,
            max_lr=MAX_LR,
            epochs=NUM_EPOCHS,
            steps_per_epoch=len(train_loader)
        )

        best_val_acc = -1.0
        best_model_state = None
        epochs_no_improve = 0

        for epoch in range(NUM_EPOCHS):
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

            # Save the best model based on validation accuracy and implement early stopping
            if val_acc > best_val_acc:
                best_val_acc = val_acc
                best_model_state = deepcopy(model.state_dict())
                epochs_no_improve = 0
            else:
                epochs_no_improve += 1
            
            if epochs_no_improve >= PATIENCE:
                break
        
        # Load the best performing model state before returning
        if best_model_state:
            model.load_state_dict(best_model_state)
            
        return model.to(torch.device("cpu"))