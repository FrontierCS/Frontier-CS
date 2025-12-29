import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim
from torch.optim.lr_scheduler import CosineAnnealingLR
import time
import math


class ResidualBlock(nn.Module):
    def __init__(self, in_features, out_features, dropout=0.1):
        super().__init__()
        self.fc1 = nn.Linear(in_features, out_features)
        self.bn1 = nn.BatchNorm1d(out_features)
        self.fc2 = nn.Linear(out_features, out_features)
        self.bn2 = nn.BatchNorm1d(out_features)
        self.dropout = nn.Dropout(dropout)
        
        self.shortcut = nn.Sequential()
        if in_features != out_features:
            self.shortcut = nn.Sequential(
                nn.Linear(in_features, out_features),
                nn.BatchNorm1d(out_features)
            )
    
    def forward(self, x):
        residual = self.shortcut(x)
        out = F.relu(self.bn1(self.fc1(x)))
        out = self.dropout(out)
        out = self.bn2(self.fc2(out))
        out += residual
        out = F.relu(out)
        return out


class BottleneckResidualBlock(nn.Module):
    def __init__(self, in_features, hidden_features, out_features, dropout=0.1):
        super().__init__()
        self.fc1 = nn.Linear(in_features, hidden_features)
        self.bn1 = nn.BatchNorm1d(hidden_features)
        self.fc2 = nn.Linear(hidden_features, hidden_features)
        self.bn2 = nn.BatchNorm1d(hidden_features)
        self.fc3 = nn.Linear(hidden_features, out_features)
        self.bn3 = nn.BatchNorm1d(out_features)
        self.dropout = nn.Dropout(dropout)
        
        self.shortcut = nn.Sequential()
        if in_features != out_features:
            self.shortcut = nn.Sequential(
                nn.Linear(in_features, out_features),
                nn.BatchNorm1d(out_features)
            )
    
    def forward(self, x):
        residual = self.shortcut(x)
        out = F.relu(self.bn1(self.fc1(x)))
        out = self.dropout(out)
        out = F.relu(self.bn2(self.fc2(out)))
        out = self.dropout(out)
        out = self.bn3(self.fc3(out))
        out += residual
        out = F.relu(out)
        return out


class EfficientNet(nn.Module):
    def __init__(self, input_dim, num_classes):
        super().__init__()
        
        # Stage 1: Initial projection (384 -> 512)
        self.stem = nn.Sequential(
            nn.Linear(input_dim, 512),
            nn.BatchNorm1d(512),
            nn.ReLU(),
            nn.Dropout(0.1)
        )
        
        # Stage 2: Bottleneck blocks (512 -> 512)
        self.stage2 = nn.Sequential(
            BottleneckResidualBlock(512, 256, 512, dropout=0.1),
            BottleneckResidualBlock(512, 256, 512, dropout=0.1),
        )
        
        # Stage 3: Reduce dimension (512 -> 384)
        self.stage3 = nn.Sequential(
            ResidualBlock(512, 384, dropout=0.1),
            ResidualBlock(384, 384, dropout=0.1),
        )
        
        # Stage 4: Further reduction (384 -> 256)
        self.stage4 = nn.Sequential(
            ResidualBlock(384, 256, dropout=0.1),
            ResidualBlock(256, 256, dropout=0.1),
        )
        
        # Stage 5: Final reduction (256 -> 128)
        self.stage5 = nn.Sequential(
            nn.Linear(256, 128),
            nn.BatchNorm1d(128),
            nn.ReLU(),
            nn.Dropout(0.1)
        )
        
        # Classification head
        self.classifier = nn.Sequential(
            nn.Linear(128, 128),
            nn.BatchNorm1d(128),
            nn.ReLU(),
            nn.Dropout(0.1),
            nn.Linear(128, num_classes)
        )
        
        # Initialize weights
        self._initialize_weights()
    
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
        x = self.stem(x)
        x = self.stage2(x)
        x = self.stage3(x)
        x = self.stage4(x)
        x = self.stage5(x)
        x = self.classifier(x)
        return x
    
    def count_parameters(self):
        return sum(p.numel() for p in self.parameters() if p.requires_grad)


