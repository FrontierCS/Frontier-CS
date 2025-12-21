import torch
import torch.nn as nn
import torch.nn.functional as F
import math
from torch.optim import AdamW
from torch.optim.lr_scheduler import CosineAnnealingLR
import copy

class ResidualBlock(nn.Module):
    def __init__(self, in_channels, out_channels, dropout_rate=0.1):
        super().__init__()
        self.conv1 = nn.Linear(in_channels, out_channels)
        self.bn1 = nn.BatchNorm1d(out_channels)
        self.conv2 = nn.Linear(out_channels, out_channels)
        self.bn2 = nn.BatchNorm1d(out_channels)
        self.dropout = nn.Dropout(dropout_rate)
        
        self.shortcut = nn.Linear(in_channels, out_channels) if in_channels != out_channels else nn.Identity()
        
    def forward(self, x):
        identity = self.shortcut(x)
        out = self.conv1(x)
        out = self.bn1(out)
        out = F.relu(out)
        out = self.dropout(out)
        out = self.conv2(out)
        out = self.bn2(out)
        out += identity
        out = F.relu(out)
        return out

class EfficientMLP(nn.Module):
    def __init__(self, input_dim=384, num_classes=128, channels=[256, 384, 384, 256], dropout=0.2):
        super().__init__()
        layers = []
        current_dim = input_dim
        
        # First layer
        layers.append(nn.Linear(current_dim, channels[0]))
        layers.append(nn.BatchNorm1d(channels[0]))
        layers.append(nn.ReLU())
        layers.append(nn.Dropout(dropout))
        current_dim = channels[0]
        
        # Residual blocks
        for i in range(1, len(channels)):
            layers.append(ResidualBlock(current_dim, channels[i], dropout_rate=dropout))
            current_dim = channels[i]
            
        # Final layers
        layers.append(nn.Linear(current_dim, 512))
        layers.append(nn.BatchNorm1d(512))
        layers.append(nn.ReLU())
        layers.append(nn.Dropout(dropout))
        
        layers.append(nn.Linear(512, 256))
        layers.append(nn.BatchNorm1d(256))
        layers.append(nn.ReLU())
        layers.append(nn.Dropout(dropout))
        
        self.features = nn.Sequential(*layers)
        self.classifier = nn.Linear(256, num_classes)
        
    def forward(self, x):
        x = self.features(x)
        return self.classifier(x)

class Solution:
    def solve(self, train_loader, val_loader, metadata: dict = None) -> torch.nn.Module:
        device = metadata.get("device", "cpu")
        input_dim = metadata["input_dim"]
        num_classes = metadata["num_classes"]
        param_limit = metadata["param_limit"]
        
        # Create model with dynamic sizing based on param limit
        model = self._create_model(input_dim, num_classes, param_limit)
        model.to(device)
        
        # Verify parameter count
        param_count = sum(p.numel() for p in model.parameters() if p.requires_grad)
        if param_count > param_limit:
            # Scale down model
            model = self._create_smaller_model(input_dim, num_classes, param_limit)
            model.to(device)
            param_count = sum(p.numel() for p in model.parameters() if p.requires_grad)
        
        # Training setup
        optimizer = AdamW(model.parameters(), lr=0.001, weight_decay=0.01)
        scheduler = CosineAnnealingLR(optimizer, T_max=100, eta_min=1e-5)
        criterion = nn.CrossEntropyLoss()
        
        # Training loop
        num_epochs = 200
        best_acc = 0.0
        best_model_state = None
        patience = 20
        patience_counter = 0
        
        for epoch in range(num_epochs):
            # Training phase
            model.train()
            train_loss = 0.0
            for batch_idx, (data, target) in enumerate(train_loader):
                data, target = data.to(device), target.to(device)
                optimizer.zero_grad()
                output = model(data)
                loss = criterion(output, target)
                loss.backward()
                torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
                optimizer.step()
                train_loss += loss.item()
            
            # Validation phase
            model.eval()
            val_correct = 0
            val_total = 0
            with torch.no_grad():
                for data, target in val_loader:
                    data, target = data.to(device), target.to(device)
                    output = model(data)
                    pred = output.argmax(dim=1, keepdim=True)
                    val_correct += pred.eq(target.view_as(pred)).sum().item()
                    val_total += target.size(0)
            
            val_acc = val_correct / val_total
            scheduler.step()
            
            # Early stopping and model saving
            if val_acc > best_acc:
                best_acc = val_acc
                best_model_state = copy.deepcopy(model.state_dict())
                patience_counter = 0
            else:
                patience_counter += 1
            
            if patience_counter >= patience:
                break
        
        # Load best model
        if best_model_state is not None:
            model.load_state_dict(best_model_state)
        
        return model
    
    def _create_model(self, input_dim, num_classes, param_limit):
        # Try different architectures to stay within limit
        configs = [
            [256, 384, 384, 256],  # Deeper network
            [384, 512, 256],        # Medium depth
            [512, 512],             # Shallower but wider
        ]
        
        for channels in configs:
            model = EfficientMLP(input_dim, num_classes, channels)
            param_count = sum(p.numel() for p in model.parameters() if p.requires_grad)
            if param_count <= param_limit:
                return model
        
        # Fallback to minimal model
        return self._create_minimal_model(input_dim, num_classes, param_limit)
    
    def _create_smaller_model(self, input_dim, num_classes, param_limit):
        # Create progressively smaller models
        channels_list = [
            [256, 256, 256],
            [192, 256, 192],
            [128, 192, 128],
            [128, 128],
        ]
        
        for channels in channels_list:
            model = EfficientMLP(input_dim, num_classes, channels)
            param_count = sum(p.numel() for p in model.parameters() if p.requires_grad)
            if param_count <= param_limit:
                return model
        
        return self._create_minimal_model(input_dim, num_classes, param_limit)
    
    def _create_minimal_model(self, input_dim, num_classes, param_limit):
        class MinimalMLP(nn.Module):
            def __init__(self, input_dim, num_classes):
                super().__init__()
                hidden = 256
                # Adjust hidden size to fit within param limit
                max_hidden = min(512, (param_limit - num_classes) // (input_dim + 1))
                hidden = max(128, max_hidden)
                
                self.layers = nn.Sequential(
                    nn.Linear(input_dim, hidden),
                    nn.BatchNorm1d(hidden),
                    nn.ReLU(),
                    nn.Dropout(0.2),
                    nn.Linear(hidden, hidden // 2),
                    nn.BatchNorm1d(hidden // 2),
                    nn.ReLU(),
                    nn.Dropout(0.2),
                    nn.Linear(hidden // 2, num_classes)
                )
                
            def forward(self, x):
                return self.layers(x)
        
        model = MinimalMLP(input_dim, num_classes)
        return model
