import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim
from torch.optim.lr_scheduler import ReduceLROnPlateau
import numpy as np
from tqdm import tqdm
import copy
import math

class ResidualBlock(nn.Module):
    def __init__(self, in_dim, out_dim, bottleneck_ratio=4, dropout=0.2):
        super().__init__()
        self.in_dim = in_dim
        self.out_dim = out_dim
        
        bottleneck_dim = max(out_dim // bottleneck_ratio, 32)
        
        self.conv = nn.Sequential(
            nn.Linear(in_dim, bottleneck_dim, bias=False),
            nn.BatchNorm1d(bottleneck_dim),
            nn.ReLU(inplace=True),
            nn.Dropout(dropout),
            nn.Linear(bottleneck_dim, out_dim, bias=False),
            nn.BatchNorm1d(out_dim)
        )
        
        self.skip = nn.Linear(in_dim, out_dim, bias=False) if in_dim != out_dim else nn.Identity()
        self.relu = nn.ReLU(inplace=True)
        
    def forward(self, x):
        identity = self.skip(x)
        out = self.conv(x)
        out += identity
        return self.relu(out)

class EfficientNet(nn.Module):
    def __init__(self, input_dim=384, num_classes=128, width_mult=1.0, depth_mult=1.0):
        super().__init__()
        
        # Calculate dimensions based on multipliers
        base_width = 512
        base_depth = 4
        
        width = int(base_width * width_mult)
        depth = int(base_depth * depth_mult)
        
        # Ensure minimum dimensions
        width = max(width, 256)
        depth = max(depth, 2)
        
        self.stem = nn.Sequential(
            nn.Linear(input_dim, width // 2),
            nn.BatchNorm1d(width // 2),
            nn.ReLU(inplace=True),
            nn.Dropout(0.2)
        )
        
        # Build residual blocks
        layers = []
        current_dim = width // 2
        
        for i in range(depth):
            if i == depth - 1:
                next_dim = width
            else:
                next_dim = min(current_dim * 2, width) if i % 2 == 0 else current_dim
                
            layers.append(ResidualBlock(current_dim, next_dim, 
                                       bottleneck_ratio=4 if i < depth//2 else 2,
                                       dropout=0.2 if i < depth-2 else 0.1))
            current_dim = next_dim
        
        self.blocks = nn.Sequential(*layers)
        
        # Final layers
        self.final = nn.Sequential(
            nn.Linear(current_dim, width // 2),
            nn.BatchNorm1d(width // 2),
            nn.ReLU(inplace=True),
            nn.Dropout(0.1),
            nn.Linear(width // 2, num_classes)
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
        x = self.stem(x)
        x = self.blocks(x)
        x = self.final(x)
        return x

class Solution:
    def solve(self, train_loader, val_loader, metadata: dict = None) -> torch.nn.Module:
        device = torch.device(metadata.get("device", "cpu"))
        num_classes = metadata["num_classes"]
        input_dim = metadata["input_dim"]
        param_limit = metadata["param_limit"]
        
        # Hyperparameter search space for architecture
        width_multipliers = [1.0, 1.1, 1.2]
        depth_multipliers = [1.0, 1.1, 1.2]
        
        best_model = None
        best_val_acc = 0.0
        
        # Try different architectures within parameter budget
        for w_mult in width_multipliers:
            for d_mult in depth_multipliers:
                model = EfficientNet(
                    input_dim=input_dim,
                    num_classes=num_classes,
                    width_mult=w_mult,
                    depth_mult=d_mult
                ).to(device)
                
                # Check parameter count
                param_count = sum(p.numel() for p in model.parameters() if p.requires_grad)
                if param_count > param_limit:
                    continue
                
                # Train this configuration
                val_acc = self._train_model(
                    model, train_loader, val_loader, device, 
                    param_count, param_limit
                )
                
                if val_acc > best_val_acc:
                    best_val_acc = val_acc
                    best_model = copy.deepcopy(model)
        
        # If no model was found (all exceeded limit), use conservative model
        if best_model is None:
            best_model = EfficientNet(
                input_dim=input_dim,
                num_classes=num_classes,
                width_mult=0.9,
                depth_mult=0.9
            ).to(device)
            
            # Final training with best found configuration
            self._train_model(
                best_model, train_loader, val_loader, device,
                sum(p.numel() for p in best_model.parameters() if p.requires_grad),
                param_limit
            )
        
        return best_model
    
    def _train_model(self, model, train_loader, val_loader, device, param_count, param_limit):
        if param_count > param_limit:
            return 0.0
        
        # Training hyperparameters
        epochs = 200
        lr = 0.001
        weight_decay = 1e-4
        
        optimizer = optim.AdamW(model.parameters(), lr=lr, weight_decay=weight_decay)
        scheduler = ReduceLROnPlateau(optimizer, mode='max', factor=0.5, patience=10, verbose=False)
        criterion = nn.CrossEntropyLoss()
        
        # MixUp augmentation
        def mixup_data(x, y, alpha=0.2):
            if alpha > 0:
                lam = np.random.beta(alpha, alpha)
            else:
                lam = 1
            
            batch_size = x.size()[0]
            index = torch.randperm(batch_size).to(device)
            
            mixed_x = lam * x + (1 - lam) * x[index]
            y_a, y_b = y, y[index]
            return mixed_x, y_a, y_b, lam
        
        def mixup_criterion(criterion, pred, y_a, y_b, lam):
            return lam * criterion(pred, y_a) + (1 - lam) * criterion(pred, y_b)
        
        best_val_acc = 0.0
        patience_counter = 0
        max_patience = 30
        
        for epoch in range(epochs):
            # Training phase
            model.train()
            train_loss = 0.0
            correct = 0
            total = 0
            
            pbar = tqdm(train_loader, desc=f'Epoch {epoch+1}/{epochs}', leave=False)
            for batch_idx, (inputs, targets) in enumerate(pbar):
                inputs, targets = inputs.to(device), targets.to(device)
                
                # Apply MixUp
                inputs, targets_a, targets_b, lam = mixup_data(inputs, targets, alpha=0.2)
                
                optimizer.zero_grad()
                outputs = model(inputs)
                loss = mixup_criterion(criterion, outputs, targets_a, targets_b, lam)
                loss.backward()
                
                # Gradient clipping
                torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
                
                optimizer.step()
                
                train_loss += loss.item()
                _, predicted = outputs.max(1)
                total += targets.size(0)
                correct += (lam * predicted.eq(targets_a).sum().item() + 
                           (1 - lam) * predicted.eq(targets_b).sum().item())
                
                pbar.set_postfix({'loss': train_loss/(batch_idx+1), 'acc': 100.*correct/total})
            
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
            
            # Update learning rate
            scheduler.step(val_acc)
            
            # Early stopping
            if val_acc > best_val_acc:
                best_val_acc = val_acc
                patience_counter = 0
            else:
                patience_counter += 1
            
            if patience_counter >= max_patience:
                break
        
        return best_val_acc