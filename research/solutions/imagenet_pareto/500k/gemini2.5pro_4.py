import torch
import torch.nn as nn
import torch.optim as optim

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
        device = torch.device(metadata.get("device", "cpu"))
        input_dim = metadata["input_dim"]
        num_classes = metadata["num_classes"]

        # Hyperparameters are tuned for performance within the constraints
        EPOCHS = 250
        LEARNING_RATE = 5e-4
        WEIGHT_DECAY = 0.01
        DROPOUT_RATE = 0.25
        LABEL_SMOOTHING = 0.1
        HIDDEN_DIM = 380  # Carefully chosen to maximize capacity under the 500K param limit

        # A ResNet-style block for MLPs to allow for deeper, more effective models
        class ResBlock(nn.Module):
            def __init__(self, dim, dropout):
                super().__init__()
                self.main_path = nn.Sequential(
                    nn.Linear(dim, dim),
                    nn.BatchNorm1d(dim),
                    nn.GELU(),
                    nn.Dropout(dropout),
                    nn.Linear(dim, dim),
                    nn.BatchNorm1d(dim),
                )
                self.activation = nn.GELU()

            def forward(self, x):
                residual = x
                out = self.main_path(x)
                out += residual
                out = self.activation(out)
                return out
        
        # The main network architecture, using a ResNet-like structure
        class Net(nn.Module):
            def __init__(self, input_dim, num_classes, hidden_dim, dropout_rate):
                super().__init__()
                self.stem = nn.Sequential(
                    nn.Linear(input_dim, hidden_dim),
                    nn.BatchNorm1d(hidden_dim),
                    nn.GELU()
                )
                self.res_block = ResBlock(hidden_dim, dropout_rate)
                self.head = nn.Linear(hidden_dim, num_classes)

            def forward(self, x):
                x = self.stem(x)
                x = self.res_block(x)
                x = self.head(x)
                return x

        model = Net(
            input_dim=input_dim,
            num_classes=num_classes,
            hidden_dim=HIDDEN_DIM,
            dropout_rate=DROPOUT_RATE
        ).to(device)

        # Total parameters for this architecture: ~487K
        # This maximizes model capacity while staying safely under the 500K limit.

        criterion = nn.CrossEntropyLoss(label_smoothing=LABEL_SMOOTHING)
        optimizer = optim.AdamW(
            model.parameters(), lr=LEARNING_RATE, weight_decay=WEIGHT_DECAY
        )
        # Cosine annealing scheduler for better convergence
        scheduler = optim.lr_scheduler.CosineAnnealingLR(
            optimizer, T_max=EPOCHS, eta_min=1e-6
        )

        # Training loop
        for _ in range(EPOCHS):
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
        return model