import torch
import torch.nn as nn
import torch.optim as optim
import copy

class ParetopNet(nn.Module):
    """
    A custom MLP architecture designed to maximize parameter usage under the 200,000 limit.
    Architecture: 384 -> 319 -> 169 -> 128
    Total parameters: 199,631
    """
    def __init__(self, input_dim: int, num_classes: int, dropout_rate: float = 0.4):
        super(ParetopNet, self).__init__()
        
        h1 = 319
        h2 = 169
        
        self.network = nn.Sequential(
            nn.Linear(input_dim, h1),
            nn.BatchNorm1d(h1),
            nn.ReLU(inplace=True),
            nn.Dropout(p=dropout_rate),
            
            nn.Linear(h1, h2),
            nn.BatchNorm1d(h2),
            nn.ReLU(inplace=True),
            nn.Dropout(p=dropout_rate),
            
            nn.Linear(h2, num_classes)
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.network(x)

class Solution:
    def solve(self, train_loader, val_loader, metadata: dict = None) -> torch.nn.Module:
        """
        Train a model and return it.
        
        Args:
            train_loader: PyTorch DataLoader with training data
            val_loader: PyTorch DataLoader with validation data
            metadata: Dict with problem-specific information
        
        Returns:
            Trained torch.nn.Module ready for evaluation
        """
        device = torch.device(metadata.get("device", "cpu"))
        input_dim = metadata["input_dim"]
        num_classes = metadata["num_classes"]

        model = ParetopNet(input_dim=input_dim, num_classes=num_classes).to(device)

        # Hyperparameters chosen for robust training on a small dataset
        N_EPOCHS = 250
        LEARNING_RATE = 3e-4
        WEIGHT_DECAY = 1e-2
        LABEL_SMOOTHING = 0.1
        PATIENCE = 35  # For early stopping

        optimizer = optim.AdamW(model.parameters(), lr=LEARNING_RATE, weight_decay=WEIGHT_DECAY)
        criterion = nn.CrossEntropyLoss(label_smoothing=LABEL_SMOOTHING)
        scheduler = optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=N_EPOCHS, eta_min=1e-6)

        best_val_acc = 0.0
        best_model_state = None
        epochs_no_improve = 0

        for epoch in range(N_EPOCHS):
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

            scheduler.step()

            # Early stopping logic: save the best model and stop if no improvement
            if val_acc > best_val_acc:
                best_val_acc = val_acc
                best_model_state = copy.deepcopy(model.state_dict())
                epochs_no_improve = 0
            else:
                epochs_no_improve += 1
                if epochs_no_improve >= PATIENCE:
                    break
        
        # Load the best performing model state
        if best_model_state:
            model.load_state_dict(best_model_state)
            
        # Ensure the final model is on CPU for the evaluation environment
        return model.to("cpu")