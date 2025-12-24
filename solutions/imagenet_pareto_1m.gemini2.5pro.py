import torch
import torch.nn as nn
import torch.optim as optim
import numpy as np
from copy import deepcopy

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
                - param_limit: int (1,000,000)
                - baseline_accuracy: float (0.8)
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

        # Hyperparameters chosen to balance model capacity and regularization
        # within the parameter budget.
        HIDDEN_DIM = 420
        NUM_BLOCKS = 2
        DROPOUT_P = 0.3
        
        LEARNING_RATE = 3e-4
        WEIGHT_DECAY = 1e-4
        EPOCHS = 350
        PATIENCE = 40
        MIXUP_ALPHA = 0.4

        # Model definition is nested to keep the solution self-contained.
        class ResBlock(nn.Module):
            def __init__(self, dim, dropout_p=0.2):
                super().__init__()
                self.block = nn.Sequential(
                    nn.Linear(dim, dim),
                    nn.BatchNorm1d(dim),
                    nn.SiLU(),
                    nn.Dropout(p=dropout_p),
                    nn.Linear(dim, dim),
                    nn.BatchNorm1d(dim)
                )
                self.activation = nn.SiLU()

            def forward(self, x):
                return self.activation(x + self.block(x))

        class Net(nn.Module):
            def __init__(self, input_dim, num_classes, hidden_dim, num_blocks, dropout_p):
                super().__init__()
                self.input_layer = nn.Sequential(
                    nn.Linear(input_dim, hidden_dim),
                    nn.BatchNorm1d(hidden_dim),
                    nn.SiLU(),
                )
                
                blocks = [ResBlock(hidden_dim, dropout_p) for _ in range(num_blocks)]
                self.blocks = nn.Sequential(*blocks)
                
                self.output_layer = nn.Linear(hidden_dim, num_classes)

            def forward(self, x):
                x = self.input_layer(x)
                x = self.blocks(x)
                x = self.output_layer(x)
                return x

        model = Net(
            input_dim=input_dim,
            num_classes=num_classes,
            hidden_dim=HIDDEN_DIM,
            num_blocks=NUM_BLOCKS,
            dropout_p=DROPOUT_P
        ).to(device)

        optimizer = optim.AdamW(model.parameters(), lr=LEARNING_RATE, weight_decay=WEIGHT_DECAY)
        criterion = nn.CrossEntropyLoss()
        scheduler = optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=EPOCHS)

        def mixup_criterion(pred, y_a, y_b, lam):
            return lam * criterion(pred, y_a) + (1 - lam) * criterion(pred, y_b)
            
        def mixup_data(x, y, alpha=1.0):
            if alpha > 0:
                lam = np.random.beta(alpha, alpha)
            else:
                lam = 1.0

            batch_size = x.size()[0]
            index = torch.randperm(batch_size).to(x.device)

            mixed_x = lam * x + (1 - lam) * x[index, :]
            y_a, y_b = y, y[index]
            return mixed_x, y_a, y_b, lam

        best_val_loss = float('inf')
        patience_counter = 0
        best_model_state = None

        for epoch in range(EPOCHS):
            model.train()
            for inputs, targets in train_loader:
                inputs, targets = inputs.to(device), targets.to(device)
                
                mixed_inputs, targets_a, targets_b, lam = mixup_data(inputs, targets, MIXUP_ALPHA)
                
                optimizer.zero_grad()
                outputs = model(mixed_inputs)
                loss = mixup_criterion(outputs, targets_a, targets_b, lam)
                
                loss.backward()
                optimizer.step()
            
            scheduler.step()
            
            model.eval()
            val_loss = 0.0
            with torch.no_grad():
                for inputs, targets in val_loader:
                    inputs, targets = inputs.to(device), targets.to(device)
                    outputs = model(inputs)
                    loss = criterion(outputs, targets)
                    val_loss += loss.item()
            
            val_loss /= len(val_loader)

            if val_loss < best_val_loss:
                best_val_loss = val_loss
                best_model_state = deepcopy(model.state_dict())
                patience_counter = 0
            else:
                patience_counter += 1

            if patience_counter >= PATIENCE:
                break
        
        if best_model_state:
            model.load_state_dict(best_model_state)
            
        return model
