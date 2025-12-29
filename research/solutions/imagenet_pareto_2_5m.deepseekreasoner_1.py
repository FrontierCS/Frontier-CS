import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.optim import AdamW
from torch.optim.lr_scheduler import CosineAnnealingLR
import math

class ResidualBlock(nn.Module):
    def __init__(self, in_dim, out_dim, dropout_rate=0.2):
        super().__init__()
        self.norm1 = nn.BatchNorm1d(in_dim)
        self.linear1 = nn.Linear(in_dim, out_dim)
        self.norm2 = nn.BatchNorm1d(out_dim)
        self.linear2 = nn.Linear(out_dim, out_dim)
        self.dropout = nn.Dropout(dropout_rate)
        self.residual = nn.Linear(in_dim, out_dim) if in_dim != out_dim else nn.Identity()
        
    def forward(self, x):
        residual = self.residual(x)
        x = self.norm1(x)
        x = F.relu(x)
        x = self.linear1(x)
        x = self.norm2(x)
        x = F.relu(x)
        x = self.dropout(x)
        x = self.linear2(x)
        return x + residual

class EfficientNet(nn.Module):
    def __init__(self, input_dim, num_classes, param_limit=2500000):
        super().__init__()
        # Calculate dimensions to stay under parameter limit
        # Use bottleneck architecture with expansion factor
        hidden1 = 1024
        hidden2 = 768
        hidden3 = 512
        hidden4 = 384
        
        self.input_proj = nn.Linear(input_dim, hidden1)
        self.norm0 = nn.BatchNorm1d(hidden1)
        
        # Residual blocks with bottleneck
        self.block1 = ResidualBlock(hidden1, hidden2)
        self.block2 = ResidualBlock(hidden2, hidden3)
        self.block3 = ResidualBlock(hidden3, hidden4)
        
        # Final layers
        self.norm_final = nn.BatchNorm1d(hidden4)
        self.fc1 = nn.Linear(hidden4, 256)
        self.norm_fc = nn.BatchNorm1d(256)
        self.fc2 = nn.Linear(256, num_classes)
        
        self.dropout = nn.Dropout(0.3)
        
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
        x = self.norm0(x)
        x = F.relu(x)
        x = self.dropout(x)
        
        x = self.block1(x)
        x = self.block2(x)
        x = self.block3(x)
        
        x = self.norm_final(x)
        x = F.relu(x)
        x = self.dropout(x)
        
        x = self.fc1(x)
        x = self.norm_fc(x)
        x = F.relu(x)
        x = self.dropout(x)
        
        x = self.fc2(x)
        return x

class Solution:
    def solve(self, train_loader, val_loader, metadata: dict = None) -> torch.nn.Module:
        if metadata is None:
            metadata = {}
            
        input_dim = metadata.get("input_dim", 384)
        num_classes = metadata.get("num_classes", 128)
        param_limit = metadata.get("param_limit", 2500000)
        device = metadata.get("device", "cpu")
        baseline_accuracy = metadata.get("baseline_accuracy", 0.85)
        
        # Build model
        model = EfficientNet(input_dim, num_classes, param_limit)
        model.to(device)
        
        # Verify parameter count
        total_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
        print(f"Total trainable parameters: {total_params:,}")
        if total_params > param_limit:
            # If model is too large, create a smaller version
            print("Model too large, creating smaller version")
            model = self._create_smaller_model(input_dim, num_classes, param_limit)
            model.to(device)
            total_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
            print(f"New model parameters: {total_params:,}")
        
        # Training setup
        criterion = nn.CrossEntropyLoss()
        optimizer = AdamW(model.parameters(), lr=0.001, weight_decay=1e-4)
        scheduler = CosineAnnealingLR(optimizer, T_max=50, eta_min=1e-5)
        
        # Training loop
        best_val_acc = 0.0
        best_model_state = None
        patience = 10
        patience_counter = 0
        
        num_epochs = 100
        
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
            train_loss = train_loss / len(train_loader)
            
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
            val_loss = val_loss / len(val_loader)
            
            # Update scheduler
            scheduler.step()
            
            # Save best model
            if val_acc > best_val_acc:
                best_val_acc = val_acc
                best_model_state = model.state_dict().copy()
                patience_counter = 0
            else:
                patience_counter += 1
            
            # Early stopping
            if patience_counter >= patience:
                print(f"Early stopping at epoch {epoch+1}")
                break
            
            if (epoch + 1) % 10 == 0:
                print(f"Epoch [{epoch+1}/{num_epochs}], "
                      f"Train Loss: {train_loss:.4f}, Train Acc: {train_acc:.2f}%, "
                      f"Val Loss: {val_loss:.4f}, Val Acc: {val_acc:.2f}%")
        
        # Load best model
        if best_model_state is not None:
            model.load_state_dict(best_model_state)
        
        print(f"Best validation accuracy: {best_val_acc:.2f}%")
        return model
    
    def _create_smaller_model(self, input_dim, num_classes, param_limit):
        """Create a smaller model if the initial one exceeds parameter limit"""
        # Simple but effective architecture within budget
        class SmallNet(nn.Module):
            def __init__(self, input_dim, num_classes):
                super().__init__()
                self.net = nn.Sequential(
                    nn.Linear(input_dim, 768),
                    nn.BatchNorm1d(768),
                    nn.ReLU(),
                    nn.Dropout(0.3),
                    
                    nn.Linear(768, 512),
                    nn.BatchNorm1d(512),
                    nn.ReLU(),
                    nn.Dropout(0.3),
                    
                    nn.Linear(512, 384),
                    nn.BatchNorm1d(384),
                    nn.ReLU(),
                    nn.Dropout(0.3),
                    
                    nn.Linear(384, 256),
                    nn.BatchNorm1d(256),
                    nn.ReLU(),
                    nn.Dropout(0.2),
                    
                    nn.Linear(256, num_classes)
                )
                
            def forward(self, x):
                return self.net(x)
        
        return SmallNet(input_dim, num_classes)