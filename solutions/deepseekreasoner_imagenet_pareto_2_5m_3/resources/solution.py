import torch
import torch.nn as nn
import torch.optim as optim
from torch.optim.lr_scheduler import CosineAnnealingLR
import copy

class Solution:
    def solve(self, train_loader, val_loader, metadata: dict = None) -> torch.nn.Module:
        input_dim = metadata["input_dim"]
        num_classes = metadata["num_classes"]
        device = metadata.get("device", "cpu")
        
        # Create a model that stays well under 2.5M parameters
        # Using a deeper but narrower architecture with residual connections
        class ResidualBlock(nn.Module):
            def __init__(self, in_features, out_features, dropout_rate=0.2):
                super().__init__()
                self.linear1 = nn.Linear(in_features, out_features)
                self.bn1 = nn.BatchNorm1d(out_features)
                self.linear2 = nn.Linear(out_features, out_features)
                self.bn2 = nn.BatchNorm1d(out_features)
                self.dropout = nn.Dropout(dropout_rate)
                self.relu = nn.ReLU()
                self.shortcut = nn.Linear(in_features, out_features) if in_features != out_features else nn.Identity()
                
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
                # Feature extractor with residual blocks
                self.initial = nn.Sequential(
                    nn.Linear(input_dim, 768),
                    nn.BatchNorm1d(768),
                    nn.ReLU(),
                    nn.Dropout(0.2)
                )
                
                # Residual blocks with bottleneck design
                self.block1 = ResidualBlock(768, 768, 0.3)
                self.block2 = ResidualBlock(768, 512, 0.3)
                self.block3 = ResidualBlock(512, 384, 0.3)
                self.block4 = ResidualBlock(384, 256, 0.3)
                
                # Classifier head
                self.classifier = nn.Sequential(
                    nn.Linear(256, 256),
                    nn.BatchNorm1d(256),
                    nn.ReLU(),
                    nn.Dropout(0.2),
                    nn.Linear(256, num_classes)
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
                x = self.initial(x)
                x = self.block1(x)
                x = self.block2(x)
                x = self.block3(x)
                x = self.block4(x)
                return self.classifier(x)
        
        # Create and verify model size
        model = EfficientNet(input_dim, num_classes)
        model.to(device)
        
        # Count parameters
        total_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
        print(f"Total trainable parameters: {total_params:,}")
        
        # Training setup
        criterion = nn.CrossEntropyLoss(label_smoothing=0.1)
        optimizer = optim.AdamW(model.parameters(), lr=0.001, weight_decay=0.05)
        scheduler = CosineAnnealingLR(optimizer, T_max=100)
        
        # Training loop with early stopping
        best_val_acc = 0.0
        best_model_state = None
        patience = 20
        patience_counter = 0
        epochs = 150
        
        for epoch in range(epochs):
            # Training phase
            model.train()
            train_loss = 0.0
            train_correct = 0
            train_total = 0
            
            for inputs, targets in train_loader:
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
            
            val_acc = 100. * val_correct / val_total
            
            # Update scheduler
            scheduler.step()
            
            # Early stopping check
            if val_acc > best_val_acc:
                best_val_acc = val_acc
                best_model_state = copy.deepcopy(model.state_dict())
                patience_counter = 0
            else:
                patience_counter += 1
            
            # Print progress
            if (epoch + 1) % 10 == 0:
                print(f"Epoch {epoch+1}/{epochs}, "
                      f"Train Loss: {train_loss/len(train_loader):.4f}, "
                      f"Train Acc: {100.*train_correct/train_total:.2f}%, "
                      f"Val Acc: {val_acc:.2f}%, "
                      f"LR: {scheduler.get_last_lr()[0]:.6f}")
            
            if patience_counter >= patience:
                print(f"Early stopping at epoch {epoch+1}")
                break
        
        # Load best model
        if best_model_state is not None:
            model.load_state_dict(best_model_state)
        
        print(f"Best validation accuracy: {best_val_acc:.2f}%")
        
        return model
