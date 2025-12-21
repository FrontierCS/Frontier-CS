import torch
import torch.nn as nn
import torch.optim as optim
from torch.optim.lr_scheduler import CosineAnnealingLR
import copy
import numpy as np

class EfficientMLP(nn.Module):
    def __init__(self, input_dim=384, num_classes=128):
        super().__init__()
        
        # Calculate dimensions to stay under 200K params
        # Using a bottleneck architecture with residual connections
        hidden1 = 512  # 384*512 + 512 = 197,120
        hidden2 = 256  # 512*256 + 256 = 131,328
        hidden3 = 192  # 256*192 + 192 = 49,344
        # Total before classifier: ~377,792 (too high)
        
        # Let's recalculate more carefully:
        # We need <= 200K total
        # Strategy: smaller hidden layers with residual connections
        hidden1 = 384  # Same as input for residual
        hidden2 = 384
        hidden3 = 384
        bottleneck = 256
        
        # Layer 1: 384*384 + 384 = 147,840
        # Layer 2: 384*384 + 384 = 147,840 (reuse for residual)
        # Layer 3: 384*256 + 256 = 98,560
        # Classifier: 256*128 + 128 = 32,896
        # Total: 147,840 + 98,560 + 32,896 = 279,296 (still too high)
        
        # Need to be more aggressive:
        hidden1 = 256
        hidden2 = 256
        hidden3 = 256
        bottleneck = 192
        
        # Layer 1: 384*256 + 256 = 98,560
        # Layer 2: 256*256 + 256 = 65,792 (residual)
        # Layer 3: 256*192 + 192 = 49,344
        # Classifier: 192*128 + 128 = 24,704
        # Total: 98,560 + 49,344 + 24,704 = 172,608 (good!)
        
        # Let's verify:
        # 98,560 + 65,792 + 49,344 + 24,704 = 238,400 (with residual)
        # Actually need to count residual projection too: 256->256 (65,792)
        # So total is 238,400 which is over 200K
        
        # Final design: no residual projection, just identity when dimensions match
        hidden1 = 256
        hidden2 = 256
        hidden3 = 192
        bottleneck = 192
        
        self.fc1 = nn.Linear(input_dim, hidden1)
        self.bn1 = nn.BatchNorm1d(hidden1)
        self.drop1 = nn.Dropout(0.3)
        
        self.fc2 = nn.Linear(hidden1, hidden2)
        self.bn2 = nn.BatchNorm1d(hidden2)
        self.drop2 = nn.Dropout(0.3)
        
        self.fc3 = nn.Linear(hidden2, hidden3)
        self.bn3 = nn.BatchNorm1d(hidden3)
        self.drop3 = nn.Dropout(0.2)
        
        self.fc4 = nn.Linear(hidden3, bottleneck)
        self.bn4 = nn.BatchNorm1d(bottleneck)
        
        self.classifier = nn.Linear(bottleneck, num_classes)
        
        # Activation
        self.act = nn.GELU()
        
        # Count parameters
        total_params = sum(p.numel() for p in self.parameters() if p.requires_grad)
        print(f"Model parameters: {total_params}")
        
    def forward(self, x):
        # Layer 1
        identity1 = x
        x = self.fc1(x)
        x = self.bn1(x)
        x = self.act(x)
        x = self.drop1(x)
        
        # Layer 2 with residual
        identity2 = x
        x = self.fc2(x)
        x = self.bn2(x)
        # Residual connection (dimensions match: 256->256)
        x = x + identity2
        x = self.act(x)
        x = self.drop2(x)
        
        # Layer 3
        x = self.fc3(x)
        x = self.bn3(x)
        x = self.act(x)
        x = self.drop3(x)
        
        # Bottleneck
        x = self.fc4(x)
        x = self.bn4(x)
        x = self.act(x)
        
        # Classifier
        x = self.classifier(x)
        return x

class Solution:
    def solve(self, train_loader, val_loader, metadata: dict = None) -> torch.nn.Module:
        device = metadata.get("device", "cpu")
        input_dim = metadata["input_dim"]
        num_classes = metadata["num_classes"]
        
        # Create model
        model = EfficientMLP(input_dim, num_classes)
        
        # Verify parameter count
        total_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
        print(f"Total trainable parameters: {total_params}")
        if total_params > 200000:
            # If somehow over budget, create simpler model
            model = nn.Sequential(
                nn.Linear(input_dim, 256),
                nn.BatchNorm1d(256),
                nn.GELU(),
                nn.Dropout(0.3),
                nn.Linear(256, 192),
                nn.BatchNorm1d(192),
                nn.GELU(),
                nn.Dropout(0.2),
                nn.Linear(192, num_classes)
            )
            total_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
            print(f"Fallback model parameters: {total_params}")
        
        model = model.to(device)
        
        # Training setup
        criterion = nn.CrossEntropyLoss()
        optimizer = optim.AdamW(model.parameters(), lr=0.001, weight_decay=1e-4)
        scheduler = CosineAnnealingLR(optimizer, T_max=50, eta_min=1e-5)
        
        # Early stopping
        best_val_acc = 0
        best_model_state = None
        patience = 15
        patience_counter = 0
        
        num_epochs = 100
        
        for epoch in range(num_epochs):
            # Training
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
            
            # Validation
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
            
            # Update scheduler
            scheduler.step()
            
            # Early stopping
            if val_acc > best_val_acc:
                best_val_acc = val_acc
                best_model_state = copy.deepcopy(model.state_dict())
                patience_counter = 0
            else:
                patience_counter += 1
            
            if patience_counter >= patience:
                print(f"Early stopping at epoch {epoch+1}")
                break
            
            if (epoch + 1) % 10 == 0:
                print(f"Epoch {epoch+1}/{num_epochs}: "
                      f"Train Loss: {train_loss/(batch_idx+1):.4f}, "
                      f"Train Acc: {train_acc:.2f}%, "
                      f"Val Acc: {val_acc:.2f}%, "
                      f"Best Val Acc: {best_val_acc:.2f}%")
        
        # Load best model
        if best_model_state is not None:
            model.load_state_dict(best_model_state)
        
        # Final validation check
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
        
        final_val_acc = 100. * val_correct / val_total
        print(f"Final validation accuracy: {final_val_acc:.2f}%")
        
        return model
