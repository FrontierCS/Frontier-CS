import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.optim import AdamW
from torch.optim.lr_scheduler import CosineAnnealingLR
import copy

class BottleneckBlock(nn.Module):
    def __init__(self, in_channels, out_channels, bottleneck_ratio=4):
        super().__init__()
        self.conv1 = nn.Linear(in_channels, out_channels // bottleneck_ratio)
        self.bn1 = nn.BatchNorm1d(out_channels // bottleneck_ratio)
        self.conv2 = nn.Linear(out_channels // bottleneck_ratio, out_channels // bottleneck_ratio)
        self.bn2 = nn.BatchNorm1d(out_channels // bottleneck_ratio)
        self.conv3 = nn.Linear(out_channels // bottleneck_ratio, out_channels)
        self.bn3 = nn.BatchNorm1d(out_channels)
        self.shortcut = nn.Linear(in_channels, out_channels) if in_channels != out_channels else nn.Identity()
        
    def forward(self, x):
        residual = self.shortcut(x)
        out = F.relu(self.bn1(self.conv1(x)))
        out = F.relu(self.bn2(self.conv2(out)))
        out = self.bn3(self.conv3(out))
        out += residual
        return F.relu(out)

class Net(nn.Module):
    def __init__(self, input_dim, num_classes):
        super().__init__()
        # Carefully designed architecture to stay under 1M params
        self.input_norm = nn.BatchNorm1d(input_dim)
        self.dropout = nn.Dropout(0.3)
        
        # Progressive width expansion then contraction
        self.block1 = BottleneckBlock(input_dim, 512)
        self.block2 = BottleneckBlock(512, 768)
        self.block3 = BottleneckBlock(768, 896)
        self.block4 = BottleneckBlock(896, 768)
        self.block5 = BottleneckBlock(768, 512)
        
        # Head with skip connection
        self.head = nn.Sequential(
            nn.Linear(512, 256),
            nn.BatchNorm1d(256),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(256, num_classes)
        )
        
    def forward(self, x):
        x = self.input_norm(x)
        x = self.dropout(x)
        x = self.block1(x)
        x = self.block2(x)
        x = self.block3(x)
        x = self.block4(x)
        x = self.block5(x)
        return self.head(x)

class Solution:
    def solve(self, train_loader, val_loader, metadata: dict = None):
        device = metadata.get("device", "cpu")
        input_dim = metadata["input_dim"]
        num_classes = metadata["num_classes"]
        
        model = Net(input_dim, num_classes).to(device)
        
        # Verify parameter count
        total_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
        if total_params > 1000000:
            # If over limit, create simpler model
            model = nn.Sequential(
                nn.Linear(input_dim, 896),
                nn.BatchNorm1d(896),
                nn.ReLU(),
                nn.Dropout(0.3),
                nn.Linear(896, 512),
                nn.BatchNorm1d(512),
                nn.ReLU(),
                nn.Dropout(0.3),
                nn.Linear(512, 256),
                nn.BatchNorm1d(256),
                nn.ReLU(),
                nn.Dropout(0.2),
                nn.Linear(256, num_classes)
            ).to(device)
        
        optimizer = AdamW(model.parameters(), lr=0.001, weight_decay=1e-4)
        scheduler = CosineAnnealingLR(optimizer, T_max=50, eta_min=1e-6)
        criterion = nn.CrossEntropyLoss()
        
        best_acc = 0
        best_model = None
        patience = 10
        patience_counter = 0
        
        for epoch in range(100):
            # Training
            model.train()
            train_loss = 0
            for inputs, targets in train_loader:
                inputs, targets = inputs.to(device), targets.to(device)
                optimizer.zero_grad()
                outputs = model(inputs)
                loss = criterion(outputs, targets)
                loss.backward()
                torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
                optimizer.step()
                train_loss += loss.item()
            
            scheduler.step()
            
            # Validation
            model.eval()
            correct = 0
            total = 0
            with torch.no_grad():
                for inputs, targets in val_loader:
                    inputs, targets = inputs.to(device), targets.to(device)
                    outputs = model(inputs)
                    preds = outputs.argmax(dim=1)
                    correct += (preds == targets).sum().item()
                    total += targets.numel()
            
            val_acc = correct / total
            if val_acc > best_acc:
                best_acc = val_acc
                best_model = copy.deepcopy(model.state_dict())
                patience_counter = 0
            else:
                patience_counter += 1
            
            if patience_counter >= patience:
                break
        
        # Load best model
        model.load_state_dict(best_model)
        return model