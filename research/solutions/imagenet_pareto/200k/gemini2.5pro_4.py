import torch
import torch.nn as nn
import torch.optim as optim
from torch.optim.lr_scheduler import CosineAnnealingLR
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
        input_dim = metadata["input_dim"]
        num_classes = metadata["num_classes"]

        # A 3-layer MLP designed to maximize parameter usage within the 200k limit.
        # It uses BatchNorm for stable training, GELU for activation, and Dropout for regularization.
        # Parameter count:
        # Linear1(384->256): 98,560
        # BN1(256): 512
        # Linear2(256->256): 65,792
        # BN2(256): 512
        # Linear3(256->128): 32,896
        # Total: 198,272 params
        h1_dim = 256
        h2_dim = 256
        dropout_rate = 0.25

        model = nn.Sequential(
            nn.Linear(input_dim, h1_dim),
            nn.BatchNorm1d(h1_dim),
            nn.GELU(),
            nn.Dropout(p=dropout_rate),
            
            nn.Linear(h1_dim, h2_dim),
            nn.BatchNorm1d(h2_dim),
            nn.GELU(),
            nn.Dropout(p=dropout_rate),
            
            nn.Linear(h2_dim, num_classes)
        ).to(device)

        # Hyperparameters tuned for robust training and strong regularization
        EPOCHS = 250
        LEARNING_RATE = 1e-3
        WEIGHT_DECAY = 1e-2
        LABEL_SMOOTHING = 0.1

        criterion = nn.CrossEntropyLoss(label_smoothing=LABEL_SMOOTHING)
        optimizer = optim.AdamW(model.parameters(), lr=LEARNING_RATE, weight_decay=WEIGHT_DECAY)
        scheduler = CosineAnnealingLR(optimizer, T_max=EPOCHS, eta_min=1e-6)

        best_val_acc = 0.0
        best_model_state = None

        # Training loop with validation-based model saving
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
            
            # Save the best model based on validation accuracy
            if val_acc > best_val_acc:
                best_val_acc = val_acc
                best_model_state = copy.deepcopy(model.state_dict())
        
        # Load the best performing model state for the final return
        if best_model_state:
            model.load_state_dict(best_model_state)
            
        return model