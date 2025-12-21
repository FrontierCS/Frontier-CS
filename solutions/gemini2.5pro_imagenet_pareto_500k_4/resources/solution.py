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
        param_limit = metadata["param_limit"]

        class ResidualBlock(nn.Module):
            def __init__(self, size, dropout_p=0.4):
                super().__init__()
                self.fc1 = nn.Linear(size, size)
                self.bn1 = nn.BatchNorm1d(size)
                self.act = nn.GELU()
                self.dropout = nn.Dropout(dropout_p)
                self.fc2 = nn.Linear(size, size)
                self.bn2 = nn.BatchNorm1d(size)

            def forward(self, x):
                identity = x
                out = self.fc1(x)
                out = self.bn1(out)
                out = self.act(out)
                out = self.dropout(out)
                out = self.fc2(out)
                out = self.bn2(out)
                out = self.dropout(out)
                out += identity
                out = self.act(out)
                return out

        class ResMLP(nn.Module):
            def __init__(self, input_dim, hidden_dim, num_classes, num_blocks=1, dropout_p=0.4):
                super().__init__()
                self.input_layer = nn.Sequential(
                    nn.Linear(input_dim, hidden_dim),
                    nn.BatchNorm1d(hidden_dim),
                    nn.GELU()
                )
                
                blocks = []
                for _ in range(num_blocks):
                    blocks.append(ResidualBlock(hidden_dim, dropout_p))
                self.res_blocks = nn.Sequential(*blocks)
                
                self.output_layer = nn.Linear(hidden_dim, num_classes)
                
            def forward(self, x):
                x = self.input_layer(x)
                x = self.res_blocks(x)
                x = self.output_layer(x)
                return x

        # Model configuration to stay under the 500k parameter limit
        # After manual calculation, hidden_dim=386 with 1 block is optimal
        hidden_dim = 386
        dropout_p = 0.4
        num_blocks = 1
        
        model = ResMLP(
            input_dim=input_dim,
            hidden_dim=hidden_dim,
            num_classes=num_classes,
            num_blocks=num_blocks,
            dropout_p=dropout_p
        ).to(device)
        
        # Verify parameter count
        param_count = sum(p.numel() for p in model.parameters() if p.requires_grad)
        if param_count > param_limit:
            # Fallback to a smaller model if the primary one exceeds the limit
            # This is a safeguard, but the primary model should be within bounds.
            hidden_dim = 380 
            model = ResMLP(
                input_dim=input_dim,
                hidden_dim=hidden_dim,
                num_classes=num_classes,
                num_blocks=1,
                dropout_p=0.4
            ).to(device)

        # Training hyperparameters
        epochs = 300
        lr = 0.001
        weight_decay = 0.01
        label_smoothing = 0.1

        criterion = nn.CrossEntropyLoss(label_smoothing=label_smoothing)
        optimizer = optim.AdamW(model.parameters(), lr=lr, weight_decay=weight_decay)
        scheduler = optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=epochs)

        # Training loop
        model.train()
        for epoch in range(epochs):
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
