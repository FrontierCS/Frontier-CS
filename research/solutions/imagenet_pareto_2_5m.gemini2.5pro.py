import torch
import torch.nn as nn
import torch.optim as optim
from copy import deepcopy

class BottleneckBlock(nn.Module):
    """A residual bottleneck block for an MLP."""
    def __init__(self, dim, inner_dim, dropout_rate=0.1):
        super().__init__()
        self.norm = nn.LayerNorm(dim)
        self.fc1 = nn.Linear(dim, inner_dim)
        self.act = nn.GELU()
        self.fc2 = nn.Linear(inner_dim, dim)
        self.dropout = nn.Dropout(dropout_rate)

    def forward(self, x):
        identity = x
        x = self.norm(x)
        x = self.fc1(x)
        x = self.act(x)
        x = self.dropout(x)
        x = self.fc2(x)
        x = self.dropout(x)
        x = x + identity
        return x

class ResMLP(nn.Module):
    """A deep MLP with residual connections."""
    def __init__(self, input_dim, num_classes, hidden_dim, inner_dim, num_blocks, dropout_rate=0.1):
        super().__init__()
        self.stem = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.LayerNorm(hidden_dim)
        )
        self.blocks = nn.ModuleList(
            [BottleneckBlock(hidden_dim, inner_dim, dropout_rate) for _ in range(num_blocks)]
        )
        self.head = nn.Sequential(
            nn.LayerNorm(hidden_dim),
            nn.Linear(hidden_dim, num_classes)
        )

    def forward(self, x):
        x = self.stem(x)
        for block in self.blocks:
            x = block(x)
        x = self.head(x)
        return x

class Solution:
    def solve(self, train_loader, val_loader, metadata: dict = None) -> torch.nn.Module:
        INPUT_DIM = metadata["input_dim"]
        NUM_CLASSES = metadata["num_classes"]
        DEVICE = metadata["device"]
        
        # Model architecture parameters chosen to maximize capacity within the budget
        HIDDEN_DIM = 960
        INNER_DIM = 240
        NUM_BLOCKS = 4
        DROPOUT_RATE = 0.1

        # Training hyperparameters
        MAX_EPOCHS = 300
        LEARNING_RATE = 3e-4
        WEIGHT_DECAY = 0.05
        LABEL_SMOOTHING = 0.1
        EARLY_STOPPING_PATIENCE = 30

        model = ResMLP(
            input_dim=INPUT_DIM,
            num_classes=NUM_CLASSES,
            hidden_dim=HIDDEN_DIM,
            inner_dim=INNER_DIM,
            num_blocks=NUM_BLOCKS,
            dropout_rate=DROPOUT_RATE,
        )
        model.to(DEVICE)

        criterion = nn.CrossEntropyLoss(label_smoothing=LABEL_SMOOTHING)
        optimizer = optim.AdamW(model.parameters(), lr=LEARNING_RATE, weight_decay=WEIGHT_DECAY)
        scheduler = optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=MAX_EPOCHS, eta_min=1e-6)

        best_val_acc = -1.0
        best_model_state = None
        patience_counter = 0

        for epoch in range(MAX_EPOCHS):
            # Training phase
            model.train()
            for inputs, targets in train_loader:
                inputs, targets = inputs.to(DEVICE), targets.to(DEVICE)
                
                optimizer.zero_grad()
                outputs = model(inputs)
                loss = criterion(outputs, targets)
                loss.backward()
                optimizer.step()

            # Validation phase
            model.eval()
            val_correct = 0
            val_total = 0
            with torch.no_grad():
                for inputs, targets in val_loader:
                    inputs, targets = inputs.to(DEVICE), targets.to(DEVICE)
                    outputs = model(inputs)
                    predicted = outputs.argmax(dim=1)
                    val_total += targets.size(0)
                    val_correct += (predicted == targets).sum().item()

            current_val_acc = val_correct / val_total

            if current_val_acc > best_val_acc:
                best_val_acc = current_val_acc
                best_model_state = deepcopy(model.state_dict())
                patience_counter = 0
            else:
                patience_counter += 1
                if patience_counter >= EARLY_STOPPING_PATIENCE:
                    break
            
            scheduler.step()

        # Load the best performing model on the validation set
        if best_model_state:
            model.load_state_dict(best_model_state)
        
        model.eval()
        return model