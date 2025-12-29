import torch
import torch.nn as nn
import torch.optim as optim
from torch.optim.lr_scheduler import CosineAnnealingLR
import copy

class ResBlock(nn.Module):
    """
    A residual block for an MLP, consisting of two linear layers with
    BatchNorm, GELU activation, and Dropout.
    """
    def __init__(self, size, dropout_p=0.25):
        super().__init__()
        self.block = nn.Sequential(
            nn.Linear(size, size),
            nn.BatchNorm1d(size),
            nn.GELU(),
            nn.Dropout(dropout_p),
            nn.Linear(size, size),
            nn.BatchNorm1d(size),
        )
        self.activation = nn.GELU()

    def forward(self, x):
        residual = x
        out = self.block(x)
        out += residual
        out = self.activation(out)
        return out

class ResNetMLP(nn.Module):
    """
    A ResNet-style MLP architecture designed to maximize parameter count
    under the 1,000,000 limit for this specific problem.
    """
    def __init__(self, input_dim, num_classes, hidden_dim=438, num_blocks=2, dropout_p=0.25):
        super().__init__()
        self.input_layer = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.BatchNorm1d(hidden_dim),
            nn.GELU()
        )
        
        blocks = [ResBlock(hidden_dim, dropout_p) for _ in range(num_blocks)]
        self.res_blocks = nn.Sequential(*blocks)
        
        self.output_layer = nn.Linear(hidden_dim, num_classes)

    def forward(self, x):
        x = self.input_layer(x)
        x = self.res_blocks(x)
        x = self.output_layer(x)
        return x

class Solution:
    def solve(self, train_loader, val_loader, metadata: dict = None) -> torch.nn.Module:
        """
        Train a ResNet-style MLP model on the given data.

        The architecture and hyperparameters are chosen to maximize accuracy
        while staying strictly under the 1,000,000 parameter limit.
        """
        device = torch.device(metadata.get("device", "cpu"))
        input_dim = metadata["input_dim"]
        num_classes = metadata["num_classes"]
        
        # --- Model Initialization ---
        # This architecture is carefully designed to be close to the 1M parameter limit.
        # hidden_dim=438, num_blocks=2 results in ~998,498 parameters.
        hidden_dim = 438
        num_blocks = 2
        dropout_p = 0.25
        
        model = ResNetMLP(
            input_dim=input_dim,
            num_classes=num_classes,
            hidden_dim=hidden_dim,
            num_blocks=num_blocks,
            dropout_p=dropout_p
        ).to(device)
        
        # --- Training Hyperparameters ---
        epochs = 500
        learning_rate = 1e-3
        weight_decay = 5e-3
        label_smoothing = 0.1

        # --- Optimizer, Loss, and Scheduler ---
        optimizer = optim.AdamW(model.parameters(), lr=learning_rate, weight_decay=weight_decay)
        criterion = nn.CrossEntropyLoss(label_smoothing=label_smoothing)
        # Cosine annealing scheduler helps in converging to a better minimum.
        scheduler = CosineAnnealingLR(optimizer, T_max=epochs * len(train_loader), eta_min=1e-6)

        best_val_acc = 0.0
        best_model_state = None

        # --- Training Loop ---
        for _ in range(epochs):
            # Training phase
            model.train()
            for inputs, targets in train_loader:
                inputs, targets = inputs.to(device), targets.to(device)

                optimizer.zero_grad(set_to_none=True)
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
            
            # Save the best model based on validation accuracy
            if val_acc > best_val_acc:
                best_val_acc = val_acc
                best_model_state = copy.deepcopy(model.state_dict())

        # Load the best performing model state for evaluation
        if best_model_state is not None:
            model.load_state_dict(best_model_state)
            
        return model