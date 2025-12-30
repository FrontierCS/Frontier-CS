import torch
import torch.nn as nn
import torch.optim as optim
from torch.optim.lr_scheduler import CosineAnnealingLR, ReduceLROnPlateau
import time
import numpy as np
from collections import OrderedDict

class ResidualBlock(nn.Module):
    def __init__(self, in_features, out_features, dropout_rate=0.2):
        super(ResidualBlock, self).__init__()
        self.in_features = in_features
        self.out_features = out_features
        
        self.norm1 = nn.BatchNorm1d(in_features)
        self.linear1 = nn.Linear(in_features, out_features)
        self.norm2 = nn.BatchNorm1d(out_features)
        self.linear2 = nn.Linear(out_features, out_features)
        self.activation = nn.GELU()
        self.dropout = nn.Dropout(dropout_rate)
        
        if in_features != out_features:
            self.shortcut = nn.Linear(in_features, out_features)
        else:
            self.shortcut = nn.Identity()
            
    def forward(self, x):
        identity = self.shortcut(x)
        
        out = self.norm1(x)
        out = self.activation(out)
        out = self.linear1(out)
        
        out = self.norm2(out)
        out = self.activation(out)
        out = self.linear2(out)
        out = self.dropout(out)
        
        out = out + identity
        return out

class EfficientMLP(nn.Module):
    def __init__(self, input_dim=384, num_classes=128, hidden_dims=None, dropout_rate=0.2):
        super(EfficientMLP, self).__init__()
        
        if hidden_dims is None:
            hidden_dims = [768, 1024, 768, 512]
        
        layers = OrderedDict()
        
        # Input layer
        layers['input_norm'] = nn.BatchNorm1d(input_dim)
        layers['input_linear'] = nn.Linear(input_dim, hidden_dims[0])
        layers['input_activation'] = nn.GELU()
        layers['input_dropout'] = nn.Dropout(dropout_rate)
        
        # Hidden layers with residual connections
        for i in range(len(hidden_dims) - 1):
            layers[f'res_block_{i}'] = ResidualBlock(
                hidden_dims[i], 
                hidden_dims[i + 1], 
                dropout_rate
            )
        
        # Final layers
        layers['final_norm'] = nn.BatchNorm1d(hidden_dims[-1])
        layers['final_activation'] = nn.GELU()
        layers['final_dropout'] = nn.Dropout(dropout_rate * 0.5)
        layers['output'] = nn.Linear(hidden_dims[-1], num_classes)
        
        self.model = nn.Sequential(layers)
        
    def forward(self, x):
        return self.model(x)

class Solution:
    def solve(self, train_loader, val_loader, metadata: dict = None):
        if metadata is None:
            metadata = {}
        
        device = metadata.get("device", "cpu")
        input_dim = metadata.get("input_dim", 384)
        num_classes = metadata.get("num_classes", 128)
        param_limit = metadata.get("param_limit", 5000000)
        
        # Adjust architecture based on parameter budget
        hidden_dims = self._optimize_architecture(input_dim, num_classes, param_limit)
        
        model = EfficientMLP(
            input_dim=input_dim,
            num_classes=num_classes,
            hidden_dims=hidden_dims,
            dropout_rate=0.25
        ).to(device)
        
        # Verify parameter count
        total_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
        print(f"Total trainable parameters: {total_params:,}")
        
        if total_params > param_limit:
            # Reduce hidden dimensions proportionally
            scale = (param_limit / total_params) ** 0.5
            hidden_dims = [int(d * scale) for d in hidden_dims]
            model = EfficientMLP(
                input_dim=input_dim,
                num_classes=num_classes,
                hidden_dims=hidden_dims,
                dropout_rate=0.25
            ).to(device)
            total_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
            print(f"Adjusted parameters: {total_params:,}")
        
        # Training configuration
        criterion = nn.CrossEntropyLoss(label_smoothing=0.1)
        optimizer = optim.AdamW(
            model.parameters(),
            lr=0.001,
            weight_decay=0.05,
            betas=(0.9, 0.999)
        )
        
        # Multi-step scheduler with warmup
        warmup_epochs = 5
        total_epochs = 200
        scheduler = CosineAnnealingLR(optimizer, T_max=total_epochs - warmup_epochs)
        
        # Early stopping
        best_val_acc = 0
        best_model_state = None
        patience = 15
        patience_counter = 0
        
        # Mixed precision training (CPU-friendly)
        scaler = torch.cuda.amp.GradScaler(enabled=False)  # Disabled for CPU
        
        # Training loop
        for epoch in range(total_epochs):
            # Warmup phase
            if epoch < warmup_epochs:
                lr_scale = min(1.0, (epoch + 1) / warmup_epochs)
                for param_group in optimizer.param_groups:
                    param_group['lr'] = 0.001 * lr_scale
            
            # Training
            model.train()
            train_loss = 0
            train_correct = 0
            train_total = 0
            
            for batch_idx, (inputs, targets) in enumerate(train_loader):
                inputs, targets = inputs.to(device), targets.to(device)
                
                optimizer.zero_grad()
                
                with torch.cuda.amp.autocast(enabled=False):
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
            
            # Validation
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
            
            # Update scheduler after warmup
            if epoch >= warmup_epochs:
                scheduler.step()
            
            # Early stopping check
            if val_acc > best_val_acc:
                best_val_acc = val_acc
                best_model_state = model.state_dict().copy()
                patience_counter = 0
            else:
                patience_counter += 1
            
            # Print progress
            if (epoch + 1) % 10 == 0:
                print(f'Epoch: {epoch+1:03d} | '
                      f'Train Loss: {train_loss/len(train_loader):.4f} | '
                      f'Train Acc: {train_acc:.2f}% | '
                      f'Val Loss: {val_loss/len(val_loader):.4f} | '
                      f'Val Acc: {val_acc:.2f}% | '
                      f'LR: {optimizer.param_groups[0]["lr"]:.6f}')
            
            if patience_counter >= patience:
                print(f'Early stopping triggered at epoch {epoch+1}')
                break
        
        # Load best model
        if best_model_state is not None:
            model.load_state_dict(best_model_state)
        
        return model
    
    def _optimize_architecture(self, input_dim, num_classes, param_limit):
        # Calculate optimal hidden dimensions within parameter budget
        # Using a pyramid structure: wider in middle, narrower at ends
        base_width = 1024
        middle_width = 1280
        
        # Try to allocate ~4.8M parameters to be safe
        target_params = param_limit * 0.96
        
        # Calculate available parameters for hidden layers
        # Subtract input and output layer parameters
        input_output_params = (
            input_dim * base_width + base_width +  # Input layer
            base_width * num_classes + num_classes  # Output layer (worst case)
        )
        
        hidden_params_budget = target_params - input_output_params
        
        # Estimate parameters per residual block
        # Each block has 2 linear layers + batchnorm
        block_params_estimate = 2 * (base_width * base_width + base_width) + 4 * base_width
        
        # Calculate number of blocks we can afford
        n_blocks = max(2, int(hidden_params_budget / block_params_estimate))
        n_blocks = min(n_blocks, 6)  # Limit depth
        
        # Create pyramid structure
        if n_blocks >= 4:
            # 4 or more blocks: narrow -> wide -> wide -> narrow
            return [base_width, middle_width, middle_width, base_width]
        elif n_blocks == 3:
            # 3 blocks: narrow -> wide -> narrow
            return [base_width, middle_width, base_width]
        else:
            # 2 blocks: moderate width throughout
            return [base_width, base_width]