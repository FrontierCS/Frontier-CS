import torch
import torch.nn as nn
import torch.optim as optim
from copy import deepcopy

class _Net(nn.Module):
    def __init__(self, input_dim, num_classes, hidden_dim1=492, hidden_dim2=492, dropout_p=0.3):
        super().__init__()
        self.layers = nn.Sequential(
            nn.Linear(input_dim, hidden_dim1),
            nn.BatchNorm1d(hidden_dim1),
            nn.GELU(),
            nn.Dropout(dropout_p),
            
            nn.Linear(hidden_dim1, hidden_dim2),
            nn.BatchNorm1d(hidden_dim2),
            nn.GELU(),
            nn.Dropout(dropout_p),
            
            nn.Linear(hidden_dim2, num_classes)
        )

    def forward(self, x):
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
        device = metadata.get("device", "cpu")
        num_classes = metadata["num_classes"]
        input_dim = metadata["input_dim"]

        # Model Initialization
        model = _Net(input_dim, num_classes).to(device)
        
        # Hyperparameters
        EPOCHS = 300
        LEARNING_RATE = 1e-3
        WEIGHT_DECAY = 1e-2
        LABEL_SMOOTHING = 0.1

        # Setup optimizer, loss function, and learning rate scheduler
        optimizer = optim.AdamW(model.parameters(), lr=LEARNING_RATE, weight_decay=WEIGHT_DECAY)
        criterion = nn.CrossEntropyLoss(label_smoothing=LABEL_SMOOTHING)
        scheduler = optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=EPOCHS, eta_min=1e-6)

        best_val_acc = -1.0
        best_model_state = None

        # Training Loop
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
            
            current_val_acc = val_correct / val_total
            
            if current_val_acc > best_val_acc:
                best_val_acc = current_val_acc
                best_model_state = deepcopy(model.state_dict())
        
        # Load the best model state found during training
        if best_model_state:
            model.load_state_dict(best_model_state)
            
        return model