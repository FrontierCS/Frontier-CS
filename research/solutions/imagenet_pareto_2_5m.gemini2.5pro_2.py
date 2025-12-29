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
                - param_limit: int (2,500,000)
                - baseline_accuracy: float (0.85)
                - train_samples: int
                - val_samples: int
                - test_samples: int
                - device: str ("cpu")
        
        Returns:
            Trained torch.nn.Module ready for evaluation
        """

        device = torch.device(metadata["device"])
        input_dim = metadata["input_dim"]
        num_classes = metadata["num_classes"]

        # --- Model Definition ---
        # A ResNet-style block for MLPs
        class ResBlock(nn.Module):
            def __init__(self, dim, dropout_p=0.3):
                super().__init__()
                self.block = nn.Sequential(
                    nn.Linear(dim, dim),
                    nn.BatchNorm1d(dim),
                    nn.ReLU(inplace=True),
                    nn.Dropout(p=dropout_p),
                    nn.Linear(dim, dim),
                    nn.BatchNorm1d(dim)
                )
                self.relu = nn.ReLU(inplace=True)

            def forward(self, x):
                identity = x
                out = self.block(x)
                out += identity
                out = self.relu(out)
                return out

        # The main model architecture, designed to be close to the 2.5M param limit
        class HighCapacityMLP(nn.Module):
            def __init__(self, input_dim, num_classes, hidden_dim=990, dropout_p=0.3):
                super().__init__()
                self.input_layer = nn.Sequential(
                    nn.Linear(input_dim, hidden_dim),
                    nn.BatchNorm1d(hidden_dim),
                    nn.ReLU(inplace=True),
                    nn.Dropout(p=dropout_p)
                )
                
                self.res_block = ResBlock(hidden_dim, dropout_p=dropout_p)
                
                self.output_layer = nn.Linear(hidden_dim, num_classes)

            def forward(self, x):
                x = self.input_layer(x)
                x = self.res_block(x)
                x = self.output_layer(x)
                return x
        
        model = HighCapacityMLP(input_dim, num_classes).to(device)

        # --- Hyperparameters and Training Setup ---
        epochs = 300
        learning_rate = 3e-4
        weight_decay = 1e-2
        label_smoothing = 0.1
        early_stopping_patience = 35

        criterion = nn.CrossEntropyLoss(label_smoothing=label_smoothing)
        optimizer = optim.AdamW(model.parameters(), lr=learning_rate, weight_decay=weight_decay)
        scheduler = optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=epochs, eta_min=1e-6)

        best_val_acc = 0.0
        epochs_no_improve = 0
        best_model_state = None

        # --- Training Loop ---
        for epoch in range(epochs):
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
            val_correct = 0
            val_total = 0
            with torch.no_grad():
                for inputs, targets in val_loader:
                    inputs, targets = inputs.to(device), targets.to(device)
                    outputs = model(inputs)
                    _, predicted = torch.max(outputs.data, 1)
                    val_total += targets.size(0)
                    val_correct += (predicted == targets).sum().item()
            
            current_val_acc = val_correct / val_total

            # Check for improvement and update best model state
            if current_val_acc > best_val_acc:
                best_val_acc = current_val_acc
                epochs_no_improve = 0
                # Use a deepcopy to prevent the state from being modified during continued training
                best_model_state = {k: v.clone() for k, v in model.state_dict().items()}
            else:
                epochs_no_improve += 1
            
            # Early stopping
            if epochs_no_improve >= early_stopping_patience:
                break
            
            scheduler.step()

        # Load the best performing model
        if best_model_state:
            model.load_state_dict(best_model_state)

        return model