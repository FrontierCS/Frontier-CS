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

        # This architecture is designed to maximize parameter usage within the 200k limit
        # while incorporating regularization techniques like BatchNorm and Dropout.
        # Parameter count for hidden_dim=257:
        # L1 (Linear): 384*257+257 = 98945
        # BN1 (BatchNorm): 2*257 = 514
        # L2 (Linear): 257*257+257 = 66306
        # BN2 (BatchNorm): 2*257 = 514
        # L3 (Linear): 257*128+128 = 33024
        # Total = 199,303 parameters
        class _CustomMLP(nn.Module):
            def __init__(self, input_dim, num_classes, hidden_dim=257, dropout_rate=0.4):
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
                    
                    nn.Linear(hidden_dim, num_classes)
                )

            def forward(self, x):
                return self.layers(x)

        model = _CustomMLP(input_dim, num_classes).to(device)

        # Hyperparameters
        EPOCHS = 400
        LEARNING_RATE = 1e-3
        WEIGHT_DECAY = 0.05
        LABEL_SMOOTHING = 0.1
        PATIENCE = 50

        optimizer = optim.AdamW(model.parameters(), lr=LEARNING_RATE, weight_decay=WEIGHT_DECAY)
        criterion = nn.CrossEntropyLoss(label_smoothing=LABEL_SMOOTHING)
        scheduler = optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=EPOCHS, eta_min=1e-6)

        best_val_acc = 0.0
        patience_counter = 0
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

            if val_total > 0:
                val_acc = val_correct / val_total
            else:
                val_acc = 0.0

            scheduler.step()

            # Early stopping and model checkpointing
            if val_acc > best_val_acc:
                best_val_acc = val_acc
                patience_counter = 0
                best_model_state = copy.deepcopy(model.state_dict())
            else:
                patience_counter += 1
                if patience_counter >= PATIENCE:
                    break
        
        # Load best model state and return in evaluation mode
        if best_model_state:
            model.load_state_dict(best_model_state)
            
        return model.eval()