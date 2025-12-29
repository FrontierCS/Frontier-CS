import torch
import torch.nn as nn
import torch.optim as optim
from copy import deepcopy

class ResBlock(nn.Module):
    """
    A residual block for an MLP, including LayerNorm/BatchNorm, activation, and dropout.
    """
    def __init__(self, dim, dropout_p=0.3):
        super().__init__()
        self.block = nn.Sequential(
            nn.Linear(dim, dim),
            nn.BatchNorm1d(dim),
            nn.ReLU(inplace=True),
            nn.Dropout(p=dropout_p),
            nn.Linear(dim, dim),
            nn.BatchNorm1d(dim),
        )
        self.relu = nn.ReLU(inplace=True)

    def forward(self, x):
        identity = x
        out = self.block(x)
        out += identity
        out = self.relu(out)
        return out

class DeepMLP(nn.Module):
    """
    A deep MLP with residual connections, designed to maximize parameter count under a budget.
    """
    def __init__(self, input_dim, num_classes, hidden_dim=1054, dropout_p=0.3):
        super().__init__()
        self.initial_layer = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.BatchNorm1d(hidden_dim),
            nn.ReLU(inplace=True),
        )
        self.res_blocks = nn.Sequential(
            ResBlock(hidden_dim, dropout_p),
            ResBlock(hidden_dim, dropout_p),
        )
        self.head = nn.Linear(hidden_dim, num_classes)
        
        # Parameter count for this architecture with hidden_dim=1054:
        # Initial Layer: (384 * 1054 + 1054) + (2 * 1054) = 407,858
        # ResBlock 1: 2 * (1054 * 1054 + 1054) + 2 * (2 * 1054) = 2,228,156
        # ResBlock 2: 2,228,156
        # Head: (1054 * 128 + 128) = 135,040
        # Total: 407,858 + 2,228,156 + 2,228,156 + 135,040 = 4,999,210
        # This is safely under the 5,000,000 parameter limit.

    def forward(self, x):
        x = self.initial_layer(x)
        x = self.res_blocks(x)
        x = self.head(x)
        return x

class Solution:
    def solve(self, train_loader, val_loader, metadata: dict = None) -> torch.nn.Module:
        """
        Train a model and return it.
        """
        device = torch.device(metadata.get("device", "cpu"))
        
        input_dim = metadata["input_dim"]
        num_classes = metadata["num_classes"]

        model = DeepMLP(
            input_dim=input_dim,
            num_classes=num_classes,
            hidden_dim=1054,
            dropout_p=0.3
        ).to(device)

        # Training Hyperparameters
        epochs = 250
        max_lr = 1.5e-3
        weight_decay = 1e-2
        label_smoothing = 0.1
        patience = 35

        criterion = nn.CrossEntropyLoss(label_smoothing=label_smoothing)
        optimizer = optim.AdamW(model.parameters(), lr=max_lr, weight_decay=weight_decay)
        
        steps_per_epoch = len(train_loader)
        scheduler = optim.lr_scheduler.OneCycleLR(
            optimizer,
            max_lr=max_lr,
            epochs=epochs,
            steps_per_epoch=steps_per_epoch,
            pct_start=0.3
        )

        best_val_acc = 0.0
        best_model_state = None
        patience_counter = 0

        for epoch in range(epochs):
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

            if val_acc > best_val_acc:
                best_val_acc = val_acc
                best_model_state = deepcopy(model.state_dict())
                patience_counter = 0
            else:
                patience_counter += 1

            if patience_counter >= patience:
                break
        
        if best_model_state:
            model.load_state_dict(best_model_state)
            
        return model