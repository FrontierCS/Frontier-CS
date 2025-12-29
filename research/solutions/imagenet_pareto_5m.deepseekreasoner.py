import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.optim import AdamW
from torch.optim.lr_scheduler import CosineAnnealingLR
import math

class ResidualBlock(nn.Module):
    def __init__(self, in_features, out_features, dropout=0.2):
        super().__init__()
        self.norm1 = nn.BatchNorm1d(in_features)
        self.linear1 = nn.Linear(in_features, out_features)
        self.norm2 = nn.BatchNorm1d(out_features)
        self.linear2 = nn.Linear(out_features, out_features)
        self.dropout = nn.Dropout(dropout)
        self.shortcut = nn.Linear(in_features, out_features) if in_features != out_features else nn.Identity()
        
    def forward(self, x):
        residual = self.shortcut(x)
        out = self.norm1(x)
        out = F.gelu(self.linear1(out))
        out = self.norm2(out)
        out = self.linear2(out)
        out = self.dropout(out)
        return out + residual

class SolutionModel(nn.Module):
    def __init__(self, input_dim=384, num_classes=128):
        super().__init__()
        hidden1 = 1024
        hidden2 = 768
        hidden3 = 512
        
        self.input_proj = nn.Sequential(
            nn.Linear(input_dim, hidden1),
            nn.BatchNorm1d(hidden1),
            nn.GELU(),
            nn.Dropout(0.2)
        )
        
        self.blocks = nn.Sequential(
            ResidualBlock(hidden1, hidden1),
            ResidualBlock(hidden1, hidden2),
            ResidualBlock(hidden2, hidden2),
            ResidualBlock(hidden2, hidden3),
            ResidualBlock(hidden3, hidden3),
        )
        
        self.output = nn.Sequential(
            nn.BatchNorm1d(hidden3),
            nn.Linear(hidden3, num_classes)
        )
        
    def forward(self, x):
        x = self.input_proj(x)
        x = self.blocks(x)
        return self.output(x)

class Solution:
    def solve(self, train_loader, val_loader, metadata: dict = None):
        device = torch.device(metadata["device"] if metadata else "cpu")
        input_dim = metadata["input_dim"]
        num_classes = metadata["num_classes"]
        
        model = SolutionModel(input_dim, num_classes).to(device)
        
        params = sum(p.numel() for p in model.parameters() if p.requires_grad)
        if params > 5000000:
            hidden_adj = int(math.sqrt(5000000 / (input_dim + num_classes + 2000)))
            model = nn.Sequential(
                nn.Linear(input_dim, hidden_adj),
                nn.BatchNorm1d(hidden_adj),
                nn.GELU(),
                nn.Dropout(0.3),
                nn.Linear(hidden_adj, hidden_adj),
                nn.BatchNorm1d(hidden_adj),
                nn.GELU(),
                nn.Dropout(0.3),
                nn.Linear(hidden_adj, num_classes)
            ).to(device)
        
        optimizer = AdamW(model.parameters(), lr=0.001, weight_decay=0.01)
        scheduler = CosineAnnealingLR(optimizer, T_max=50)
        criterion = nn.CrossEntropyLoss()
        
        best_acc = 0
        best_model_state = None
        patience = 10
        patience_counter = 0
        
        for epoch in range(100):
            model.train()
            total_loss = 0
            for batch_idx, (data, target) in enumerate(train_loader):
                data, target = data.to(device), target.to(device)
                optimizer.zero_grad()
                output = model(data)
                loss = criterion(output, target)
                loss.backward()
                optimizer.step()
                total_loss += loss.item()
            
            scheduler.step()
            
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
            
            val_acc = correct / total
            
            if val_acc > best_acc:
                best_acc = val_acc
                best_model_state = {k: v.cpu().clone() for k, v in model.state_dict().items()}
                patience_counter = 0
            else:
                patience_counter += 1
            
            if patience_counter >= patience:
                break
        
        if best_model_state:
            model.load_state_dict(best_model_state)
        
        return model.cpu()