def adjust_model_size(model, input_dim, num_classes, param_limit):
    """Adjust model architecture to stay within parameter limit"""
    param_count = model.count_parameters()
    
    # If already under limit, return
    if param_count <= param_limit:
        return model
    
    # Calculate reduction factor
    current_params = param_count
    target_params = param_limit
    reduction_factor = math.sqrt(target_params / current_params)
    
    # Create a more compact model
    hidden1 = max(128, int(512 * reduction_factor))
    hidden2 = max(128, int(384 * reduction_factor))
    hidden3 = max(64, int(256 * reduction_factor))
    
    class CompactNet(nn.Module):
        def __init__(self):
            super().__init__()
            self.net = nn.Sequential(
                nn.Linear(input_dim, hidden1),
                nn.BatchNorm1d(hidden1),
                nn.ReLU(),
                nn.Dropout(0.1),
                
                nn.Linear(hidden1, hidden2),
                nn.BatchNorm1d(hidden2),
                nn.ReLU(),
                nn.Dropout(0.1),
                
                nn.Linear(hidden2, hidden3),
                nn.BatchNorm1d(hidden3),
                nn.ReLU(),
                nn.Dropout(0.1),
                
                nn.Linear(hidden3, 128),
                nn.BatchNorm1d(128),
                nn.ReLU(),
                nn.Dropout(0.1),
                
                nn.Linear(128, num_classes)
            )
        
        def forward(self, x):
            return self.net(x)
    
    return CompactNet()


class EarlyStopping:
    def __init__(self, patience=15, min_delta=0.0001):
        self.patience = patience
        self.min_delta = min_delta
        self.counter = 0
        self.best_loss = None
        self.early_stop = False
    
    def __call__(self, val_loss):
        if self.best_loss is None:
            self.best_loss = val_loss
        elif val_loss > self.best_loss - self.min_delta:
            self.counter += 1
            if self.counter >= self.patience:
                self.early_stop = True
        else:
            self.best_loss = val_loss
            self.counter = 0
        return self.early_stop


class Solution:
    def solve(self, train_loader, val_loader, metadata: dict = None):
        input_dim = metadata["input_dim"]
        num_classes = metadata["num_classes"]
        param_limit = metadata["param_limit"]
        device = metadata.get("device", "cpu")
        
        # Initialize model
        model = EfficientNet(input_dim, num_classes)
        model = model.to(device)
        
        # Adjust model size if needed
        param_count = sum(p.numel() for p in model.parameters() if p.requires_grad)
        if param_count > param_limit:
            model = adjust_model_size(model, input_dim, num_classes, param_limit)
            model = model.to(device)
        
        # Double-check parameter count
        final_param_count = sum(p.numel() for p in model.parameters() if p.requires_grad)
        if final_param_count > param_limit:
            # Create minimal viable model
            class MinimalNet(nn.Module):
                def __init__(self):
                    super().__init__()
                    self.fc1 = nn.Linear(input_dim, 256)
                    self.bn1 = nn.BatchNorm1d(256)
                    self.fc2 = nn.Linear(256, 128)
                    self.bn2 = nn.BatchNorm1d(128)
                    self.fc3 = nn.Linear(128, num_classes)
                
                def forward(self, x):
                    x = F.relu(self.bn1(self.fc1(x)))
                    x = F.relu(self.bn2(self.fc2(x)))
                    x = self.fc3(x)
                    return x
            
            model = MinimalNet().to(device)
        
        # Training setup
        criterion = nn.CrossEntropyLoss()
        optimizer = optim.AdamW(model.parameters(), lr=0.001, weight_decay=0.01)
        scheduler = CosineAnnealingLR(optimizer, T_max=50, eta_min=1e-5)
        early_stopping = EarlyStopping(patience=15)
        
        # Training loop
        num_epochs = 100
        best_val_loss = float('inf')
        best_model_state = None
        
        for epoch in range(num_epochs):
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
                torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
                
                optimizer.step()
                
                train_loss += loss.item()
                _, predicted = outputs.max(1)
                train_total += targets.size(0)
                train_correct += predicted.eq(targets).sum().item()
            
            train_acc = 100. * train_correct / train_total
            
            # Validation phase
            model.eval()
            val_loss = 0.0
            val_correct = 0
            val_total = 0
            
            with torch.no_grad():
                for inputs, targets in val_loader:
                    inputs, targets = inputs.to(device), targets.to(device)
                    outputs = model(inputs)
                    loss = criterion(outputs, targets)
                    
                    val_loss += loss.item()
                    _, predicted = outputs.max(1)
                    val_total += targets.size(0)
                    val_correct += predicted.eq(targets).sum().item()
            
            val_acc = 100. * val_correct / val_total
            avg_val_loss = val_loss / len(val_loader)
            
            # Update scheduler
            scheduler.step()
            
            # Save best model
            if avg_val_loss < best_val_loss:
                best_val_loss = avg_val_loss
                best_model_state = {k: v.cpu().clone() for k, v in model.state_dict().items()}
            
            # Check early stopping
            if early_stopping(avg_val_loss):
                break
        
        # Load best model
        if best_model_state is not None:
            model.load_state_dict(best_model_state)
        
        model.eval()
        return model