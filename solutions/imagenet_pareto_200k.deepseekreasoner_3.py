import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim
from torch.optim.lr_scheduler import CosineAnnealingLR
import math

class EfficientNet(nn.Module):
    def __init__(self, input_dim=384, num_classes=128, hidden_dims=None):
        super().__init__()
        if hidden_dims is None:
            hidden_dims = [256, 256, 192, 128]
        
        layers = []
        prev_dim = input_dim
        
        for i, h_dim in enumerate(hidden_dims):
            layers.append(nn.Linear(prev_dim, h_dim))
            layers.append(nn.BatchNorm1d(h_dim))
            layers.append(nn.ReLU())
            layers.append(nn.Dropout(0.25 if i < 2 else 0.1))
            prev_dim = h_dim
        
        self.features = nn.Sequential(*layers)
        self.output = nn.Linear(prev_dim, num_classes)
        
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
        x = self.features(x)
        return self.output(x)

class Solution:
    def solve(self, train_loader, val_loader, metadata: dict = None) -> torch.nn.Module:
        device = torch.device(metadata["device"] if metadata and "device" in metadata else "cpu")
        input_dim = metadata["input_dim"] if metadata and "input_dim" in metadata else 384
        num_classes = metadata["num_classes"] if metadata and "num_classes" in metadata else 128
        
        hidden_configs = [
            [256, 256, 192, 128],  # Base config
            [320, 256, 192, 128],  # Slightly wider first layer
            [256, 256, 256, 128],  # More capacity in middle
            [288, 256, 192, 160],  # Wider output
        ]
        
        best_model = None
        best_val_acc = 0.0
        
        for config in hidden_configs:
            model = EfficientNet(input_dim, num_classes, config)
            model.to(device)
            
            param_count = sum(p.numel() for p in model.parameters() if p.requires_grad)
            if param_count > 200000:
                continue
            
            val_acc = self._train_and_validate(model, train_loader, val_loader, device)
            
            if val_acc > best_val_acc:
                best_val_acc = val_acc
                best_model = model
        
        if best_model is None:
            best_model = EfficientNet(input_dim, num_classes, [256, 256, 192, 128])
            best_model.to(device)
            self._train_and_validate(best_model, train_loader, val_loader, device)
        
        return best_model
    
    def _train_and_validate(self, model, train_loader, val_loader, device):
        optimizer = optim.AdamW(
            model.parameters(),
            lr=0.001,
            weight_decay=0.01,
            betas=(0.9, 0.999)
        )
        
        scheduler = CosineAnnealingLR(optimizer, T_max=50, eta_min=1e-5)
        criterion = nn.CrossEntropyLoss(label_smoothing=0.1)
        
        best_val_acc = 0.0
        patience = 15
        patience_counter = 0
        
        for epoch in range(100):
            model.train()
            total_loss = 0.0
            correct = 0
            total = 0
            
            for batch_idx, (data, target) in enumerate(train_loader):
                data, target = data.to(device), target.to(device)
                
                optimizer.zero_grad()
                output = model(data)
                loss = criterion(output, target)
                loss.backward()
                
                torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
                optimizer.step()
                
                total_loss += loss.item()
                pred = output.argmax(dim=1)
                correct += (pred == target).sum().item()
                total += target.size(0)
            
            train_acc = correct / total
            
            val_acc = self._validate(model, val_loader, device)
            
            if val_acc > best_val_acc:
                best_val_acc = val_acc
                patience_counter = 0
            else:
                patience_counter += 1
            
            if patience_counter >= patience:
                break
            
            scheduler.step()
        
        model.load_state_dict(torch.load('best_model.pth', map_location=device))
        return best_val_acc
    
    def _validate(self, model, val_loader, device):
        model.eval()
        correct = 0
        total = 0
        
        with torch.no_grad():
            for data, target in val_loader:
                data, target = data.to(device), target.to(device)
                output = model(data)
                pred = output.argmax(dim=1)
                correct += (pred == target).sum().item()
                total += target.size(0)
        
        return correct / total

def count_parameters(model):
    return sum(p.numel() for p in model.parameters() if p.requires_grad)
