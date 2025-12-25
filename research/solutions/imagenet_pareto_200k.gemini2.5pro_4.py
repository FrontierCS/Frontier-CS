import torch
import torch.nn as nn
import copy

class ResidualBlock(nn.Module):
    def __init__(self, size, dropout_p):
        super().__init__()
        self.fc1 = nn.Linear(size, size)
        self.bn1 = nn.BatchNorm1d(size)
        self.act = nn.GELU()
        self.fc2 = nn.Linear(size, size)
        self.bn2 = nn.BatchNorm1d(size)
        self.dropout = nn.Dropout(dropout_p)

    def forward(self, x):
        residual = x
        out = self.fc1(x)
        out = self.bn1(out)
        out = self.act(out)
        out = self.dropout(out)
        out = self.fc2(out)
        out = self.bn2(out)
        out = self.dropout(out)
        out += residual
        out = self.act(out)
        return out

class CustomModel(nn.Module):
    def __init__(self, input_dim, num_classes, hidden_dim, dropout_p):
        super().__init__()
        self.input_layer = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.BatchNorm1d(hidden_dim),
            nn.GELU(),
            nn.Dropout(dropout_p / 2)
        )
        self.res_block = ResidualBlock(hidden_dim, dropout_p)
        self.output_layer = nn.Linear(hidden_dim, num_classes)
        
        # Total parameters for h=211: 199,141
        # input_layer: (384*211+211) + (2*211) = 81,697
        # res_block: 2*(211*211+211) + 2*(2*211) = 90,308
        # output_layer: 211*128+128 = 27,136

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
                - param_limit: int (200,000)
                - baseline_accuracy: float (0.65)
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
        
        # Hyperparameters
        hidden_dim = 211
        dropout_p = 0.25
        epochs = 250
        lr = 0.001
        weight_decay = 0.01
        label_smoothing = 0.1

        model = CustomModel(
            input_dim=input_dim,
            num_classes=num_classes,
            hidden_dim=hidden_dim,
            dropout_p=dropout_p
        ).to(device)

        optimizer = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=weight_decay)
        scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=epochs)
        criterion = nn.CrossEntropyLoss(label_smoothing=label_smoothing)

        best_val_accuracy = 0.0
        best_model_state = None

        for epoch in range(epochs):
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
            correct = 0
            total = 0
            with torch.no_grad():
                for inputs, targets in val_loader:
                    inputs, targets = inputs.to(device), targets.to(device)
                    outputs = model(inputs)
                    _, predicted = torch.max(outputs.data, 1)
                    total += targets.size(0)
                    correct += (predicted == targets).sum().item()
            
            val_accuracy = correct / total
            if val_accuracy > best_val_accuracy:
                best_val_accuracy = val_accuracy
                best_model_state = copy.deepcopy(model.state_dict())

        if best_model_state:
            model.load_state_dict(best_model_state)
        
        model.eval()
        return model
