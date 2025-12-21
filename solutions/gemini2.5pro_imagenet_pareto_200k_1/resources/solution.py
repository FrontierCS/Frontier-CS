import torch
import torch.nn as nn
import copy
from torch.optim.lr_scheduler import OneCycleLR

class Net(nn.Module):
    def __init__(self, input_dim: int, num_classes: int, dropout_p: float = 0.3):
        super().__init__()
        self.layers = nn.Sequential(
            nn.Linear(input_dim, 256),
            nn.BatchNorm1d(256),
            nn.ReLU(inplace=True),
            nn.Dropout(dropout_p),

            nn.Linear(256, 192),
            nn.BatchNorm1d(192),
            nn.ReLU(inplace=True),
            nn.Dropout(dropout_p),

            nn.Linear(192, 128),
            nn.BatchNorm1d(128),
            nn.ReLU(inplace=True),
            nn.Dropout(dropout_p),

            nn.Linear(128, num_classes)
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
                - param_limit: int (200,000)
                - baseline_accuracy: float (0.65)
                - train_samples: int
                - val_samples: int
                - test_samples: int
                - device: str ("cpu")
        
        Returns:
            Trained torch.nn.Module ready for evaluation
        """
        device = torch.device(metadata.get("device", "cpu"))

        # Hyperparameters
        num_epochs = 300
        patience = 40
        max_lr = 0.01
        weight_decay = 5e-4
        label_smoothing = 0.1
        dropout_p = 0.3

        # Model Initialization
        model = Net(
            input_dim=metadata["input_dim"],
            num_classes=metadata["num_classes"],
            dropout_p=dropout_p
        ).to(device)

        # Loss Function, Optimizer, and Scheduler
        criterion = nn.CrossEntropyLoss(label_smoothing=label_smoothing)
        optimizer = torch.optim.AdamW(model.parameters(), lr=max_lr, weight_decay=weight_decay)
        
        total_steps = num_epochs * len(train_loader)
        scheduler = OneCycleLR(optimizer, max_lr=max_lr, total_steps=total_steps)

        # Training Loop with Early Stopping
        best_val_acc = 0.0
        epochs_no_improve = 0
        best_model_state = None

        for epoch in range(num_epochs):
            model.train()
            for inputs, targets in train_loader:
                inputs, targets = inputs.to(device), targets.to(device)

                optimizer.zero_grad()
                outputs = model(inputs)
                loss = criterion(outputs, targets)
                loss.backward()
                optimizer.step()
                scheduler.step()

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

            val_acc = total_correct / total_samples

            if val_acc > best_val_acc:
                best_val_acc = val_acc
                best_model_state = copy.deepcopy(model.state_dict())
                epochs_no_improve = 0
            else:
                epochs_no_improve += 1
                if epochs_no_improve >= patience:
                    break
        
        if best_model_state:
            model.load_state_dict(best_model_state)

        return model
