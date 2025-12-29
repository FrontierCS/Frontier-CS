import torch
import torch.nn as nn
import torch.optim as optim
from torch.optim.lr_scheduler import ReduceLROnPlateau
import copy
import time

class EfficientMLP(nn.Module):
    def __init__(self, input_dim, num_classes, hidden_dims, dropout_rate=0.3):
        super().__init__()
        layers = []
        prev_dim = input_dim
        
        for i, h_dim in enumerate(hidden_dims):
            layers.append(nn.Linear(prev_dim, h_dim))
            layers.append(nn.BatchNorm1d(h_dim))
            layers.append(nn.ReLU(inplace=True))
            if dropout_rate > 0 and i < len(hidden_dims) - 1:
                layers.append(nn.Dropout(dropout_rate))
            prev_dim = h_dim
            
        layers.append(nn.Linear(prev_dim, num_classes))
        self.model = nn.Sequential(*layers)
        
    def forward(self, x):
        return self.model(x)

class Solution:
    def solve(self, train_loader, val_loader, metadata: dict = None) -> nn.Module:
        device = metadata.get("device", "cpu")
        input_dim = metadata["input_dim"]
        num_classes = metadata["num_classes"]
        param_limit = metadata["param_limit"]
        
        hidden_configs = [
            [512, 256, 128],  # Deep and efficient
            [384, 256, 192, 128],  # Progressive compression
            [256, 256, 256, 128],  # Uniform
        ]
        
        best_model = None
        best_val_acc = 0.0
        
        for hidden_dims in hidden_configs:
            model = EfficientMLP(
                input_dim=input_dim,
                num_classes=num_classes,
                hidden_dims=hidden_dims,
                dropout_rate=0.3
            ).to(device)
            
            param_count = sum(p.numel() for p in model.parameters() if p.requires_grad)
            if param_count > param_limit:
                continue
                
            print(f"Trying architecture {hidden_dims}, params: {param_count}")
            
            optimizer = optim.AdamW(
                model.parameters(),
                lr=0.001,
                weight_decay=0.0001
            )
            scheduler = ReduceLROnPlateau(
                optimizer,
                mode='max',
                patience=5,
                factor=0.5,
                min_lr=1e-6
            )
            criterion = nn.CrossEntropyLoss()
            
            best_epoch_model = None
            best_epoch_acc = 0.0
            patience = 15
            patience_counter = 0
            
            for epoch in range(100):
                model.train()
                train_loss = 0.0
                
                for batch_idx, (data, target) in enumerate(train_loader):
                    data, target = data.to(device), target.to(device)
                    
                    optimizer.zero_grad()
                    output = model(data)
                    loss = criterion(output, target)
                    loss.backward()
                    
                    torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
                    optimizer.step()
                    
                    train_loss += loss.item()
                
                model.eval()
                val_correct = 0
                val_total = 0
                with torch.no_grad():
                    for data, target in val_loader:
                        data, target = data.to(device), target.to(device)
                        output = model(data)
                        pred = output.argmax(dim=1)
                        val_correct += (pred == target).sum().item()
                        val_total += target.size(0)
                
                val_acc = val_correct / val_total
                scheduler.step(val_acc)
                
                if val_acc > best_epoch_acc:
                    best_epoch_acc = val_acc
                    best_epoch_model = copy.deepcopy(model)
                    patience_counter = 0
                else:
                    patience_counter += 1
                
                if patience_counter >= patience:
                    break
            
            if best_epoch_acc > best_val_acc:
                best_val_acc = best_epoch_acc
                best_model = best_epoch_model
                print(f"New best val accuracy: {best_val_acc:.4f}")
            
            if best_val_acc > 0.85:
                break
        
        if best_model is None:
            hidden_dims = [384, 256, 192]
            best_model = EfficientMLP(
                input_dim=input_dim,
                num_classes=num_classes,
                hidden_dims=hidden_dims,
                dropout_rate=0.3
            ).to(device)
            
            optimizer = optim.AdamW(best_model.parameters(), lr=0.001, weight_decay=0.0001)
            criterion = nn.CrossEntropyLoss()
            
            for epoch in range(50):
                best_model.train()
                for data, target in train_loader:
                    data, target = data.to(device), target.to(device)
                    optimizer.zero_grad()
                    output = best_model(data)
                    loss = criterion(output, target)
                    loss.backward()
                    optimizer.step()
        
        param_count = sum(p.numel() for p in best_model.parameters() if p.requires_grad)
        print(f"Final model parameters: {param_count}")
        
        best_model.eval()
        return best_model