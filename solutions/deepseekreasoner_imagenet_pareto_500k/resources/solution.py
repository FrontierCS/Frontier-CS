import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim
from torch.optim.lr_scheduler import CosineAnnealingLR
import time
import warnings
warnings.filterwarnings("ignore")

class ResidualBlock(nn.Module):
    def __init__(self, in_channels, out_channels, stride=1, dropout=0.1):
        super().__init__()
        self.conv1 = nn.Linear(in_channels, out_channels)
        self.bn1 = nn.BatchNorm1d(out_channels)
        self.conv2 = nn.Linear(out_channels, out_channels)
        self.bn2 = nn.BatchNorm1d(out_channels)
        self.dropout = nn.Dropout(dropout)
        
        self.shortcut = nn.Sequential()
        if stride != 1 or in_channels != out_channels:
            self.shortcut = nn.Sequential(
                nn.Linear(in_channels, out_channels, bias=False),
                nn.BatchNorm1d(out_channels)
            )
    
    def forward(self, x):
        identity = self.shortcut(x)
        out = F.relu(self.bn1(self.conv1(x)))
        out = self.dropout(out)
        out = self.bn2(self.conv2(out))
        out += identity
        out = F.relu(out)
        return out

class CustomModel(nn.Module):
    def __init__(self, input_dim=384, num_classes=128, param_limit=500000):
        super().__init__()
        
        # Calculate layer dimensions to stay under parameter limit
        # Using bottleneck architecture with residual connections
        hidden1 = 512
        hidden2 = 256
        hidden3 = 256
        hidden4 = 128
        
        # Initial projection
        self.input_proj = nn.Sequential(
            nn.Linear(input_dim, hidden1),
            nn.BatchNorm1d(hidden1),
            nn.ReLU(),
            nn.Dropout(0.2)
        )
        
        # Residual blocks
        self.block1 = ResidualBlock(hidden1, hidden2, dropout=0.2)
        self.block2 = ResidualBlock(hidden2, hidden3, dropout=0.2)
        self.block3 = ResidualBlock(hidden3, hidden4, dropout=0.1)
        
        # Output layer
        self.output = nn.Linear(hidden4, num_classes)
        
        # Initialize weights
        self._initialize_weights()
        
        # Verify parameter count
        total_params = sum(p.numel() for p in self.parameters() if p.requires_grad)
        if total_params > param_limit:
            raise ValueError(f"Model has {total_params} parameters, exceeds {param_limit} limit")
    
    def _initialize_weights(self):
        for m in self.modules():
            if isinstance(m, nn.Linear):
                nn.init.kaiming_normal_(m.weight, mode='fan_out', nonlinearity='relu')
                if m.bias is not None:
                    nn.init.constant_(m.bias, 0)
            elif isinstance(m, nn.BatchNorm1d):
                nn.init.constant_(m.weight, 1)
                nn.init.constant_(m.bias, 0)
    
    def forward(self, x):
        x = self.input_proj(x)
        x = self.block1(x)
        x = self.block2(x)
        x = self.block3(x)
        x = self.output(x)
        return x

class Solution:
    def solve(self, train_loader, val_loader, metadata: dict = None) -> torch.nn.Module:
        if metadata is None:
            metadata = {}
        
        num_classes = metadata.get("num_classes", 128)
        input_dim = metadata.get("input_dim", 384)
        param_limit = metadata.get("param_limit", 500000)
        device_str = metadata.get("device", "cpu")
        device = torch.device(device_str)
        
        # Create model with parameter constraint
        model = CustomModel(input_dim, num_classes, param_limit)
        model = model.to(device)
        
        # Training hyperparameters
        epochs = 150
        lr = 0.001
        weight_decay = 1e-4
        
        # Optimizer and scheduler
        optimizer = optim.AdamW(model.parameters(), lr=lr, weight_decay=weight_decay)
        scheduler = CosineAnnealingLR(optimizer, T_max=epochs)
        
        # Loss function
        criterion = nn.CrossEntropyLoss()
        
        # Training loop with early stopping
        best_val_acc = 0.0
        best_model_state = None
        patience = 20
        patience_counter = 0
        
        for epoch in range(epochs):
            # Training phase
            model.train()
            train_loss = 0.0
            train_correct = 0
            train_total = 0
            
            for batch_idx, (inputs, targets) in enumerate(train_loader):
                inputs, targets = inputs.to(device), targets.to(device)
                
                optimizer.zero_grad()
                outputs = model(inputs)
                loss = criterion(outputs, targets)
                loss.backward()
                
                # Gradient clipping
                torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
                
                optimizer.step()
                
                train_loss += loss.item()
                _, predicted = outputs.max(1)
                train_total += targets.size(0)
                train_correct += predicted.eq(targets).sum().item()
            
            train_acc = 100. * train_correct / train_total
            
            # Validation phase
            model.eval()
            val_correct = 0
            val_total = 0
            
            with torch.no_grad():
                for inputs, targets in val_loader:
                    inputs, targets = inputs.to(device), targets.to(device)
                    outputs = model(inputs)
                    _, predicted = outputs.max(1)
                    val_total += targets.size(0)
                    val_correct += predicted.eq(targets).sum().item()
            
            val_acc = 100. * val_correct / val_total
            
            # Early stopping and model checkpointing
            if val_acc > best_val_acc:
                best_val_acc = val_acc
                best_model_state = model.state_dict().copy()
                patience_counter = 0
            else:
                patience_counter += 1
            
            # Update learning rate
            scheduler.step()
            
            # Early stopping
            if patience_counter >= patience and epoch > 50:
                break
        
        # Load best model
        if best_model_state is not None:
            model.load_state_dict(best_model_state)
        
        # Final training on combined train+val data for better generalization
        model.train()
        combined_loader = torch.utils.data.DataLoader(
            torch.utils.data.ConcatDataset([train_loader.dataset, val_loader.dataset]),
            batch_size=train_loader.batch_size,
            shuffle=True
        )
        
        # Fine-tuning with lower learning rate
        fine_tune_epochs = 30
        optimizer = optim.AdamW(model.parameters(), lr=lr/10, weight_decay=weight_decay)
        
        for epoch in range(fine_tune_epochs):
            for batch_idx, (inputs, targets) in enumerate(combined_loader):
                inputs, targets = inputs.to(device), targets.to(device)
                
                optimizer.zero_grad()
                outputs = model(inputs)
                loss = criterion(outputs, targets)
                loss.backward()
                torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=0.5)
                optimizer.step()
        
        model.eval()
        return model
