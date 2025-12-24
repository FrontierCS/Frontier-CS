import torch
import torch.nn as nn
import torch.optim as optim
from torch.optim.lr_scheduler import CosineAnnealingLR
import copy
import math

def count_parameters(model):
    return sum(p.numel() for p in model.parameters() if p.requires_grad)

class ResidualBlock(nn.Module):
    def __init__(self, in_features, out_features, dropout_rate=0.2):
        super().__init__()
        self.linear1 = nn.Linear(in_features, out_features)
        self.bn1 = nn.BatchNorm1d(out_features)
        self.linear2 = nn.Linear(out_features, out_features)
        self.bn2 = nn.BatchNorm1d(out_features)
        self.dropout = nn.Dropout(dropout_rate)
        self.relu = nn.ReLU()
        
        if in_features != out_features:
            self.shortcut = nn.Linear(in_features, out_features)
        else:
            self.shortcut = nn.Identity()
            
    def forward(self, x):
        residual = self.shortcut(x)
        out = self.linear1(x)
        out = self.bn1(out)
        out = self.relu(out)
        out = self.dropout(out)
        out = self.linear2(out)
        out = self.bn2(out)
        out += residual
        out = self.relu(out)
        return out

class EfficientNet(nn.Module):
    def __init__(self, input_dim, num_classes):
        super().__init__()
        # Calculate dimensions to stay under 2.5M params
        hidden1 = 1024
        hidden2 = 768
        hidden3 = 512
        hidden4 = 384
        
        # Initial projection
        self.input_proj = nn.Sequential(
            nn.Linear(input_dim, hidden1),
            nn.BatchNorm1d(hidden1),
            nn.ReLU(),
            nn.Dropout(0.3)
        )
        
        # Residual blocks
        self.block1 = ResidualBlock(hidden1, hidden2, 0.25)
        self.block2 = ResidualBlock(hidden2, hidden3, 0.2)
        self.block3 = ResidualBlock(hidden3, hidden4, 0.15)
        
        # Attention mechanism
        self.attention = nn.Sequential(
            nn.Linear(hidden4, hidden4 // 4),
            nn.ReLU(),
            nn.Linear(hidden4 // 4, hidden4),
            nn.Sigmoid()
        )
        
        # Final classifier
        self.classifier = nn.Sequential(
            nn.Linear(hidden4, hidden4 // 2),
            nn.BatchNorm1d(hidden4 // 2),
            nn.ReLU(),
            nn.Dropout(0.1),
            nn.Linear(hidden4 // 2, num_classes)
        )
        
    def forward(self, x):
        x = self.input_proj(x)
        x = self.block1(x)
        x = self.block2(x)
        x = self.block3(x)
        
        # Attention weighting
        attn_weights = self.attention(x)
        x = x * attn_weights
        
        return self.classifier(x)

class Solution:
    def solve(self, train_loader, val_loader, metadata: dict = None):
        device = metadata.get("device", "cpu")
        input_dim = metadata["input_dim"]
        num_classes = metadata["num_classes"]
        param_limit = metadata["param_limit"]
        
        # Create model with architecture tuned for 2.5M limit
        model = EfficientNet(input_dim, num_classes)
        model = model.to(device)
        
        # Verify parameter count
        param_count = count_parameters(model)
        if param_count > param_limit:
            # If too large, create a smaller model
            model = self._create_smaller_model(input_dim, num_classes, param_limit)
            model = model.to(device)
        
        # Training setup
        criterion = nn.CrossEntropyLoss()
        optimizer = optim.AdamW(
            model.parameters(),
            lr=0.001,
            weight_decay=0.01,
            betas=(0.9, 0.999)
        )
        
        # Cosine annealing scheduler
        scheduler = CosineAnnealingLR(
            optimizer,
            T_max=100,
            eta_min=1e-6
        )
        
        # Early stopping
        best_val_acc = 0.0
        best_model_state = None
        patience = 15
        patience_counter = 0
        
        # Training loop
        num_epochs = 200
        for epoch in range(num_epochs):
            # Training phase
            model.train()
            total_train_loss = 0.0
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
                
                total_train_loss += loss.item()
                _, predicted = outputs.max(1)
                train_total += targets.size(0)
                train_correct += predicted.eq(targets).sum().item()
            
            train_loss = total_train_loss / len(train_loader)
            train_acc = 100.0 * train_correct / train_total
            
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
            
            val_acc = 100.0 * val_correct / val_total
            
            # Learning rate schedule
            scheduler.step()
            
            # Early stopping
            if val_acc > best_val_acc:
                best_val_acc = val_acc
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
        """Create a smaller model if initial one exceeds parameter limit"""
        # Progressive scaling to stay under limit
        hidden_dims = [768, 512, 384, 256]
        
        for attempt in range(len(hidden_dims)):
            hidden1 = hidden_dims[attempt]
            hidden2 = max(hidden1 // 2, 256)
            hidden3 = max(hidden2 // 2, 128)
            
            model = nn.Sequential(
                nn.Linear(input_dim, hidden1),
                nn.BatchNorm1d(hidden1),
                nn.ReLU(),
                nn.Dropout(0.3),
                
                nn.Linear(hidden1, hidden2),
                nn.BatchNorm1d(hidden2),
                nn.ReLU(),
                nn.Dropout(0.2),
                
                nn.Linear(hidden2, hidden3),
                nn.BatchNorm1d(hidden3),
                nn.ReLU(),
                nn.Dropout(0.1),
                
                nn.Linear(hidden3, num_classes)
            )
            
            if count_parameters(model) <= param_limit:
                return model
        
        # Fallback to minimal model
        return nn.Sequential(
            nn.Linear(input_dim, 512),
            nn.ReLU(),
            nn.Linear(512, 256),
            nn.ReLU(),
            nn.Linear(256, num_classes)
        )
