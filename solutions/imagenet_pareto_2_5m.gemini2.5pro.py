import torch
import torch.nn as nn
import torch.optim as optim
import copy

class SimpleResBlock(nn.Module):
    def __init__(self, dim, hidden_factor=4, dropout_p=0.3):
        super().__init__()
        hidden_dim = int(dim * hidden_factor)
        self.block = nn.Sequential(
            nn.Linear(dim, hidden_dim),
            nn.BatchNorm1d(hidden_dim),
            nn.GELU(),
            nn.Dropout(dropout_p),
            nn.Linear(hidden_dim, dim),
            nn.BatchNorm1d(dim)
        )
        self.activation = nn.GELU()
        self.dropout = nn.Dropout(dropout_p)

    def forward(self, x):
        residual = x
        out = self.block(x)
        out += residual
        out = self.activation(out)
        out = self.dropout(out)
        return out

class ImageNetParetoModel(nn.Module):
    def __init__(self, input_dim, num_classes, hidden_dim=526, dropout_p=0.3):
        super().__init__()
        self.embedding = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.BatchNorm1d(hidden_dim),
            nn.GELU(),
            nn.Dropout(dropout_p)
        )
        self.res_block = SimpleResBlock(hidden_dim, hidden_factor=4, dropout_p=dropout_p)
        self.classifier = nn.Linear(hidden_dim, num_classes)
        self._initialize_weights()

    def _initialize_weights(self):
        for m in self.modules():
            if isinstance(m, nn.Linear):
                nn.init.kaiming_normal_(m.weight, mode='fan_in', nonlinearity='relu')
                if m.bias is not None:
                    nn.init.constant_(m.bias, 0)
            elif isinstance(m, nn.BatchNorm1d):
                nn.init.constant_(m.weight, 1)
                nn.init.constant_(m.bias, 0)

    def forward(self, x):
        x = self.embedding(x)
        x = self.res_block(x)
        x = self.classifier(x)
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
                - param_limit: int (2,500,000)
                - baseline_accuracy: float (0.85)
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

        # This model has ~2,491,766 parameters with hidden_dim=526
        model = ImageNetParetoModel(
            input_dim=input_dim,
            num_classes=num_classes,
            hidden_dim=526,
            dropout_p=0.3
        ).to(device)

        EPOCHS = 350
        LEARNING_RATE = 1e-3
        WEIGHT_DECAY = 1e-4
        LABEL_SMOOTHING = 0.1
        PATIENCE = 60

        optimizer = optim.AdamW(model.parameters(), lr=LEARNING_RATE, weight_decay=WEIGHT_DECAY)
        criterion = nn.CrossEntropyLoss(label_smoothing=LABEL_SMOOTHING)
        scheduler = optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=EPOCHS, eta_min=1e-6)

        best_val_acc = 0.0
        best_model_state = None
        patience_counter = 0

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
                patience_counter = 0
            else:
                patience_counter += 1

            if patience_counter >= PATIENCE:
                break

        if best_model_state:
            model.load_state_dict(best_model_state)
        
        return model
