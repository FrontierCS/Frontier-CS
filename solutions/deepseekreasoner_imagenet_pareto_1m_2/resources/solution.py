import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim
from torch.optim.lr_scheduler import CosineAnnealingLR
import math
from collections import OrderedDict

class ResidualBlock(nn.Module):
    def __init__(self, in_dim, out_dim, dropout_rate=0.2):
        super().__init__()
        self.norm1 = nn.BatchNorm1d(in_dim)
        self.linear1 = nn.Linear(in_dim, out_dim)
        self.norm2 = nn.BatchNorm1d(out_dim)
        self.linear2 = nn.Linear(out_dim, out_dim)
        self.dropout = nn.Dropout(dropout_rate)
        self.shortcut = nn.Linear(in_dim, out_dim) if in_dim != out_dim else nn.Identity()
        
    def forward(self, x):
        identity = self.shortcut(x)
        out = self.norm1(x)
        out = F.relu(out)
        out = self.linear1(out)
        out = self.norm2(out)
        out = F.relu(out)
        out = self.dropout(out)
        out = self.linear2(out)
        return out + identity

class EfficientNet(nn.Module):
    def __init__(self, input_dim=384, num_classes=128, width_mult=1.0, depth_mult=1.0):
        super().__init__()
        base_width = 384
        base_depth = 4
        
        width = int(base_width * width_mult)
        depth = int(base_depth * depth_mult)
        
        layers = []
        in_dim = input_dim
        
        for i in range(depth):
            out_dim = width if i < depth - 1 else max(width // 2, 128)
            layers.append(ResidualBlock(in_dim, out_dim, dropout_rate=0.2))
            in_dim = out_dim
        
        layers.append(nn.BatchNorm1d(in_dim))
        layers.append(nn.ReLU())
        layers.append(nn.Dropout(0.2))
        layers.append(nn.Linear(in_dim, num_classes))
        
        self.model = nn.Sequential(*layers)
        
    def forward(self, x):
        return self.model(x)

class Solution:
    def solve(self, train_loader, val_loader, metadata: dict = None) -> torch.nn.Module:
        device = metadata.get("device", "cpu")
        input_dim = metadata["input_dim"]
        num_classes = metadata["num_classes"]
        param_limit = metadata["param_limit"]
        
        best_model = None
        best_val_acc = 0.0
        
        width_multipliers = [0.8, 1.0, 1.2]
        depth_multipliers = [1.0, 1.2, 1.5]
        
        for w_mult in width_multipliers:
            for d_mult in depth_multipliers:
                model = EfficientNet(input_dim, num_classes, w_mult, d_mult).to(device)
                param_count = sum(p.numel() for p in model.parameters() if p.requires_grad)
                
                if param_count > param_limit:
                    continue
                
                print(f"Testing config: width={w_mult}, depth={d_mult}, params={param_count}")
                
                val_acc = self._train_and_evaluate(model, train_loader, val_loader, device)
                
                if val_acc > best_val_acc:
                    best_val_acc = val_acc
                    best_model = model
                    print(f"New best: {val_acc:.4f}")
        
        if best_model is None:
            best_model = EfficientNet(input_dim, num_classes, 0.8, 1.0).to(device)
            best_val_acc = self._train_and_evaluate(best_model, train_loader, val_loader, device)
        
        return best_model
    
    def _train_and_evaluate(self, model, train_loader, val_loader, device, epochs=50):
        optimizer = optim.AdamW(model.parameters(), lr=0.001, weight_decay=0.01)
        scheduler = CosineAnnealingLR(optimizer, T_max=epochs, eta_min=1e-5)
        criterion = nn.CrossEntropyLoss(label_smoothing=0.1)
        
        best_acc = 0.0
        patience = 10
        patience_counter = 0
        
        for epoch in range(epochs):
            model.train()
            total_loss = 0
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
                pred = output.argmax(dim=1, keepdim=True)
                correct += pred.eq(target.view_as(pred)).sum().item()
                total += target.size(0)
            
            scheduler.step()
            
            train_acc = 100. * correct / total
            
            val_acc = self._evaluate(model, val_loader, device)
            
            if val_acc > best_acc:
                best_acc = val_acc
                patience_counter = 0
            else:
                patience_counter += 1
            
            if patience_counter >= patience:
                break
        
        return best_acc
    
    def _evaluate(self, model, loader, device):
        model.eval()
        correct = 0
        total = 0
        with torch.no_grad():
            for data, target in loader:
                data, target = data.to(device), target.to(device)
                output = model(data)
                pred = output.argmax(dim=1)
                correct += pred.eq(target).sum().item()
                total += target.size(0)
        return 100. * correct / total
