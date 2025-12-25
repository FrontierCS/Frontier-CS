import torch
import torch.nn as nn
import torch.optim as optim
from collections import OrderedDict

class _Model(nn.Module):
    def __init__(self, input_dim: int, num_classes: int, hidden_dim: int = 493, dropout_p: float = 0.3):
        super().__init__()
        self.layers = nn.Sequential(OrderedDict([
            ('fc1', nn.Linear(input_dim, hidden_dim)),
            ('bn1', nn.BatchNorm1d(hidden_dim)),
            ('act1', nn.GELU()),
            ('drop1', nn.Dropout(p=dropout_p)),
            
            ('fc2', nn.Linear(hidden_dim, hidden_dim)),
            ('bn2', nn.BatchNorm1d(hidden_dim)),
            ('act2', nn.GELU()),
            ('drop2', nn.Dropout(p=dropout_p)),
            
            ('fc3', nn.Linear(hidden_dim, num_classes))
        ]))

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
                - param_limit: int (500,000)
                - baseline_accuracy: float (0.72)
                - train_samples: int
                - val_samples: int
                - test_samples: int
                - device: str ("cpu")
        
        Returns:
            Trained torch.nn.Module ready for evaluation
        """
        device = torch.device(metadata.get("device", "cpu"))
        num_classes = metadata["num_classes"]
        input_dim = metadata["input_dim"]

        # Model architecture designed to be close to the 500k parameter limit
        # Total parameters: 498,551
        model = _Model(
            input_dim=input_dim,
            num_classes=num_classes,
            hidden_dim=493,
            dropout_p=0.3
        ).to(device)

        # Training hyperparameters
        epochs = 300
        patience = 50
        max_lr = 6e-3
        weight_decay = 0.02
        label_smoothing = 0.1

        # Optimizer, Scheduler, and Loss Function
        criterion = nn.CrossEntropyLoss(label_smoothing=label_smoothing)
        optimizer = optim.AdamW(model.parameters(), lr=max_lr, weight_decay=weight_decay)
        
        scheduler = optim.lr_scheduler.OneCycleLR(
            optimizer,
            max_lr=max_lr,
            epochs=epochs,
            steps_per_epoch=len(train_loader),
            pct_start=0.3,
            div_factor=25.0,
            final_div_factor=1e4
        )

        # Training loop with early stopping
        best_val_acc = 0.0
        best_model_state = None
        patience_counter = 0

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
                scheduler.step()

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

            # Early stopping logic
            if val_acc > best_val_acc:
                best_val_acc = val_acc
                best_model_state = {k: v.cpu() for k, v in model.state_dict().items()}
                patience_counter = 0
            else:
                patience_counter += 1

            if patience_counter >= patience:
                break
        
        # Load best model and return
        if best_model_state:
            model.load_state_dict(best_model_state)
        
        model.to(device)
        model.eval()
        return model
