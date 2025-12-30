import torch
import torch.nn as nn
import torch.optim as optim
import copy

class _Model(nn.Module):
    def __init__(self, input_dim: int, num_classes: int):
        super().__init__()
        # This architecture is a deep MLP with BatchNorm and Dropout, designed to
        # maximize model capacity under the 500,000 parameter constraint while
        # providing strong regularization for the small dataset.
        # Total trainable parameters: 499,428
        self.layers = nn.Sequential(
            nn.Linear(input_dim, 600),
            nn.BatchNorm1d(600),
            nn.ReLU(inplace=True),
            nn.Dropout(0.5),
            
            nn.Linear(600, 300),
            nn.BatchNorm1d(300),
            nn.ReLU(inplace=True),
            nn.Dropout(0.3),

            nn.Linear(300, 200),
            nn.BatchNorm1d(200),
            nn.ReLU(inplace=True),
            nn.Dropout(0.3),

            nn.Linear(200, num_classes)
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.layers(x)


class Solution:
    def solve(self, train_loader: torch.utils.data.DataLoader, 
              val_loader: torch.utils.data.DataLoader, 
              metadata: dict = None) -> torch.nn.Module:
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

        model = _Model(input_dim, num_classes).to(device)

        # Hyperparameters chosen for robust training and good generalization.
        # A longer training schedule with cosine annealing helps find a good minimum.
        num_epochs = 400
        learning_rate = 1e-3
        weight_decay = 5e-4
        
        criterion = nn.CrossEntropyLoss()
        optimizer = optim.AdamW(model.parameters(), lr=learning_rate, weight_decay=weight_decay)
        scheduler = optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=num_epochs)

        best_val_accuracy = 0.0
        best_model_state = None

        for epoch in range(num_epochs):
            # Training phase
            model.train()
            for inputs, targets in train_loader:
                inputs, targets = inputs.to(device), targets.to(device)
                
                optimizer.zero_grad()
                outputs = model(inputs)
                loss = criterion(outputs, targets)
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
            
            current_val_accuracy = correct / total
            
            # Save the model state with the best validation accuracy (early stopping)
            if current_val_accuracy > best_val_accuracy:
                best_val_accuracy = current_val_accuracy
                best_model_state = copy.deepcopy(model.state_dict())

        # Load the best performing model state for the final return
        if best_model_state:
            model.load_state_dict(best_model_state)
            
        # Ensure the model is on CPU for evaluation as per environment spec
        return model.to(torch.device("cpu"))