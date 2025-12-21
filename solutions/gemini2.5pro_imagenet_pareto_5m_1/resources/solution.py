import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, ConcatDataset

# Helper classes for the model architecture, defined at the module level for clarity.

class ResBlock(nn.Module):
    """
    A residual block for the MLP. It consists of two linear layers with
    BatchNorm, GELU activation, and Dropout, with a skip connection.
    """
    def __init__(self, dim, dropout_rate=0.2):
        super().__init__()
        self.block = nn.Sequential(
            nn.Linear(dim, dim),
            nn.BatchNorm1d(dim),
            nn.GELU(),
            nn.Dropout(p=dropout_rate),
            nn.Linear(dim, dim),
            nn.BatchNorm1d(dim)
        )
        self.act = nn.GELU()

    def forward(self, x):
        residual = x
        out = self.block(x)
        out += residual
        out = self.act(out)
        return out

class ResMLP(nn.Module):
    """
    A Residual Multi-Layer Perceptron (ResMLP) model.
    It uses a stem to project the input, a series of residual blocks,
    and a final head for classification.
    """
    def __init__(self, input_dim, hidden_dim, num_classes, num_blocks, dropout_rate):
        super().__init__()
        self.stem = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.BatchNorm1d(hidden_dim),
            nn.GELU()
        )
        
        self.blocks = nn.Sequential(
            *[ResBlock(hidden_dim, dropout_rate) for _ in range(num_blocks)]
        )
        
        self.head = nn.Linear(hidden_dim, num_classes)

    def forward(self, x):
        x = self.stem(x)
        x = self.blocks(x)
        x = self.head(x)
        return x

class Solution:
    """
    The main solution class for training the model.
    """
    def solve(self, train_loader: DataLoader, val_loader: DataLoader, metadata: dict = None) -> nn.Module:
        """
        Trains a ResMLP model on the provided data and returns the trained model.

        The strategy is as follows:
        1.  **Architecture**: A deep but narrow Residual MLP (ResMLP) is chosen.
            This architecture uses skip connections, which helps in training deeper networks
            and often leads to better performance. Batch normalization and dropout are
            used for regularization to combat overfitting on the small dataset.
        2.  **Parameter Budget**: The model's hyperparameters (hidden_dim, num_blocks)
            are carefully chosen to keep the total number of trainable parameters
            just under the 5,000,000 limit. A 3-block ResMLP with hidden_dim=869
            results in approximately 4.99M parameters.
        3.  **Data Utilization**: The training and validation datasets are concatenated.
            This leverages all available labeled data for training the final model, which is
            a common practice to improve generalization.
        4.  **Optimization**: AdamW optimizer is used, which often performs better than
            standard Adam due to its improved weight decay implementation.
        5.  **Learning Rate Schedule**: A CosineAnnealingLR scheduler is employed to
            smoothly decrease the learning rate over a long training duration (400 epochs).
            This helps the model to settle into a good minimum in the loss landscape.
        6.  **Training Duration**: The number of epochs is set to 400, a value that
            balances thorough training with the 1-hour time limit on a CPU.
        """
        # 1. Extract metadata and set up the device
        device = torch.device(metadata.get("device", "cpu"))
        input_dim = metadata["input_dim"]
        num_classes = metadata["num_classes"]
        param_limit = metadata["param_limit"]

        # 2. Define model hyperparameters to stay under the parameter limit
        # This configuration results in ~4.99M parameters.
        hidden_dim = 869
        num_blocks = 3
        dropout_rate = 0.2

        # 3. Instantiate the model
        model = ResMLP(
            input_dim=input_dim,
            hidden_dim=hidden_dim,
            num_classes=num_classes,
            num_blocks=num_blocks,
            dropout_rate=dropout_rate
        ).to(device)
        
        # Verify parameter count does not exceed the limit
        param_count = sum(p.numel() for p in model.parameters() if p.requires_grad)
        if param_count > param_limit:
            # This should not happen with the chosen hyperparameters, but is a safeguard.
            raise ValueError(f"Model exceeds parameter limit: {param_count} > {param_limit}")

        # 4. Combine train and validation datasets for training
        combined_dataset = ConcatDataset([train_loader.dataset, val_loader.dataset])
        
        # 5. Define training hyperparameters
        batch_size = 128
        num_epochs = 400
        learning_rate = 1e-3
        weight_decay = 1e-2

        # Create a new DataLoader for the combined dataset
        combined_loader = DataLoader(
            combined_dataset, 
            batch_size=batch_size, 
            shuffle=True,
            num_workers=0,  # Best for CPU-only execution
            pin_memory=False
        )

        # 6. Set up the optimizer, learning rate scheduler, and loss function
        optimizer = optim.AdamW(model.parameters(), lr=learning_rate, weight_decay=weight_decay)
        scheduler = optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=num_epochs)
        criterion = nn.CrossEntropyLoss()

        # 7. Execute the training loop
        model.train()
        for _ in range(num_epochs):
            for inputs, targets in combined_loader:
                inputs, targets = inputs.to(device), targets.to(device)

                # Forward pass
                outputs = model(inputs)
                loss = criterion(outputs, targets)

                # Backward pass and optimization
                optimizer.zero_grad()
                loss.backward()
                optimizer.step()
            
            # Update the learning rate
            scheduler.step()
        
        # 8. Set the model to evaluation mode before returning
        model.eval()
        return model
