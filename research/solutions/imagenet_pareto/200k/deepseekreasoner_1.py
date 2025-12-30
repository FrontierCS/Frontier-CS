import torch
import torch.nn as nn
import torch.optim as optim
from torch.optim.lr_scheduler import CosineAnnealingLR
import copy
import warnings

class Solution:
    def solve(self, train_loader, val_loader, metadata: dict = None) -> torch.nn.Module:
        # Extract metadata
        num_classes = metadata["num_classes"]
        input_dim = metadata["input_dim"]
        device = metadata["device"]
        param_limit = metadata["param_limit"]
        
        # Define model architecture with batch norm and residual connections
        class EfficientNet(nn.Module):
            def __init__(self, input_dim=384, num_classes=128):
                super().__init__()
                
                # Main network - carefully balanced for 200K params
                self.features = nn.Sequential(
                    # Layer 1: input expansion
                    nn.Linear(input_dim, 384),
                    nn.BatchNorm1d(384),
                    nn.ReLU(inplace=True),
                    nn.Dropout(0.2),
                    
                    # Layer 2: depthwise with residual
                    self._make_layer(384, 384, downsample=False),
                    
                    # Layer 3: reduction
                    self._make_layer(384, 256, downsample=True),
                    
                    # Layer 4: mid-level features
                    self._make_layer(256, 256, downsample=False),
                    
                    # Layer 5: further reduction
                    self._make_layer(256, 192, downsample=True),
                    
                    # Layer 6: final features
                    self._make_layer(192, 192, downsample=False),
                )
                
                # Classifier with bottleneck
                self.classifier = nn.Sequential(
                    nn.Dropout(0.3),
                    nn.Linear(192, 256),
                    nn.BatchNorm1d(256),
                    nn.ReLU(inplace=True),
                    nn.Dropout(0.2),
                    nn.Linear(256, num_classes)
                )
                
                # Initialize weights
                self._initialize_weights()
                
            def _make_layer(self, in_dim, out_dim, downsample=False):
                layers = []
                if downsample:
                    layers.append(nn.Linear(in_dim, out_dim))
                else:
                    # Depthwise-like operation for efficiency
                    layers.append(nn.Linear(in_dim, in_dim))
                    layers.append(nn.BatchNorm1d(in_dim))
                    layers.append(nn.ReLU(inplace=True))
                    layers.append(nn.Dropout(0.1))
                    layers.append(nn.Linear(in_dim, out_dim))
                
                layers.append(nn.BatchNorm1d(out_dim))
                layers.append(nn.ReLU(inplace=True))
                return nn.Sequential(*layers)
            
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
                x = self.features(x)
                x = self.classifier(x)
                return x
        
        # Create model
        model = EfficientNet(input_dim, num_classes).to(device)
        
        # Verify parameter count
        total_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
        if total_params > param_limit:
            # If over limit, create simpler model
            warnings.warn(f"Model has {total_params} parameters, exceeding {param_limit}. Creating simpler model.")
            model = nn.Sequential(
                nn.Linear(input_dim, 384),
                nn.BatchNorm1d(384),
                nn.ReLU(),
                nn.Dropout(0.3),
                nn.Linear(384, 256),
                nn.BatchNorm1d(256),
                nn.ReLU(),
                nn.Dropout(0.3),
                nn.Linear(256, num_classes)
            ).to(device)
        
        # Final parameter check
        total_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
        if total_params > param_limit:
            raise ValueError(f"Model exceeds parameter limit: {total_params} > {param_limit}")
        
        # Training setup
        criterion = nn.CrossEntropyLoss(label_smoothing=0.1)
        optimizer = optim.AdamW(model.parameters(), lr=0.001, weight_decay=1e-4)
        scheduler = CosineAnnealingLR(optimizer, T_max=30, eta_min=1e-6)
        
        # Early stopping
        best_val_acc = 0.0
        best_model_state = None
        patience_counter = 0
        max_patience = 15
        
        # Training loop
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
                torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
                
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
            
            val_acc = 100.0 * val_correct / val_total
            
            # Update scheduler
            scheduler.step()
            
            # Early stopping and model checkpointing
            if val_acc > best_val_acc:
                best_val_acc = val_acc
                best_model_state = copy.deepcopy(model.state_dict())
                patience_counter = 0
            else:
                patience_counter += 1
            
            # Break if no improvement for too long
            if patience_counter >= max_patience:
                break
        
        # Load best model
        if best_model_state is not None:
            model.load_state_dict(best_model_state)
        
        return model