import torch
import torch.nn as nn
import torch.optim as optim
from torch.optim.lr_scheduler import CosineAnnealingLR, ReduceLROnPlateau
import math
from collections import OrderedDict

class ResidualBlock(nn.Module):
    def __init__(self, in_dim, out_dim, dropout_rate=0.3):
        super().__init__()
        self.linear1 = nn.Linear(in_dim, out_dim)
        self.bn1 = nn.BatchNorm1d(out_dim)
        self.relu = nn.ReLU()
        self.dropout = nn.Dropout(dropout_rate)
        self.linear2 = nn.Linear(out_dim, out_dim)
        self.bn2 = nn.BatchNorm1d(out_dim)
        
        self.shortcut = nn.Linear(in_dim, out_dim) if in_dim != out_dim else nn.Identity()
        
    def forward(self, x):
        identity = self.shortcut(x)
        out = self.linear1(x)
        out = self.bn1(out)
        out = self.relu(out)
        out = self.dropout(out)
        out = self.linear2(out)
        out = self.bn2(out)
        out += identity
        out = self.relu(out)
        return out

class EfficientNet(nn.Module):
    def __init__(self, input_dim=384, num_classes=128, dropout_rate=0.3):
        super().__init__()
        
        # Calculate dimensions to stay under 1M params
        # Using expanding then compressing architecture
        hidden1 = 768  # 2x expansion
        hidden2 = 512
        hidden3 = 384
        hidden4 = 256
        
        self.features = nn.Sequential(OrderedDict([
            ('input_norm', nn.BatchNorm1d(input_dim)),
            ('fc1', nn.Linear(input_dim, hidden1)),
            ('bn1', nn.BatchNorm1d(hidden1)),
            ('relu1', nn.ReLU()),
            ('dropout1', nn.Dropout(dropout_rate)),
            
            ('res1', ResidualBlock(hidden1, hidden2, dropout_rate)),
            ('res2', ResidualBlock(hidden2, hidden2, dropout_rate)),
            
            ('fc2', nn.Linear(hidden2, hidden3)),
            ('bn2', nn.BatchNorm1d(hidden3)),
            ('relu2', nn.ReLU()),
            ('dropout2', nn.Dropout(dropout_rate)),
            
            ('res3', ResidualBlock(hidden3, hidden4, dropout_rate)),
            ('res4', ResidualBlock(hidden4, hidden4, dropout_rate)),
            
            ('final_pool', nn.AdaptiveAvgPool1d(1)),
        ]))
        
        self.classifier = nn.Sequential(
            nn.Linear(hidden4, hidden3),
            nn.BatchNorm1d(hidden3),
            nn.ReLU(),
            nn.Dropout(dropout_rate),
            nn.Linear(hidden3, num_classes)
        )
        
    def forward(self, x):
        x = self.features(x)
        x = x.squeeze(-1)
        return self.classifier(x)

class Solution:
    def solve(self, train_loader, val_loader, metadata: dict = None):
        device = torch.device(metadata.get("device", "cpu"))
        input_dim = metadata["input_dim"]
        num_classes = metadata["num_classes"]
        
        # Create model with parameter budget constraint
        model = EfficientNet(input_dim, num_classes).to(device)
        
        # Verify parameter count
        total_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
        print(f"Total parameters: {total_params:,}")
        
        # Training configuration
        criterion = nn.CrossEntropyLoss(label_smoothing=0.1)
        optimizer = optim.AdamW(model.parameters(), lr=0.001, weight_decay=0.01)
        scheduler = CosineAnnealingLR(optimizer, T_max=100)
        
        # Training loop
        best_val_acc = 0
        best_model_state = None
        patience = 20
        patience_counter = 0
        
        epochs = 200
        for epoch in range(epochs):
            # Training phase
            model.train()
            train_loss = 0
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
            val_loss = 0
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
            
            # Learning rate scheduling
            scheduler.step()
            
            # Early stopping with patience
            if val_acc > best_val_acc:
                best_val_acc = val_acc
                best_model_state = model.state_dict().copy()
                patience_counter = 0
            else:
                patience_counter += 1
            
            if patience_counter >= patience:
                print(f"Early stopping at epoch {epoch}")
                break
            
            if (epoch + 1) % 10 == 0:
                print(f'Epoch: {epoch+1:03d} | '
                      f'Train Loss: {train_loss/len(train_loader):.4f} | '
                      f'Train Acc: {train_acc:.2f}% | '
                      f'Val Loss: {val_loss:.4f} | '
                      f'Val Acc: {val_acc:.2f}%')
        
        # Load best model
        model.load_state_dict(best_model_state)
        model.eval()
        
        return model