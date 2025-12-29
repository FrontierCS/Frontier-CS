import torch
import torch.nn as nn
import torch.optim as optim

class Solution:
    """
    Implements the solution for the ImageNet Pareto Optimization problem.
    """

    class ResidualBlock(nn.Module):
        """
        A residual block for an MLP, using pre-activation and BatchNorm.
        """
        def __init__(self, size: int, dropout_rate: float):
            super().__init__()
            self.norm1 = nn.BatchNorm1d(size)
            self.fc1 = nn.Linear(size, size)
            self.act = nn.GELU()
            self.dropout = nn.Dropout(dropout_rate)
            self.norm2 = nn.BatchNorm1d(size)
            self.fc2 = nn.Linear(size, size)

        def forward(self, x: torch.Tensor) -> torch.Tensor:
            residual = x
            
            out = self.norm1(x)
            out = self.act(out)
            out = self.fc1(out)
            
            out = self.norm2(out)
            out = self.act(out)
            out = self.dropout(out)
            out = self.fc2(out)
            
            out += residual
            return out

    class ResMLP(nn.Module):
        """
        A simple ResNet-style MLP.
        """
        def __init__(self, input_dim: int, num_classes: int, hidden_dim: int, num_blocks: int, dropout_rate: float):
            super().__init__()
            self.input_proj = nn.Linear(input_dim, hidden_dim)
            
            blocks = []
            for _ in range(num_blocks):
                blocks.append(Solution.ResidualBlock(hidden_dim, dropout_rate))
            self.blocks = nn.Sequential(*blocks)
            
            self.output_norm = nn.LayerNorm(hidden_dim)
            self.classifier = nn.Linear(hidden_dim, num_classes)

        def forward(self, x: torch.Tensor) -> torch.Tensor:
            x = self.input_proj(x)
            x = self.blocks(x)
            x = self.output_norm(x)
            x = self.classifier(x)
            return x

    def solve(self, train_loader, val_loader, metadata: dict = None) -> torch.nn.Module:
        """
        Train a model and return it.
        
        Args:
            train_loader: PyTorch DataLoader with training data
            val_loader: PyTorch DataLoader with validation data
            metadata: Dict with keys like num_classes, input_dim, etc.
        
        Returns:
            Trained torch.nn.Module ready for evaluation
        """
        # Set a seed for reproducibility
        torch.manual_seed(42)

        # Extract metadata
        device = metadata.get("device", "cpu")
        input_dim = metadata["input_dim"]
        num_classes = metadata["num_classes"]
        
        # --- Hyperparameters ---
        # Architecture: Carefully chosen to be just under 5M parameters
        HIDDEN_DIM = 1050
        NUM_BLOCKS = 2
        DROPOUT_RATE = 0.2

        # Training: Optimized for fast convergence and good generalization
        EPOCHS = 250
        MAX_LR = 1e-3
        WEIGHT_DECAY = 0.01
        LABEL_SMOOTHING = 0.1

        # Instantiate the model
        model = self.ResMLP(
            input_dim=input_dim,
            num_classes=num_classes,
            hidden_dim=HIDDEN_DIM,
            num_blocks=NUM_BLOCKS,
            dropout_rate=DROPOUT_RATE,
        ).to(device)

        # Loss function with label smoothing
        criterion = nn.CrossEntropyLoss(label_smoothing=LABEL_SMOOTHING)
        
        # Optimizer with weight decay
        optimizer = optim.AdamW(model.parameters(), lr=MAX_LR, weight_decay=WEIGHT_DECAY)
        
        # Learning rate scheduler for better convergence
        total_steps = len(train_loader) * EPOCHS
        scheduler = optim.lr_scheduler.OneCycleLR(
            optimizer,
            max_lr=MAX_LR,
            total_steps=total_steps,
            pct_start=0.3,
            anneal_strategy='cos',
        )
        
        # --- Training Loop ---
        model.train()
        for _ in range(EPOCHS):
            for inputs, targets in train_loader:
                inputs, targets = inputs.to(device), targets.to(device)
                
                # Forward pass
                outputs = model(inputs)
                loss = criterion(outputs, targets)
                
                # Backward pass and optimization
                optimizer.zero_grad()
                loss.backward()
                optimizer.step()
                
                # Step the scheduler on a per-batch basis
                scheduler.step()
        
        return model