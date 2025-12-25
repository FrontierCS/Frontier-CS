import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim
from torch.optim.lr_scheduler import CosineAnnealingLR, ReduceLROnPlateau
import numpy as np
from collections import OrderedDict
import time

class Solution:
    def solve(self, train_loader, val_loader, metadata: dict = None) -> torch.nn.Module:
        device = torch.device(metadata["device"] if metadata and "device" in metadata else "cpu")
        input_dim = metadata["input_dim"] if metadata else 384
        num_classes = metadata["num_classes"] if metadata else 128
        param_limit = metadata["param_limit"] if metadata else 1000000
        
        # Model architecture designed to stay under 1M parameters
        class EfficientNet(nn.Module):
            def __init__(self, input_dim, num_classes):
                super().__init__()
                
                # Calculate dimensions to stay under 1M params
                # Strategy: Gradually reduce dimension with bottleneck layers
                hidden1 = 512
                hidden2 = 384
                hidden3 = 256
                hidden4 = 256
                hidden5 = 192
                
                # Main network with residual connections
                self.layers = nn.Sequential(OrderedDict([
                    # Initial projection
                    ('fc1', nn.Linear(input_dim, hidden1)),
                    ('bn1', nn.BatchNorm1d(hidden1)),
                    ('relu1', nn.ReLU(inplace=True)),
                    ('drop1', nn.Dropout(0.3)),
                    
                    # Bottleneck block 1
                    ('fc2', nn.Linear(hidden1, hidden2)),
                    ('bn2', nn.BatchNorm1d(hidden2)),
                    ('relu2', nn.ReLU(inplace=True)),
                    ('drop2', nn.Dropout(0.3)),
                    
                    # Bottleneck block 2 with residual
                    ('fc3', nn.Linear(hidden2, hidden3)),
                    ('bn3', nn.BatchNorm1d(hidden3)),
                    ('relu3', nn.ReLU(inplace=True)),
                    ('drop3', nn.Dropout(0.3)),
                    
                    # Bottleneck block 3
                    ('fc4', nn.Linear(hidden3, hidden4)),
                    ('bn4', nn.BatchNorm1d(hidden4)),
                    ('relu4', nn.ReLU(inplace=True)),
                    ('drop4', nn.Dropout(0.2)),
                    
                    # Final bottleneck
                    ('fc5', nn.Linear(hidden4, hidden5)),
                    ('bn5', nn.BatchNorm1d(hidden5)),
                    ('relu5', nn.ReLU(inplace=True)),
                    ('drop5', nn.Dropout(0.1)),
                ]))
                
                # Output layer
                self.fc_out = nn.Linear(hidden5, num_classes)
                
                # Initialize weights
                self._initialize_weights()
                
                # Verify parameter count
                self._verify_param_count(param_limit)
            
            def _initialize_weights(self):
                for m in self.modules():
                    if isinstance(m, nn.Linear):
                        nn.init.kaiming_normal_(m.weight, mode='fan_out', nonlinearity='relu')
                        if m.bias is not None:
                            nn.init.constant_(m.bias, 0)
                    elif isinstance(m, nn.BatchNorm1d):
                        nn.init.constant_(m.weight, 1)
                        nn.init.constant_(m.bias, 0)
            
            def _verify_param_count(self, limit):
                total = sum(p.numel() for p in self.parameters() if p.requires_grad)
                if total > limit:
                    raise ValueError(f"Model has {total} parameters, exceeding limit of {limit}")
            
            def forward(self, x):
                features = self.layers(x)
                return self.fc_out(features)
        
        # Create model
        model = EfficientNet(input_dim, num_classes).to(device)
        
        # Training configuration
        criterion = nn.CrossEntropyLoss()
        
        # Use AdamW with weight decay for better regularization
        optimizer = optim.AdamW(
            model.parameters(),
            lr=0.001,
            weight_decay=1e-4,
            betas=(0.9, 0.999)
        )
        
        # Learning rate scheduler
        scheduler = CosineAnnealingLR(optimizer, T_max=100, eta_min=1e-5)
        
        # Training loop with early stopping
        num_epochs = 150
        patience = 20
        best_val_acc = 0.0
        patience_counter = 0
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
                
                # Add L2 regularization
                l2_lambda = 1e-4
                l2_reg = torch.tensor(0.).to(device)
                for param in model.parameters():
                    l2_reg += torch.norm(param)
                loss += l2_lambda * l2_reg
                
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
            
            # Update learning rate
            scheduler.step()
            
            # Early stopping check
            if val_acc > best_val_acc:
                best_val_acc = val_acc
                best_model_state = model.state_dict().copy()
                patience_counter = 0
            else:
                patience_counter += 1
            
            # Early stopping
            if patience_counter >= patience:
                break
        
        # Load best model
        if best_model_state is not None:
            model.load_state_dict(best_model_state)
        
        # Final validation check
        model.eval()
        final_val_correct = 0
        final_val_total = 0
        
        with torch.no_grad():
            for inputs, targets in val_loader:
                inputs, targets = inputs.to(device), targets.to(device)
                outputs = model(inputs)
                _, predicted = outputs.max(1)
                final_val_total += targets.size(0)
                final_val_correct += predicted.eq(targets).sum().item()
        
        final_val_acc = final_val_correct / final_val_total
        
        # If validation accuracy is too low, do a quick retraining with different hyperparameters
        if final_val_acc < 0.8:
            # Simple fallback model
            class FallbackModel(nn.Module):
                def __init__(self, input_dim, num_classes):
                    super().__init__()
                    self.fc1 = nn.Linear(input_dim, 512)
                    self.bn1 = nn.BatchNorm1d(512)
                    self.drop1 = nn.Dropout(0.3)
                    self.fc2 = nn.Linear(512, 256)
                    self.bn2 = nn.BatchNorm1d(256)
                    self.drop2 = nn.Dropout(0.2)
                    self.fc3 = nn.Linear(256, num_classes)
                
                def forward(self, x):
                    x = F.relu(self.bn1(self.fc1(x)))
                    x = self.drop1(x)
                    x = F.relu(self.bn2(self.fc2(x)))
                    x = self.drop2(x)
                    return self.fc3(x)
            
            fallback_model = FallbackModel(input_dim, num_classes).to(device)
            
            # Quick training
            optimizer = optim.Adam(fallback_model.parameters(), lr=0.005)
            criterion = nn.CrossEntropyLoss()
            
            for epoch in range(50):
                fallback_model.train()
                for inputs, targets in train_loader:
                    inputs, targets = inputs.to(device), targets.to(device)
                    optimizer.zero_grad()
                    outputs = fallback_model(inputs)
                    loss = criterion(outputs, targets)
                    loss.backward()
                    optimizer.step()
            
            model = fallback_model
        
        # Final parameter count verification
        param_count = sum(p.numel() for p in model.parameters() if p.requires_grad)
        if param_count > param_limit:
            # Emergency reduction - create a smaller model
            class EmergencyModel(nn.Module):
                def __init__(self, input_dim, num_classes):
                    super().__init__()
                    self.fc1 = nn.Linear(input_dim, 256)
                    self.bn1 = nn.BatchNorm1d(256)
                    self.fc2 = nn.Linear(256, 128)
                    self.bn2 = nn.BatchNorm1d(128)
                    self.fc3 = nn.Linear(128, num_classes)
                
                def forward(self, x):
                    x = F.relu(self.bn1(self.fc1(x)))
                    x = F.relu(self.bn2(self.fc2(x)))
                    return self.fc3(x)
            
            emergency_model = EmergencyModel(input_dim, num_classes).to(device)
            
            # Quick training
            optimizer = optim.Adam(emergency_model.parameters(), lr=0.01)
            criterion = nn.CrossEntropyLoss()
            
            for epoch in range(30):
                emergency_model.train()
                for inputs, targets in train_loader:
                    inputs, targets = inputs.to(device), targets.to(device)
                    optimizer.zero_grad()
                    outputs = emergency_model(inputs)
                    loss = criterion(outputs, targets)
                    loss.backward()
                    optimizer.step()
            
            model = emergency_model
        
        return model
