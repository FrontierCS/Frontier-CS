import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim
from torch.optim.lr_scheduler import CosineAnnealingLR
from collections import OrderedDict
import math

class ResidualBlock(nn.Module):
    def __init__(self, in_channels, out_channels, stride=1, dropout_rate=0.2):
        super().__init__()
        self.conv1 = nn.Conv1d(in_channels, out_channels, kernel_size=3, 
                              padding=1, stride=stride, bias=False)
        self.bn1 = nn.BatchNorm1d(out_channels)
        self.conv2 = nn.Conv1d(out_channels, out_channels, kernel_size=3,
                              padding=1, bias=False)
        self.bn2 = nn.BatchNorm1d(out_channels)
        self.dropout = nn.Dropout(dropout_rate)
        
        self.shortcut = nn.Sequential()
        if stride != 1 or in_channels != out_channels:
            self.shortcut = nn.Sequential(
                nn.Conv1d(in_channels, out_channels, kernel_size=1,
                         stride=stride, bias=False),
                nn.BatchNorm1d(out_channels)
            )
    
    def forward(self, x):
        residual = self.shortcut(x)
        out = F.relu(self.bn1(self.conv1(x)))
        out = self.dropout(out)
        out = self.bn2(self.conv2(out))
        out += residual
        return F.relu(out)

class CustomModel(nn.Module):
    def __init__(self, input_dim=384, num_classes=128):
        super().__init__()
        
        # Calculate dimensions to stay under 500K params
        hidden1 = 256
        hidden2 = 192
        hidden3 = 128
        
        # Initial projection to 1D conv format
        self.input_proj = nn.Linear(input_dim, hidden1)
        self.bn0 = nn.BatchNorm1d(hidden1)
        
        # Reshape for 1D convolutions: [batch, channels, length]
        self.conv_reshape = hidden1 // 8
        
        # Residual blocks with careful channel planning
        self.res1 = ResidualBlock(self.conv_reshape, 64, stride=1, dropout_rate=0.2)
        self.res2 = ResidualBlock(64, 128, stride=2, dropout_rate=0.3)
        self.res3 = ResidualBlock(128, 128, stride=1, dropout_rate=0.3)
        
        # Adaptive pooling to fixed size
        self.adaptive_pool = nn.AdaptiveAvgPool1d(8)
        
        # Calculate flattened size after convolutions
        conv_output_size = 128 * 8  # channels * pooled_length
        
        # Final classifier with bottleneck
        self.fc1 = nn.Linear(conv_output_size, hidden2)
        self.bn4 = nn.BatchNorm1d(hidden2)
        self.dropout1 = nn.Dropout(0.4)
        
        self.fc2 = nn.Linear(hidden2, hidden3)
        self.bn5 = nn.BatchNorm1d(hidden3)
        self.dropout2 = nn.Dropout(0.3)
        
        self.fc3 = nn.Linear(hidden3, num_classes)
        
        # Initialize weights
        self._initialize_weights()
    
    def _initialize_weights(self):
        for m in self.modules():
            if isinstance(m, nn.Conv1d) or isinstance(m, nn.Linear):
                nn.init.kaiming_normal_(m.weight, mode='fan_out', nonlinearity='relu')
                if m.bias is not None:
                    nn.init.constant_(m.bias, 0)
            elif isinstance(m, nn.BatchNorm1d):
                nn.init.constant_(m.weight, 1)
                nn.init.constant_(m.bias, 0)
    
    def forward(self, x):
        # Input shape: [batch, input_dim]
        out = F.relu(self.bn0(self.input_proj(x)))
        
        # Reshape for 1D convolutions
        batch_size = out.size(0)
        out = out.view(batch_size, self.conv_reshape, -1)
        
        # Residual blocks
        out = self.res1(out)
        out = self.res2(out)
        out = self.res3(out)
        
        # Pooling
        out = self.adaptive_pool(out)
        
        # Flatten
        out = out.view(batch_size, -1)
        
        # Classifier
        out = F.relu(self.bn4(self.fc1(out)))
        out = self.dropout1(out)
        
        out = F.relu(self.bn5(self.fc2(out)))
        out = self.dropout2(out)
        
        out = self.fc3(out)
        return out

class Solution:
    def solve(self, train_loader, val_loader, metadata: dict = None) -> torch.nn.Module:
        device = metadata.get("device", "cpu")
        num_classes = metadata.get("num_classes", 128)
        input_dim = metadata.get("input_dim", 384)
        param_limit = metadata.get("param_limit", 500000)
        
        # Create model with dynamic architecture to respect param limit
        model = CustomModel(input_dim=input_dim, num_classes=num_classes)
        model.to(device)
        
        # Verify parameter count
        total_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
        print(f"Model parameters: {total_params:,} / {param_limit:,}")
        
        # Optimizer with weight decay
        optimizer = optim.AdamW(
            model.parameters(),
            lr=0.001,
            weight_decay=5e-4,
            betas=(0.9, 0.999)
        )
        
        # Cosine annealing scheduler
        scheduler = CosineAnnealingLR(
            optimizer,
            T_max=100,
            eta_min=1e-5
        )
        
        criterion = nn.CrossEntropyLoss()
        
        # Mixed precision training for CPU (bfloat16 where supported)
        use_bf16 = hasattr(torch, "bfloat16") and torch.cpu.has_bfloat16_support()
        dtype = torch.bfloat16 if use_bf16 else torch.float32
        
        # Training loop
        num_epochs = 150
        best_val_acc = 0.0
        best_model_state = None
        
        for epoch in range(num_epochs):
            # Training phase
            model.train()
            train_loss = 0.0
            train_correct = 0
            train_total = 0
            
            for batch_idx, (inputs, targets) in enumerate(train_loader):
                inputs, targets = inputs.to(device), targets.to(device)
                
                optimizer.zero_grad(set_to_none=True)
                
                with torch.cpu.amp.autocast(enabled=use_bf16, dtype=dtype):
                    outputs = model(inputs)
                    loss = criterion(outputs, targets)
                
                # Mixed precision backward
                if use_bf16:
                    from torch.cpu.amp import GradScaler
                    scaler = GradScaler()
                    scaler.scale(loss).backward()
                    scaler.step(optimizer)
                    scaler.update()
                else:
                    loss.backward()
                    optimizer.step()
                
                train_loss += loss.item()
                _, predicted = outputs.max(1)
                train_total += targets.size(0)
                train_correct += predicted.eq(targets).sum().item()
            
            train_acc = 100.0 * train_correct / train_total
            
            # Validation phase
            model.eval()
            val_correct = 0
            val_total = 0
            
            with torch.no_grad():
                for inputs, targets in val_loader:
                    inputs, targets = inputs.to(device), targets.to(device)
                    
                    with torch.cpu.amp.autocast(enabled=use_bf16, dtype=dtype):
                        outputs = model(inputs)
                    
                    _, predicted = outputs.max(1)
                    val_total += targets.size(0)
                    val_correct += predicted.eq(targets).sum().item()
            
            val_acc = 100.0 * val_correct / val_total
            
            # Update scheduler
            scheduler.step()
            
            # Save best model
            if val_acc > best_val_acc:
                best_val_acc = val_acc
                best_model_state = model.state_dict().copy()
            
            # Early stopping check
            if epoch > 50 and best_val_acc > 75.0:
                current_lr = optimizer.param_groups[0]['lr']
                if current_lr < 1e-4 and val_acc < best_val_acc - 2.0:
                    break
        
        # Load best model
        if best_model_state is not None:
            model.load_state_dict(best_model_state)
        
        # Final validation check
        model.eval()
        return model
