import torch
import torch.nn as nn
import torch.nn.functional as F
import math
from typing import Optional

class ResidualBlock(nn.Module):
    def __init__(self, in_features, out_features, dropout_rate=0.2, use_bottleneck=True):
        super().__init__()
        self.use_bottleneck = use_bottleneck
        self.in_features = in_features
        self.out_features = out_features
        
        if use_bottleneck and in_features > 256:
            bottleneck = in_features // 4
            self.bottleneck = nn.Sequential(
                nn.Linear(in_features, bottleneck, bias=False),
                nn.BatchNorm1d(bottleneck),
                nn.ReLU(inplace=True)
            )
            in_features = bottleneck
        else:
            self.bottleneck = None
        
        self.linear1 = nn.Linear(in_features, out_features, bias=False)
        self.bn1 = nn.BatchNorm1d(out_features)
        self.relu1 = nn.ReLU(inplace=True)
        self.dropout1 = nn.Dropout(dropout_rate)
        
        self.linear2 = nn.Linear(out_features, out_features, bias=False)
        self.bn2 = nn.BatchNorm1d(out_features)
        
        self.shortcut = nn.Sequential()
        if self.in_features != self.out_features:
            self.shortcut = nn.Sequential(
                nn.Linear(self.in_features, out_features, bias=False),
                nn.BatchNorm1d(out_features)
            )
        
        self.relu2 = nn.ReLU(inplace=True)
        self.dropout2 = nn.Dropout(dropout_rate)
        
    def forward(self, x):
        identity = x
        
        if self.bottleneck is not None:
            x = self.bottleneck(x)
        
        out = self.linear1(x)
        out = self.bn1(out)
        out = self.relu1(out)
        out = self.dropout1(out)
        
        out = self.linear2(out)
        out = self.bn2(out)
        
        shortcut_out = self.shortcut(identity)
        out += shortcut_out
        
        out = self.relu2(out)
        out = self.dropout2(out)
        
        return out

class EfficientMLP(nn.Module):
    def __init__(self, input_dim=384, num_classes=128, param_limit=2500000):
        super().__init__()
        self.input_dim = input_dim
        self.num_classes = num_classes
        
        # Carefully designed architecture to maximize capacity within budget
        hidden_dims = [512, 768, 768, 512, 384]
        
        self.input_layer = nn.Sequential(
            nn.Linear(input_dim, hidden_dims[0]),
            nn.BatchNorm1d(hidden_dims[0]),
            nn.ReLU(inplace=True),
            nn.Dropout(0.2)
        )
        
        self.residual_blocks = nn.ModuleList()
        for i in range(len(hidden_dims) - 1):
            block = ResidualBlock(
                hidden_dims[i],
                hidden_dims[i + 1],
                dropout_rate=0.2,
                use_bottleneck=(hidden_dims[i] > 384)
            )
            self.residual_blocks.append(block)
        
        # Attention mechanism for feature refinement
        self.attention = nn.Sequential(
            nn.Linear(hidden_dims[-1], hidden_dims[-1] // 4),
            nn.ReLU(inplace=True),
            nn.Linear(hidden_dims[-1] // 4, hidden_dims[-1]),
            nn.Sigmoid()
        )
        
        # Final classification layers
        self.fc1 = nn.Linear(hidden_dims[-1], 256)
        self.bn_fc = nn.BatchNorm1d(256)
        self.relu_fc = nn.ReLU(inplace=True)
        self.dropout_fc = nn.Dropout(0.3)
        
        self.fc2 = nn.Linear(256, num_classes)
        
        self._initialize_weights()
        self._validate_parameter_count(param_limit)
    
    def _initialize_weights(self):
        for m in self.modules():
            if isinstance(m, nn.Linear):
                nn.init.kaiming_normal_(m.weight, mode='fan_out', nonlinearity='relu')
                if m.bias is not None:
                    nn.init.constant_(m.bias, 0)
            elif isinstance(m, nn.BatchNorm1d):
                nn.init.constant_(m.weight, 1)
                nn.init.constant_(m.bias, 0)
    
    def _validate_parameter_count(self, limit):
        total_params = sum(p.numel() for p in self.parameters() if p.requires_grad)
        if total_params > limit:
            raise ValueError(f"Model has {total_params} parameters, exceeds limit {limit}")
    
    def forward(self, x):
        x = self.input_layer(x)
        
        for block in self.residual_blocks:
            x = block(x)
        
        # Apply attention
        attn_weights = self.attention(x)
        x = x * attn_weights
        
        # Final layers
        x = self.fc1(x)
        x = self.bn_fc(x)
        x = self.relu_fc(x)
        x = self.dropout_fc(x)
        
        x = self.fc2(x)
        return x

class Solution:
    def solve(self, train_loader, val_loader, metadata: dict = None) -> torch.nn.Module:
        num_classes = metadata["num_classes"]
        input_dim = metadata["input_dim"]
        param_limit = metadata["param_limit"]
        device = metadata.get("device", "cpu")
        baseline_accuracy = metadata.get("baseline_accuracy", 0.85)
        
        model = EfficientMLP(
            input_dim=input_dim,
            num_classes=num_classes,
            param_limit=param_limit
        )
        
        # Verify parameter count
        total_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
        if total_params > param_limit:
            raise ValueError(f"Model exceeds parameter limit: {total_params} > {param_limit}")
        
        model.to(device)
        
        # Training configuration
        criterion = nn.CrossEntropyLoss()
        optimizer = torch.optim.AdamW(
            model.parameters(),
            lr=0.001,
            weight_decay=0.01
        )
        
        scheduler = torch.optim.lr_scheduler.OneCycleLR(
            optimizer,
            max_lr=0.01,
            epochs=100,
            steps_per_epoch=len(train_loader),
            pct_start=0.3,
            anneal_strategy='cos'
        )
        
        # Early stopping
        best_val_acc = 0.0
        best_model_state = None
        patience = 15
        patience_counter = 0
        
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
                scheduler.step()
                
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
            
            # Early stopping logic
            if val_acc > best_val_acc + 0.01:  # Improvement threshold
                best_val_acc = val_acc
                best_model_state = model.state_dict().copy()
                patience_counter = 0
            else:
                patience_counter += 1
            
            if patience_counter >= patience:
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
        
        final_val_acc = final_val_correct / final_val_total
        
        # If validation accuracy is too low, do additional training with different settings
        if final_val_acc < baseline_accuracy + 0.02:
            model.train()
            optimizer = torch.optim.SGD(
                model.parameters(),
                lr=0.001,
                momentum=0.9,
                weight_decay=1e-4
            )
            
            for epoch in range(30):
                model.train()
                for inputs, targets in train_loader:
                    inputs, targets = inputs.to(device), targets.to(device)
                    optimizer.zero_grad()
                    outputs = model(inputs)
                    loss = criterion(outputs, targets)
                    loss.backward()
                    optimizer.step()
        
        model.eval()
        return model
