import torch
import torch.nn as nn
import torch.optim as optim
import copy
import numpy as np

class ResidualBlock(nn.Module):
    """A ResNet-style block for MLPs."""
    def __init__(self, dim, dropout_p=0.25):
        super().__init__()
        self.block = nn.Sequential(
            nn.Linear(dim, dim),
            nn.BatchNorm1d(dim),
            nn.ReLU(inplace=True),
            nn.Dropout(dropout_p),
            nn.Linear(dim, dim),
            nn.BatchNorm1d(dim),
        )
        self.relu = nn.ReLU(inplace=True)

    def forward(self, x):
        residual = self.block(x)
        return self.relu(x + residual)

class DeepMLP(nn.Module):
    """The main model, designed to be close to the 1M parameter limit."""
    def __init__(self, input_dim, num_classes, hidden_dim=588, dropout_p=0.3):
        super().__init__()
        self.input_layer = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.BatchNorm1d(hidden_dim),
            nn.ReLU(inplace=True),
            nn.Dropout(dropout_p),
        )
        
        self.res_block = ResidualBlock(hidden_dim, dropout_p)
        
        self.output_layer = nn.Linear(hidden_dim, num_classes)

    def forward(self, x):
        x = self.input_layer(x)
        x = self.res_block(x)
        x = self.output_layer(x)
        return x

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
                - param_limit: int (1,000,000)
                - baseline_accuracy: float (0.8)
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
        
        # Model selection: A deep MLP with residual connections, batch norm, and dropout.
        # The hidden dimension (588) is chosen to maximize parameter count under the 1M limit,
        # resulting in a model with ~997,964 parameters.
        model = DeepMLP(
            input_dim=input_dim,
            num_classes=num_classes,
            hidden_dim=588,
            dropout_p=0.3
        ).to(device)

        # Hyperparameters chosen for robust training on small datasets.
        NUM_EPOCHS = 1000
        MAX_LR = 0.015
        WEIGHT_DECAY = 0.01
        PATIENCE = 100
        LABEL_SMOOTHING = 0.1
        MIXUP_ALPHA = 0.4

        criterion = nn.CrossEntropyLoss(label_smoothing=LABEL_SMOOTHING)
        optimizer = optim.AdamW(model.parameters(), lr=MAX_LR, weight_decay=WEIGHT_DECAY)
        
        scheduler = optim.lr_scheduler.OneCycleLR(
            optimizer,
            max_lr=MAX_LR,
            epochs=NUM_EPOCHS,
            steps_per_epoch=len(train_loader)
        )

        best_val_acc = -1.0
        epochs_no_improve = 0
        best_model_state = None

        for epoch in range(NUM_EPOCHS):
            model.train()
            for inputs, targets in train_loader:
                inputs, targets = inputs.to(device), targets.to(device)

                # Mixup regularization
                lam = np.random.beta(MIXUP_ALPHA, MIXUP_ALPHA) if MIXUP_ALPHA > 0 else 1.0
                rand_index = torch.randperm(inputs.size(0)).to(device)
                target_a, target_b = targets, targets[rand_index]
                mixed_input = lam * inputs + (1 - lam) * inputs[rand_index, :]

                optimizer.zero_grad(set_to_none=True)
                
                outputs = model(mixed_input)
                loss = lam * criterion(outputs, target_a) + (1 - lam) * criterion(outputs, target_b)
                
                loss.backward()
                optimizer.step()
                scheduler.step()

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
            
            # Early stopping logic
            if val_acc > best_val_acc:
                best_val_acc = val_acc
                epochs_no_improve = 0
                best_model_state = copy.deepcopy(model.state_dict())
            else:
                epochs_no_improve += 1
            
            if epochs_no_improve >= PATIENCE:
                break
        
        # Load the best performing model on the validation set
        if best_model_state:
            model.load_state_dict(best_model_state)
            
        return model.to("cpu")