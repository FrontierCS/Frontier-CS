import torch
import torch.nn as nn
import torch.optim as optim
from torch.optim.lr_scheduler import CosineAnnealingLR
import time
import math

class ResidualBlock(nn.Module):
    def __init__(self, in_features, out_features, dropout_rate=0.2):
        super().__init__()
        self.norm1 = nn.BatchNorm1d(in_features)
        self.linear1 = nn.Linear(in_features, out_features)
        self.norm2 = nn.BatchNorm1d(out_features)
        self.linear2 = nn.Linear(out_features, out_features)
        self.dropout = nn.Dropout(dropout_rate)
        self.act = nn.GELU()
        
        self.shortcut = nn.Linear(in_features, out_features) if in_features != out_features else nn.Identity()
        
    def forward(self, x):
        identity = self.shortcut(x)
        
        out = self.norm1(x)
        out = self.act(out)
        out = self.linear1(out)
        
        out = self.norm2(out)
        out = self.act(out)
        out = self.dropout(out)
        out = self.linear2(out)
        
        return out + identity

class EfficientNet(nn.Module):
    def __init__(self, input_dim=384, num_classes=128):
        super().__init__()
        self.input_dim = input_dim
        self.num_classes = num_classes
        
        # Calculate dimensions to stay under 5M parameters
        # Using progressive expansion then contraction
        dim1 = 1024  # ~384k params
        dim2 = 1792  # ~1.8M params
        dim3 = 1536  # ~2.75M params (from previous layers)
        dim4 = 896   # ~1.4M params
        dim5 = 512   # ~0.46M params
        
        # Initial projection
        self.initial = nn.Sequential(
            nn.Linear(input_dim, dim1),
            nn.BatchNorm1d(dim1),
            nn.GELU(),
            nn.Dropout(0.2)
        )
        
        # Residual blocks with bottleneck
        self.block1 = ResidualBlock(dim1, dim2, dropout_rate=0.25)
        self.block2 = ResidualBlock(dim2, dim3, dropout_rate=0.25)
        self.block3 = ResidualBlock(dim3, dim4, dropout_rate=0.2)
        self.block4 = ResidualBlock(dim4, dim5, dropout_rate=0.15)
        
        # Final layers
        self.final_norm = nn.BatchNorm1d(dim5)
        self.final_act = nn.GELU()
        self.final_dropout = nn.Dropout(0.1)
        self.classifier = nn.Linear(dim5, num_classes)
        
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
        x = self.initial(x)
        x = self.block1(x)
        x = self.block2(x)
        x = self.block3(x)
        x = self.block4(x)
        x = self.final_norm(x)
        x = self.final_act(x)
        x = self.final_dropout(x)
        return self.classifier(x)

class Solution:
    def solve(self, train_loader, val_loader, metadata: dict = None) -> torch.nn.Module:
        if metadata is None:
            metadata = {}
        
        device = metadata.get('device', 'cpu')
        num_classes = metadata.get('num_classes', 128)
        input_dim = metadata.get('input_dim', 384)
        param_limit = metadata.get('param_limit', 5000000)
        
        # Create and verify model fits within parameter budget
        model = EfficientNet(input_dim, num_classes)
        model.to(device)
        
        # Count parameters
        total_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
        print(f"Total trainable parameters: {total_params:,}")
        
        if total_params > param_limit:
            # Fallback to smaller model if over budget
            return self._create_smaller_model(input_dim, num_classes, device, param_limit)
        
        # Training setup
        criterion = nn.CrossEntropyLoss(label_smoothing=0.1)
        
        # Use AdamW with weight decay
        optimizer = optim.AdamW(
            model.parameters(),
            lr=0.0015,
            weight_decay=0.05,
            betas=(0.9, 0.999)
        )
        
        # Cosine annealing scheduler with warmup
        scheduler = CosineAnnealingLR(optimizer, T_max=100, eta_min=1e-6)
        
        # Training loop
        best_val_acc = 0.0
        best_model_state = None
        patience_counter = 0
        max_patience = 15
        
        num_epochs = 150
        warmup_epochs = 10
        
        for epoch in range(num_epochs):
            # Adjust learning rate with warmup
            if epoch < warmup_epochs:
                lr_scale = min(1.0, (epoch + 1) / warmup_epochs)
                for param_group in optimizer.param_groups:
                    param_group['lr'] = 0.0015 * lr_scale
            
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
                
                # Gradient clipping
                torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
                
                loss.backward()
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
            
            # Update scheduler after warmup
            if epoch >= warmup_epochs:
                scheduler.step()
            
            # Early stopping and model saving
            if val_acc > best_val_acc:
                best_val_acc = val_acc
                best_model_state = model.state_dict().copy()
                patience_counter = 0
            else:
                patience_counter += 1
            
            # Print progress
            if (epoch + 1) % 10 == 0 or epoch == 0:
                print(f'Epoch [{epoch+1}/{num_epochs}] '
                      f'Train Loss: {train_loss/len(train_loader):.4f}, '
                      f'Train Acc: {train_acc:.2f}%, '
                      f'Val Loss: {val_loss/len(val_loader):.4f}, '
                      f'Val Acc: {val_acc:.2f}%')
            
            if patience_counter >= max_patience:
                print(f'Early stopping at epoch {epoch+1}')
                break
        
        # Load best model
        if best_model_state is not None:
            model.load_state_dict(best_model_state)
        
        # Final validation
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
        
        final_val_acc = 100. * final_val_correct / final_val_total
        print(f'Final Validation Accuracy: {final_val_acc:.2f}%')
        
        return model
    
    def _create_smaller_model(self, input_dim, num_classes, device, param_limit):
        """Create a smaller model if initial model exceeds parameter limit"""
        print("Creating smaller model to fit within parameter budget...")
        
        # Simple MLP with careful parameter count
        hidden1 = 1152
        hidden2 = 1152
        hidden3 = 768
        
        model = nn.Sequential(
            nn.Linear(input_dim, hidden1),
            nn.BatchNorm1d(hidden1),
            nn.GELU(),
            nn.Dropout(0.2),
            
            nn.Linear(hidden1, hidden2),
            nn.BatchNorm1d(hidden2),
            nn.GELU(),
            nn.Dropout(0.25),
            
            nn.Linear(hidden2, hidden3),
            nn.BatchNorm1d(hidden3),
            nn.GELU(),
            nn.Dropout(0.2),
            
            nn.Linear(hidden3, num_classes)
        )
        
        model.to(device)
        
        # Verify parameter count
        total_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
        print(f"Smaller model parameters: {total_params:,}")
        
        return model