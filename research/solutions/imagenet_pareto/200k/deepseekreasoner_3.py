import torch
import torch.nn as nn
import torch.optim as optim
from torch.optim.lr_scheduler import CosineAnnealingLR
import copy

class ChannelAttention(nn.Module):
    def __init__(self, channels, reduction=8):
        super().__init__()
        self.avg_pool = nn.AdaptiveAvgPool1d(1)
        self.fc = nn.Sequential(
            nn.Linear(channels, channels // reduction, bias=False),
            nn.ReLU(inplace=True),
            nn.Linear(channels // reduction, channels, bias=False),
            nn.Sigmoid()
        )
        
    def forward(self, x):
        b, c, _ = x.size()
        y = self.avg_pool(x).view(b, c)
        y = self.fc(y).view(b, c, 1)
        return x * y.expand_as(x)

class ResidualBlock(nn.Module):
    def __init__(self, in_channels, out_channels, stride=1, dropout=0.1):
        super().__init__()
        self.conv1 = nn.Conv1d(in_channels, out_channels, kernel_size=3, 
                              stride=stride, padding=1, bias=False)
        self.bn1 = nn.BatchNorm1d(out_channels)
        self.relu = nn.ReLU(inplace=True)
        self.dropout = nn.Dropout(dropout)
        self.conv2 = nn.Conv1d(out_channels, out_channels, kernel_size=3,
                              padding=1, bias=False)
        self.bn2 = nn.BatchNorm1d(out_channels)
        
        self.shortcut = nn.Sequential()
        if stride != 1 or in_channels != out_channels:
            self.shortcut = nn.Sequential(
                nn.Conv1d(in_channels, out_channels, kernel_size=1,
                         stride=stride, bias=False),
                nn.BatchNorm1d(out_channels)
            )
            
    def forward(self, x):
        residual = self.shortcut(x)
        out = self.conv1(x)
        out = self.bn1(out)
        out = self.relu(out)
        out = self.dropout(out)
        out = self.conv2(out)
        out = self.bn2(out)
        out += residual
        out = self.relu(out)
        return out

class EfficientNet(nn.Module):
    def __init__(self, input_dim=384, num_classes=128):
        super().__init__()
        
        # Initial projection to higher dimension
        self.conv1 = nn.Conv1d(1, 64, kernel_size=5, stride=1, padding=2, bias=False)
        self.bn1 = nn.BatchNorm1d(64)
        self.relu = nn.ReLU(inplace=True)
        self.maxpool = nn.MaxPool1d(kernel_size=3, stride=2, padding=1)
        
        # Residual blocks with attention
        self.layer1 = self._make_layer(64, 64, 2, stride=1)
        self.attn1 = ChannelAttention(64)
        
        self.layer2 = self._make_layer(64, 128, 2, stride=2)
        self.attn2 = ChannelAttention(128)
        
        self.layer3 = self._make_layer(128, 256, 1, stride=2)
        self.attn3 = ChannelAttention(256)
        
        # Adaptive pooling
        self.adaptive_pool = nn.AdaptiveAvgPool1d(1)
        
        # Final classifier
        self.fc = nn.Sequential(
            nn.Linear(256, 128),
            nn.BatchNorm1d(128),
            nn.ReLU(inplace=True),
            nn.Dropout(0.3),
            nn.Linear(128, num_classes)
        )
        
    def _make_layer(self, in_channels, out_channels, blocks, stride=1):
        layers = []
        layers.append(ResidualBlock(in_channels, out_channels, stride))
        for _ in range(1, blocks):
            layers.append(ResidualBlock(out_channels, out_channels))
        return nn.Sequential(*layers)
        
    def forward(self, x):
        # Reshape input from (batch, 384) to (batch, 1, 384)
        x = x.unsqueeze(1)
        
        x = self.conv1(x)
        x = self.bn1(x)
        x = self.relu(x)
        x = self.maxpool(x)
        
        x = self.layer1(x)
        x = self.attn1(x)
        
        x = self.layer2(x)
        x = self.attn2(x)
        
        x = self.layer3(x)
        x = self.attn3(x)
        
        x = self.adaptive_pool(x)
        x = torch.flatten(x, 1)
        
        x = self.fc(x)
        return x

class Solution:
    def solve(self, train_loader, val_loader, metadata: dict = None):
        if metadata is None:
            metadata = {}
            
        input_dim = metadata.get("input_dim", 384)
        num_classes = metadata.get("num_classes", 128)
        device = metadata.get("device", "cpu")
        param_limit = metadata.get("param_limit", 200000)
        
        # Initialize model
        model = EfficientNet(input_dim, num_classes).to(device)
        
        # Verify parameter count
        total_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
        if total_params > param_limit:
            # Scale down model if needed
            model = self._create_smaller_model(input_dim, num_classes, param_limit).to(device)
            total_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
        
        # Training setup
        criterion = nn.CrossEntropyLoss(label_smoothing=0.1)
        optimizer = optim.AdamW(model.parameters(), lr=0.001, weight_decay=0.01)
        scheduler = CosineAnnealingLR(optimizer, T_max=30, eta_min=1e-6)
        
        best_acc = 0.0
        best_model_state = None
        patience = 10
        patience_counter = 0
        
        num_epochs = 100
        
        for epoch in range(num_epochs):
            # Training phase
            model.train()
            train_loss = 0.0
            correct = 0
            total = 0
            
            for batch_idx, (inputs, targets) in enumerate(train_loader):
                inputs, targets = inputs.to(device), targets.to(device)
                
                optimizer.zero_grad()
                outputs = model(inputs)
                loss = criterion(outputs, targets)
                
                loss.backward()
                torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
                optimizer.step()
                
                train_loss += loss.item()
                _, predicted = outputs.max(1)
                total += targets.size(0)
                correct += predicted.eq(targets).sum().item()
            
            train_acc = 100. * correct / total
            avg_train_loss = train_loss / len(train_loader)
            
            # Validation phase
            model.eval()
            val_loss = 0.0
            correct = 0
            total = 0
            
            with torch.no_grad():
                for inputs, targets in val_loader:
                    inputs, targets = inputs.to(device), targets.to(device)
                    outputs = model(inputs)
                    loss = criterion(outputs, targets)
                    
                    val_loss += loss.item()
                    _, predicted = outputs.max(1)
                    total += targets.size(0)
                    correct += predicted.eq(targets).sum().item()
            
            val_acc = 100. * correct / total
            avg_val_loss = val_loss / len(val_loader)
            
            # Update scheduler
            scheduler.step()
            
            # Early stopping with patience
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
    
    def _create_smaller_model(self, input_dim, num_classes, param_limit):
        """Create a smaller model if the default exceeds parameter limit"""
        class SmallNet(nn.Module):
            def __init__(self, input_dim, num_classes):
                super().__init__()
                hidden1 = 256
                hidden2 = 192
                hidden3 = 128
                
                self.net = nn.Sequential(
                    nn.Linear(input_dim, hidden1),
                    nn.BatchNorm1d(hidden1),
                    nn.ReLU(inplace=True),
                    nn.Dropout(0.3),
                    
                    nn.Linear(hidden1, hidden2),
                    nn.BatchNorm1d(hidden2),
                    nn.ReLU(inplace=True),
                    nn.Dropout(0.3),
                    
                    nn.Linear(hidden2, hidden3),
                    nn.BatchNorm1d(hidden3),
                    nn.ReLU(inplace=True),
                    nn.Dropout(0.2),
                    
                    nn.Linear(hidden3, num_classes)
                )
            
            def forward(self, x):
                return self.net(x)
        
        # Try different architectures until we find one that fits
        for scale in [1.0, 0.9, 0.8, 0.7, 0.6]:
            hidden1 = int(256 * scale)
            hidden2 = int(192 * scale)
            hidden3 = int(128 * scale)
            
            model = nn.Sequential(
                nn.Linear(input_dim, hidden1),
                nn.BatchNorm1d(hidden1),
                nn.ReLU(inplace=True),
                nn.Dropout(0.3),
                
                nn.Linear(hidden1, hidden2),
                nn.BatchNorm1d(hidden2),
                nn.ReLU(inplace=True),
                nn.Dropout(0.3),
                
                nn.Linear(hidden2, hidden3),
                nn.BatchNorm1d(hidden3),
                nn.ReLU(inplace=True),
                nn.Dropout(0.2),
                
                nn.Linear(hidden3, num_classes)
            )
            
            total_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
            if total_params <= param_limit:
                return model
        
        # If still too large, create minimal model
        return SmallNet(input_dim, num_classes)