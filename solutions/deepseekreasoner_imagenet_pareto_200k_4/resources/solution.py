import torch
import torch.nn as nn
import torch.optim as optim
from torch.optim.lr_scheduler import ReduceLROnPlateau
import time

class ResidualBlock(nn.Module):
    def __init__(self, in_dim, out_dim, stride=1, dropout=0.2):
        super().__init__()
        self.bn1 = nn.BatchNorm1d(in_dim)
        self.relu = nn.ReLU(inplace=True)
        self.conv1 = nn.Linear(in_dim, out_dim)
        self.bn2 = nn.BatchNorm1d(out_dim)
        self.conv2 = nn.Linear(out_dim, out_dim)
        self.dropout = nn.Dropout(dropout)
        
        self.shortcut = nn.Sequential()
        if stride != 1 or in_dim != out_dim:
            self.shortcut = nn.Linear(in_dim, out_dim)
    
    def forward(self, x):
        identity = x
        out = self.bn1(x)
        out = self.relu(out)
        out = self.conv1(out)
        out = self.bn2(out)
        out = self.relu(out)
        out = self.dropout(out)
        out = self.conv2(out)
        out += self.shortcut(identity)
        return out

class EfficientNet(nn.Module):
    def __init__(self, input_dim=384, num_classes=128):
        super().__init__()
        
        # Calculate dimensions to stay under 200K parameters
        hidden1 = 320
        hidden2 = 256
        hidden3 = 192
        hidden4 = 128
        
        # Initial projection
        self.input_proj = nn.Sequential(
            nn.Linear(input_dim, hidden1),
            nn.BatchNorm1d(hidden1),
            nn.ReLU(inplace=True),
            nn.Dropout(0.1)
        )
        
        # Residual blocks
        self.block1 = ResidualBlock(hidden1, hidden2, dropout=0.2)
        self.block2 = ResidualBlock(hidden2, hidden3, dropout=0.2)
        self.block3 = ResidualBlock(hidden3, hidden4, dropout=0.2)
        
        # Final layers
        self.final_bn = nn.BatchNorm1d(hidden4)
        self.final_relu = nn.ReLU(inplace=True)
        self.final_dropout = nn.Dropout(0.1)
        self.classifier = nn.Linear(hidden4, num_classes)
        
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
        x = self.input_proj(x)
        x = self.block1(x)
        x = self.block2(x)
        x = self.block3(x)
        x = self.final_bn(x)
        x = self.final_relu(x)
        x = self.final_dropout(x)
        x = self.classifier(x)
        return x

