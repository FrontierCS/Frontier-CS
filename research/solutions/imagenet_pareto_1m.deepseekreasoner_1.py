import torch
import torch.nn as nn
import torch.optim as optim
from torch.optim.lr_scheduler import CosineAnnealingLR
import math

class ResidualBlock(nn.Module):
    def __init__(self, in_features, out_features, dropout_rate=0.2):
        super().__init__()
        self.linear1 = nn.Linear(in_features, out_features)
        self.bn1 = nn.BatchNorm1d(out_features)
        self.linear2 = nn.Linear(out_features, out_features)
        self.bn2 = nn.BatchNorm1d(out_features)
        self.dropout = nn.Dropout(dropout_rate)
        self.relu = nn.ReLU()
        
        self.shortcut = None
        if in_features != out_features:
            self.shortcut = nn.Linear(in_features, out_features)
        
    def forward(self, x):
        identity = x
        
        out = self.linear1(x)
        out = self.bn1(out)
        out = self.relu(out)
        out = self.dropout(out)
        
        out = self.linear2(out)
        out = self.bn2(out)
        
        if self.shortcut is not None:
            identity = self.shortcut(identity)
        
        out += identity
        out = self.relu(out)
        return out

class EfficientModel(nn.Module):
    def __init__(self, input_dim, num_classes):
        super().__init__()
        # Carefully designed architecture to maximize capacity within 1M params
        hidden1 = 512
        hidden2 = 384
        hidden3 = 320
        hidden4 = 256
        
        self.input_layer = nn.Sequential(
            nn.Linear(input_dim, hidden1),
            nn.BatchNorm1d(hidden1),
            nn.ReLU(),
            nn.Dropout(0.3)
        )
        
        self.res_block1 = ResidualBlock(hidden1, hidden2, dropout_rate=0.25)
        self.res_block2 = ResidualBlock(hidden2, hidden3, dropout_rate=0.2)
        self.res_block3 = ResidualBlock(hidden3, hidden4, dropout_rate=0.15)
        
        # Attention-like gating mechanism
        self.attention = nn.Sequential(
            nn.Linear(hidden4, hidden4 // 4),
            nn.ReLU(),
            nn.Linear(hidden4 // 4, hidden4),
            nn.Sigmoid()
        )
        
        self.output_layer = nn.Linear(hidden4, num_classes)
        
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
        x = self.input_layer(x)
        x = self.res_block1(x)
        x = self.res_block2(x)
        x = self.res_block3(x)
        
        # Apply attention gating
        attn_weights = self.attention(x)
        x = x * attn_weights + x  # Residual attention
        
        return self.output_layer(x)

class Solution:
    def solve(self, train_loader, val_loader, metadata: dict = None):
        device = torch.device(metadata.get("device", "cpu"))
        input_dim = metadata["input_dim"]
        num_classes = metadata["num_classes"]
        param_limit = metadata["param_limit"]
        
        # Create model with parameter constraint
        model = EfficientModel(input_dim, num_classes).to(device)
        
        # Verify parameter count
        total_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
        print(f"Model parameters: {total_params:,}")
        
        # Adjust model if over limit
        if total_params > param_limit:
            # Create simpler model if over limit
            model = self._create_simpler_model(input_dim, num_classes).to(device)
            total_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
            print(f"Adjusted model parameters: {total_params:,}")
        
        # Training setup
        criterion = nn.CrossEntropyLoss()
        optimizer = optim.AdamW(model.parameters(), lr=0.001, weight_decay=1e-4)
        scheduler = CosineAnnealingLR(optimizer, T_max=100, eta_min=1e-6)
        
        # Mixed precision training for efficiency
        scaler = torch.cuda.amp.GradScaler() if device.type == 'cuda' else None
        
        best_val_acc = 0
        best_model_state = None
        patience = 15
        patience_counter = 0
        
        num_epochs = 200
        
        for epoch in range(num_epochs):
            # Training phase
            model.train()
            train_loss = 0
            correct = 0
            total = 0
            
            for batch_idx, (inputs, targets) in enumerate(train_loader):
                inputs, targets = inputs.to(device), targets.to(device)
                
                optimizer.zero_grad()
                
                if scaler is not None:
                    with torch.cuda.amp.autocast():
                        outputs = model(inputs)
                        loss = criterion(outputs, targets)
                    scaler.scale(loss).backward()
                    scaler.step(optimizer)
                    scaler.update()
                else:
                    outputs = model(inputs)
                    loss = criterion(outputs, targets)
                    loss.backward()
                    optimizer.step()
                
                train_loss += loss.item()
                _, predicted = outputs.max(1)
                total += targets.size(0)
                correct += predicted.eq(targets).sum().item()
            
            train_acc = 100. * correct / total
            
            # Validation phase
            model.eval()
            val_loss = 0
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
            
            # Update scheduler
            scheduler.step()
            
            # Early stopping with patience
            if val_acc > best_val_acc:
                best_val_acc = val_acc
                best_model_state = {k: v.cpu().clone() for k, v in model.state_dict().items()}
                patience_counter = 0
            else:
                patience_counter += 1
            
            if epoch % 20 == 0:
                print(f'Epoch {epoch:3d}: Train Acc: {train_acc:.2f}%, Val Acc: {val_acc:.2f}%')
            
            if patience_counter >= patience:
                print(f'Early stopping at epoch {epoch}')
                break
        
        # Load best model
        if best_model_state is not None:
            model.load_state_dict(best_model_state)
        
        return model
    
    def _create_simpler_model(self, input_dim, num_classes):
        """Fallback model if main model exceeds parameter limit"""
        class SimpleModel(nn.Module):
            def __init__(self, input_dim, num_classes):
                super().__init__()
                hidden1 = 384
                hidden2 = 256
                hidden3 = 192
                
                self.network = nn.Sequential(
                    nn.Linear(input_dim, hidden1),
                    nn.BatchNorm1d(hidden1),
                    nn.ReLU(),
                    nn.Dropout(0.3),
                    
                    nn.Linear(hidden1, hidden2),
                    nn.BatchNorm1d(hidden2),
                    nn.ReLU(),
                    nn.Dropout(0.25),
                    
                    nn.Linear(hidden2, hidden3),
                    nn.BatchNorm1d(hidden3),
                    nn.ReLU(),
                    nn.Dropout(0.2),
                    
                    nn.Linear(hidden3, num_classes)
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
                return self.network(x)
        
        return SimpleModel(input_dim, num_classes)
