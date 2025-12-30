import torch
import torch.nn as nn
import torch.optim as optim
from torch.optim.lr_scheduler import CosineAnnealingLR
import copy

class ResidualBlock(nn.Module):
    """
    A standard residual block for an MLP, with pre-activation style.
    It consists of two linear layers, batch normalization, GELU activation, and dropout.
    """
    def __init__(self, size: int, dropout_rate: float):
        super().__init__()
        self.fc1 = nn.Linear(size, size)
        self.bn1 = nn.BatchNorm1d(size)
        self.fc2 = nn.Linear(size, size)
        self.bn2 = nn.BatchNorm1d(size)
        self.activation = nn.GELU()
        self.dropout = nn.Dropout(dropout_rate)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        residual = x
        out = self.fc1(x)
        out = self.bn1(out)
        out = self.activation(out)
        out = self.dropout(out)
        out = self.fc2(out)
        out = self.bn2(out)
        out += residual
        out = self.activation(out)
        return out

class ResMLP(nn.Module):
    """
    A ResNet-style Multi-Layer Perceptron (ResMLP) designed for vector data.
    """
    def __init__(self, input_dim: int, hidden_dim: int, num_classes: int, num_blocks: int, dropout_rate: float):
        super().__init__()
        self.input_layer = nn.Linear(input_dim, hidden_dim)
        self.input_bn = nn.BatchNorm1d(hidden_dim)
        self.input_activation = nn.GELU()
        
        blocks = [ResidualBlock(hidden_dim, dropout_rate) for _ in range(num_blocks)]
        self.res_blocks = nn.Sequential(*blocks)
        
        self.classifier = nn.Linear(hidden_dim, num_classes)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self.input_layer(x)
        x = self.input_bn(x)
        x = self.input_activation(x)
        x = self.res_blocks(x)
        x = self.classifier(x)
        return x

class Solution:
    """
    Solution class for training a parameter-constrained model.
    """
    def solve(self, train_loader: torch.utils.data.DataLoader, val_loader: torch.utils.data.DataLoader, metadata: dict = None) -> torch.nn.Module:
        """
        Trains a ResMLP model on the provided data loaders.
        
        The architecture and hyperparameters are tuned to maximize accuracy
        while staying under the 500,000 parameter limit.
        """
        device = metadata.get("device", "cpu")
        input_dim = metadata["input_dim"]
        num_classes = metadata["num_classes"]

        # --- Model Configuration ---
        # This configuration creates a model with approximately 483,104 parameters,
        # which effectively utilizes the given budget. The architecture is a deep
        # ResNet-style MLP, which is well-suited for this type of data.
        hidden_dim = 288
        num_blocks = 2
        dropout_rate = 0.25
        
        model = ResMLP(
            input_dim=input_dim,
            hidden_dim=hidden_dim,
            num_classes=num_classes,
            num_blocks=num_blocks,
            dropout_rate=dropout_rate,
        ).to(device)

        # --- Training Configuration ---
        epochs = 300
        lr = 0.001
        weight_decay = 0.01

        optimizer = optim.AdamW(model.parameters(), lr=lr, weight_decay=weight_decay)
        scheduler = CosineAnnealingLR(optimizer, T_max=epochs, eta_min=1e-6)
        criterion = nn.CrossEntropyLoss()

        # --- Training Loop with Early Stopping Logic ---
        best_val_acc = 0.0
        best_model_state = None
        
        for _ in range(epochs):
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
            
            # Step the learning rate scheduler
            scheduler.step()

            # Save the best model state based on validation accuracy
            if val_acc > best_val_acc:
                best_val_acc = val_acc
                best_model_state = copy.deepcopy(model.state_dict())

        # Load the weights of the best performing model
        if best_model_state:
            model.load_state_dict(best_model_state)
            
        return model