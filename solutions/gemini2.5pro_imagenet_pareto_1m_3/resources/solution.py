import torch
import torch.nn as nn
import torch.optim as optim
from torch.optim.lr_scheduler import CosineAnnealingLR

class SimpleResidualBlock(nn.Module):
    def __init__(self, size: int, dropout_p: float):
        super().__init__()
        self.block = nn.Sequential(
            nn.Linear(size, size),
            nn.BatchNorm1d(size),
            nn.GELU(),
            nn.Dropout(p=dropout_p)
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return x + self.block(x)

class Model(nn.Module):
    def __init__(self, input_dim: int, num_classes: int, hidden_dim: int, num_blocks: int, dropout_p: float):
        super().__init__()
        self.input_layer = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.BatchNorm1d(hidden_dim),
            nn.GELU(),
            nn.Dropout(p=dropout_p)
        )
        
        layers = [SimpleResidualBlock(hidden_dim, dropout_p) for _ in range(num_blocks)]
        self.residual_layers = nn.Sequential(*layers)
        
        self.output_layer = nn.Linear(hidden_dim, num_classes)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self.input_layer(x)
        x = self.residual_layers(x)
        x = self.output_layer(x)
        return x

class Solution:
    def solve(self, train_loader, val_loader, metadata: dict = None) -> torch.nn.Module:
        # Architecture and training hyperparameters are tuned to maximize accuracy
        # under the 1,000,000 parameter constraint. The architecture is a deep
        # MLP with residual connections, batch normalization, and dropout.
        # The training uses AdamW, CosineAnnealingLR, and label smoothing.
        # Calculated params for this config: 994,583
        
        # --- Configuration ---
        HIDDEN_DIM = 495
        NUM_BLOCKS = 3
        DROPOUT_P = 0.4
        
        NUM_EPOCHS = 350
        LEARNING_RATE = 1e-3
        WEIGHT_DECAY = 1e-4
        LABEL_SMOOTHING = 0.1

        # --- Setup ---
        device = torch.device(metadata.get("device", "cpu"))
        input_dim = metadata["input_dim"]
        num_classes = metadata["num_classes"]

        model = Model(
            input_dim=input_dim,
            num_classes=num_classes,
            hidden_dim=HIDDEN_DIM,
            num_blocks=NUM_BLOCKS,
            dropout_p=DROPOUT_P
        ).to(device)

        optimizer = optim.AdamW(model.parameters(), lr=LEARNING_RATE, weight_decay=WEIGHT_DECAY)
        scheduler = CosineAnnealingLR(optimizer, T_max=NUM_EPOCHS)
        criterion = nn.CrossEntropyLoss(label_smoothing=LABEL_SMOOTHING)

        # --- Training Loop ---
        model.train()
        for epoch in range(NUM_EPOCHS):
            for inputs, targets in train_loader:
                inputs, targets = inputs.to(device), targets.to(device)
                
                outputs = model(inputs)
                loss = criterion(outputs, targets)
                
                optimizer.zero_grad()
                loss.backward()
                optimizer.step()
            
            scheduler.step()
            
        return model