class Solution:
    def solve(self, train_loader, val_loader, metadata: dict = None):
        if metadata is None:
            metadata = {}
        
        device = metadata.get("device", "cpu")
        num_classes = metadata.get("num_classes", 128)
        input_dim = metadata.get("input_dim", 384)
        param_limit = metadata.get("param_limit", 200000)
        
        # Create model
        model = EfficientNet(input_dim=input_dim, num_classes=num_classes)
        model.to(device)
        
        # Verify parameter count
        total_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
        if total_params > param_limit:
            # Scale down architecture if needed
            return self._create_smaller_model(input_dim, num_classes, param_limit, device)
        
        # Training setup
        criterion = nn.CrossEntropyLoss()
        optimizer = optim.AdamW(model.parameters(), lr=0.001, weight_decay=1e-4)
        scheduler = ReduceLROnPlateau(optimizer, mode='max', factor=0.5, patience=5, verbose=False)
        
        # Training parameters
        epochs = 150
        best_acc = 0.0
        patience = 15
        patience_counter = 0
        
        for epoch in range(epochs):
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
                
                # Gradient clipping
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
            
            # Update learning rate
            scheduler.step(val_acc)
            
            # Early stopping check
            if val_acc > best_acc:
                best_acc = val_acc
                best_model_state = model.state_dict().copy()
                patience_counter = 0
            else:
                patience_counter += 1
            
            if patience_counter >= patience:
                break
        
        # Load best model
        model.load_state_dict(best_model_state)
        
        # Final validation check
        model.eval()
        final_val_acc = self._evaluate(model, val_loader, device)
        
        # If validation accuracy is too low, train a bit more with different settings
        if final_val_acc < 65.0 and epoch < epochs - 50:
            return self._train_with_adjusted_settings(train_loader, val_loader, metadata)
        
        return model
    
    def _evaluate(self, model, loader, device):
        model.eval()
        correct = 0
        total = 0
        with torch.no_grad():
            for inputs, targets in loader:
                inputs, targets = inputs.to(device), targets.to(device)
                outputs = model(inputs)
                _, predicted = outputs.max(1)
                total += targets.size(0)
                correct += predicted.eq(targets).sum().item()
        return 100. * correct / total
    
    def _create_smaller_model(self, input_dim, num_classes, param_limit, device):
        """Create a smaller model if the original exceeds parameter limit"""
        class SmallerNet(nn.Module):
            def __init__(self, input_dim, num_classes):
                super().__init__()
                self.net = nn.Sequential(
                    nn.Linear(input_dim, 256),
                    nn.BatchNorm1d(256),
                    nn.ReLU(inplace=True),
                    nn.Dropout(0.2),
                    
                    nn.Linear(256, 192),
                    nn.BatchNorm1d(192),
                    nn.ReLU(inplace=True),
                    nn.Dropout(0.2),
                    
                    nn.Linear(192, 128),
                    nn.BatchNorm1d(128),
                    nn.ReLU(inplace=True),
                    nn.Dropout(0.1),
                    
                    nn.Linear(128, num_classes)
                )
                
                # Initialize weights
                for m in self.modules():
                    if isinstance(m, nn.Linear):
                        nn.init.kaiming_normal_(m.weight, mode='fan_out', nonlinearity='relu')
                        if m.bias is not None:
                            nn.init.constant_(m.bias, 0)
                    elif isinstance(m, nn.BatchNorm1d):
                        nn.init.constant_(m.weight, 1)
                        nn.init.constant_(m.bias, 0)
            
            def forward(self, x):
                return self.net(x)
        
        model = SmallerNet(input_dim, num_classes)
        model.to(device)
        return model
    
    def _train_with_adjusted_settings(self, train_loader, val_loader, metadata):
        """Alternative training with different settings"""
        device = metadata.get("device", "cpu")
        num_classes = metadata.get("num_classes", 128)
        input_dim = metadata.get("input_dim", 384)
        
        # Create a simpler model
        class SimpleNet(nn.Module):
            def __init__(self, input_dim, num_classes):
                super().__init__()
                self.net = nn.Sequential(
                    nn.Linear(input_dim, 320),
                    nn.BatchNorm1d(320),
                    nn.ReLU(inplace=True),
                    nn.Dropout(0.3),
                    
                    nn.Linear(320, 256),
                    nn.BatchNorm1d(256),
                    nn.ReLU(inplace=True),
                    nn.Dropout(0.3),
                    
                    nn.Linear(256, num_classes)
                )
            
            def forward(self, x):
                return self.net(x)
        
        model = SimpleNet(input_dim, num_classes)
        model.to(device)
        
        # Stronger regularization
        criterion = nn.CrossEntropyLoss()
        optimizer = optim.AdamW(model.parameters(), lr=0.0005, weight_decay=1e-3)
        scheduler = optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=100)
        
        epochs = 120
        best_acc = 0.0
        
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
            
            # Validate periodically
            if (epoch + 1) % 5 == 0:
                model.eval()
                correct = 0
                total = 0
                with torch.no_grad():
                    for inputs, targets in val_loader:
                        inputs, targets = inputs.to(device), targets.to(device)
                        outputs = model(inputs)
                        _, predicted = outputs.max(1)
                        total += targets.size(0)
                        correct += predicted.eq(targets).sum().item()
                
                val_acc = 100. * correct / total
                if val_acc > best_acc:
                    best_acc = val_acc
                    best_state = model.state_dict().copy()
        
        model.load_state_dict(best_state)
        return model
