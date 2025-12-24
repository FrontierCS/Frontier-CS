import torch
import torch.nn as nn
import torch.optim as optim
import math
import numpy as np

class ResidualBlock(nn.Module):
    def __init__(self, hidden_dim, dropout_rate=0.2):
        super(ResidualBlock, self).__init__()
        self.linear = nn.Linear(hidden_dim, hidden_dim)
        self.bn = nn.BatchNorm1d(hidden_dim)
        self.act = nn.GELU()
        self.dropout = nn.Dropout(dropout_rate)

    def forward(self, x):
        residual = x
        out = self.linear(x)
        out = self.bn(out)
        out = self.act(out)
        out = self.dropout(out)
        return residual + out

class ParetoModel(nn.Module):
    def __init__(self, input_dim, num_classes, hidden_dim=712, num_blocks=4):
        super(ParetoModel, self).__init__()
        
        # Input normalization
        self.input_bn = nn.BatchNorm1d(input_dim)
        
        # Input projection
        self.input_proj = nn.Linear(input_dim, hidden_dim)
        self.input_act = nn.GELU()
        
        # Residual blocks
        self.blocks = nn.ModuleList([
            ResidualBlock(hidden_dim) for _ in range(num_blocks)
        ])
        
        # Output head
        self.final_bn = nn.BatchNorm1d(hidden_dim)
        self.classifier = nn.Linear(hidden_dim, num_classes)
        
        # Initialize weights
        self._init_weights()

    def _init_weights(self):
        for m in self.modules():
            if isinstance(m, nn.Linear):
                nn.init.kaiming_normal_(m.weight, mode='fan_out', nonlinearity='relu')
                if m.bias is not None:
                    nn.init.constant_(m.bias, 0)
            elif isinstance(m, nn.BatchNorm1d):
                nn.init.constant_(m.weight, 1)
                nn.init.constant_(m.bias, 0)

    def forward(self, x):
        x = self.input_bn(x)
        x = self.input_proj(x)
        x = self.input_act(x)
        
        for block in self.blocks:
            x = block(x)
            
        x = self.final_bn(x)
        x = self.classifier(x)
        return x

class Solution:
    def solve(self, train_loader, val_loader, metadata: dict = None) -> torch.nn.Module:
        # Extract metadata
        input_dim = metadata.get("input_dim", 384)
        num_classes = metadata.get("num_classes", 128)
        device = metadata.get("device", "cpu")
        
        # Configuration
        # H=712 with 4 blocks results in ~2.4M parameters, safely under the 2.5M limit
        HIDDEN_DIM = 712
        NUM_BLOCKS = 4
        EPOCHS = 80
        LR = 0.001
        WEIGHT_DECAY = 1e-4
        MIXUP_ALPHA = 0.4
        
        # Initialize model
        model = ParetoModel(input_dim, num_classes, HIDDEN_DIM, NUM_BLOCKS)
        model = model.to(device)
        
        # Verify parameter count
        param_count = sum(p.numel() for p in model.parameters() if p.requires_grad)
        if param_count > 2500000:
            # Fallback to smaller model if calculation was wrong
            HIDDEN_DIM = 600
            model = ParetoModel(input_dim, num_classes, HIDDEN_DIM, NUM_BLOCKS)
            model = model.to(device)
            
        optimizer = optim.AdamW(model.parameters(), lr=LR, weight_decay=WEIGHT_DECAY)
        scheduler = optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=EPOCHS)
        criterion = nn.CrossEntropyLoss(label_smoothing=0.1)
        
        best_val_acc = 0.0
        best_model_state = None
        
        # Training Loop
        for epoch in range(EPOCHS):
            model.train()
            for inputs, targets in train_loader:
                inputs, targets = inputs.to(device), targets.to(device)
                
                optimizer.zero_grad()
                
                # Mixup augmentation
                if MIXUP_ALPHA > 0:
                    lam = np.random.beta(MIXUP_ALPHA, MIXUP_ALPHA)
                    index = torch.randperm(inputs.size(0)).to(device)
                    mixed_inputs = lam * inputs + (1 - lam) * inputs[index]
                    target_a, target_b = targets, targets[index]
                    
                    outputs = model(mixed_inputs)
                    loss = lam * criterion(outputs, target_a) + (1 - lam) * criterion(outputs, target_b)
                else:
                    outputs = model(inputs)
                    loss = criterion(outputs, targets)
                
                loss.backward()
                torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
                optimizer.step()
            
            scheduler.step()
            
            # Validation
            if epoch % 5 == 0 or epoch > EPOCHS - 10:
                model.eval()
                correct = 0
                total = 0
                with torch.no_grad():
                    for inputs, targets in val_loader:
                        inputs, targets = inputs.to(device), targets.to(device)
                        outputs = model(inputs)
                        _, predicted = outputs.max(1)
                        total += targets.size(0)
                        correct += predicted.eq(targets).sum().item()
                
                val_acc = correct / total
                if val_acc >= best_val_acc:
                    best_val_acc = val_acc
                    # Deep copy of state dict
                    best_model_state = {k: v.cpu().clone() for k, v in model.state_dict().items()}
        
        # Load best model
        if best_model_state is not None:
            model.load_state_dict(best_model_state)
            
        return model
