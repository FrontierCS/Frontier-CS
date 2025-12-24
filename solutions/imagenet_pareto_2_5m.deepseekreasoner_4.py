import torch
import torch.nn as nn
import torch.optim as optim
from torch.optim.lr_scheduler import CosineAnnealingLR
import math

class ResidualBlock(nn.Module):
    def __init__(self, in_features, out_features, dropout_rate=0.1):
        super().__init__()
        self.linear1 = nn.Linear(in_features, out_features)
        self.bn1 = nn.BatchNorm1d(out_features)
        self.linear2 = nn.Linear(out_features, out_features)
        self.bn2 = nn.BatchNorm1d(out_features)
        self.dropout = nn.Dropout(dropout_rate)
        self.activation = nn.GELU()
        
        self.shortcut = nn.Identity() if in_features == out_features else nn.Linear(in_features, out_features)
        
    def forward(self, x):
        identity = self.shortcut(x)
        out = self.linear1(x)
        out = self.bn1(out)
        out = self.activation(out)
        out = self.dropout(out)
        out = self.linear2(out)
        out = self.bn2(out)
        out = self.activation(out + identity)
        out = self.dropout(out)
        return out

class Solution:
    def solve(self, train_loader, val_loader, metadata: dict = None) -> torch.nn.Module:
        input_dim = metadata["input_dim"]
        num_classes = metadata["num_classes"]
        device = metadata["device"]
        
        class EfficientNet(nn.Module):
            def __init__(self):
                super().__init__()
                self.features = nn.Sequential(
                    nn.Linear(input_dim, 768),
                    nn.BatchNorm1d(768),
                    nn.GELU(),
                    nn.Dropout(0.1),
                    
                    ResidualBlock(768, 768, 0.1),
                    ResidualBlock(768, 768, 0.1),
                    ResidualBlock(768, 512, 0.15),
                    ResidualBlock(512, 512, 0.15),
                    ResidualBlock(512, 384, 0.15),
                    ResidualBlock(384, 384, 0.15),
                    ResidualBlock(384, 256, 0.2),
                    ResidualBlock(256, 256, 0.2),
                    
                    nn.AdaptiveAvgPool1d(1),
                    nn.Flatten(),
                )
                
                self.classifier = nn.Sequential(
                    nn.Linear(256, 256),
                    nn.BatchNorm1d(256),
                    nn.GELU(),
                    nn.Dropout(0.2),
                    nn.Linear(256, num_classes)
                )
                
                self._initialize_weights()
            
            def _initialize_weights(self):
                for m in self.modules():
                    if isinstance(m, nn.Linear):
                        nn.init.kaiming_normal_(m.weight, mode='fan_out', nonlinearity='gelu')
                        if m.bias is not None:
                            nn.init.constant_(m.bias, 0)
                    elif isinstance(m, nn.BatchNorm1d):
                        nn.init.constant_(m.weight, 1)
                        nn.init.constant_(m.bias, 0)
            
            def forward(self, x):
                x = self.features(x)
                return self.classifier(x)
        
        model = EfficientNet().to(device)
        
        total_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
        if total_params > 2500000:
            raise ValueError(f"Model has {total_params} parameters, exceeding 2.5M limit")
        
        criterion = nn.CrossEntropyLoss(label_smoothing=0.1)
        optimizer = optim.AdamW(model.parameters(), lr=0.001, weight_decay=0.05)
        scheduler = CosineAnnealingLR(optimizer, T_max=50, eta_min=1e-6)
        
        best_acc = 0
        best_model_state = None
        
        for epoch in range(100):
            model.train()
            total_loss = 0
            correct = 0
            total = 0
            
            for batch_idx, (inputs, targets) in enumerate(train_loader):
                inputs, targets = inputs.to(device), targets.to(device)
                
                optimizer.zero_grad()
                outputs = model(inputs)
                loss = criterion(outputs, targets)
                loss.backward()
                
                torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
                optimizer.step()
                
                total_loss += loss.item()
                _, predicted = outputs.max(1)
                total += targets.size(0)
                correct += predicted.eq(targets).sum().item()
            
            scheduler.step()
            
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
            if val_acc > best_acc:
                best_acc = val_acc
                best_model_state = {k: v.cpu().clone() for k, v in model.state_dict().items()}
            
            if epoch > 30 and val_acc < best_acc - 5:
                break
        
        if best_model_state is not None:
            model.load_state_dict(best_model_state)
        model.eval()
        return model.to(device)
