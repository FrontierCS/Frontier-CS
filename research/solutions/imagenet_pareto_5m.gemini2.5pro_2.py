import torch
import torch.nn as nn
import torch.optim as optim
from torch.optim.lr_scheduler import CosineAnnealingLR
import copy

class ResBlock(nn.Module):
    """
    A residual block with two linear layers, batch normalization, SiLU activation, and dropout.
    """
    def __init__(self, dim, dropout_rate=0.25):
        super().__init__()
        self.block = nn.Sequential(
            nn.Linear(dim, dim),
            nn.BatchNorm1d(dim),
            nn.SiLU(),
            nn.Dropout(p=dropout_rate),
            nn.Linear(dim, dim),
            nn.BatchNorm1d(dim),
        )
        self.silu = nn.SiLU()
        self.dropout = nn.Dropout(p=dropout_rate)

    def forward(self, x):
        identity = x
        out = self.block(x)
        out += identity
        out = self.silu(out)
        out = self.dropout(out)
        return out

class ParetoModel(nn.Module):
    """
    A deep MLP model with residual connections, designed to maximize capacity
    within a given parameter budget.
    """
    def __init__(self, input_dim, num_classes, hidden_dim, num_blocks, dropout_rate):
        super().__init__()
        self.initial_projection = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.BatchNorm1d(hidden_dim),
            nn.SiLU(),
        )
        
        self.blocks = nn.Sequential(
            *[ResBlock(hidden_dim, dropout_rate) for _ in range(num_blocks)]
        )
        
        self.head = nn.Linear(hidden_dim, num_classes)

    def forward(self, x):
        x = self.initial_projection(x)
        x = self.blocks(x)
        x = self.head(x)
        return x

class Solution:
    def solve(self, train_loader, val_loader, metadata: dict = None) -> torch.nn.Module:
        """
        Train a model and return it.
        """
        device = torch.device(metadata.get("device", "cpu"))

        # Model parameters from metadata
        input_dim = metadata["input_dim"]
        num_classes = metadata["num_classes"]
        param_limit = metadata["param_limit"]

        # Tuned architecture hyperparameters to be close to the 5M parameter limit
        HIDDEN_DIM = 512
        NUM_BLOCKS = 9
        DROPOUT_RATE = 0.25

        model = ParetoModel(
            input_dim=input_dim,
            num_classes=num_classes,
            hidden_dim=HIDDEN_DIM,
            num_blocks=NUM_BLOCKS,
            dropout_rate=DROPOUT_RATE
        ).to(device)

        # Sanity check for parameter count, with a fallback if miscalculated
        param_count = sum(p.numel() for p in model.parameters() if p.requires_grad)
        if param_count > param_limit:
            # This fallback uses 8 blocks instead of 9, reducing parameters
            model = ParetoModel(
                input_dim=input_dim,
                num_classes=num_classes,
                hidden_dim=512,
                num_blocks=8,
                dropout_rate=DROPOUT_RATE
            ).to(device)

        # Tuned training hyperparameters
        EPOCHS = 300
        LEARNING_RATE = 0.001
        WEIGHT_DECAY = 0.01
        LABEL_SMOOTHING = 0.1

        criterion = nn.CrossEntropyLoss(label_smoothing=LABEL_SMOOTHING)
        optimizer = optim.AdamW(model.parameters(), lr=LEARNING_RATE, weight_decay=WEIGHT_DECAY)
        
        total_steps = EPOCHS * len(train_loader)
        scheduler = CosineAnnealingLR(optimizer, T_max=total_steps)

        best_val_acc = -1.0
        best_model_state = None

        for epoch in range(EPOCHS):
            model.train()
            for inputs, targets in train_loader:
                inputs, targets = inputs.to(device), targets.to(device)

                optimizer.zero_grad()
                outputs = model(inputs)
                loss = criterion(outputs, targets)
                loss.backward()
                optimizer.step()
                scheduler.step()
            
            # Validation phase to select the best model checkpoint
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
            if val_acc > best_val_acc:
                best_val_acc = val_acc
                best_model_state = copy.deepcopy(model.state_dict())

        # Load the best model state found during training
        if best_model_state:
            model.load_state_dict(best_model_state)
        
        model.eval()
        return model
