import torch
import torch.nn as nn
import torch.optim as optim
import numpy as np

class ResBlock(nn.Module):
    def __init__(self, dim, dropout=0.25):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(dim, dim, bias=False),
            nn.BatchNorm1d(dim),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(dim, dim, bias=False),
            nn.BatchNorm1d(dim),
            nn.GELU(),
            nn.Dropout(dropout)
        )
        
    def forward(self, x):
        return x + self.net(x)

class ParetoModel(nn.Module):
    def __init__(self, input_dim, num_classes, hidden_dim=525):
        super().__init__()
        self.bn_input = nn.BatchNorm1d(input_dim)
        
        self.proj_in = nn.Sequential(
            nn.Linear(input_dim, hidden_dim, bias=False),
            nn.BatchNorm1d(hidden_dim),
            nn.GELU(),
            nn.Dropout(0.1)
        )
        
        self.blocks = nn.Sequential(
            ResBlock(hidden_dim),
            ResBlock(hidden_dim),
            ResBlock(hidden_dim),
            ResBlock(hidden_dim)
        )
        
        self.proj_out = nn.Linear(hidden_dim, num_classes)
        
    def forward(self, x):
        x = self.bn_input(x)
        x = self.proj_in(x)
        x = self.blocks(x)
        return self.proj_out(x)

class Solution:
    def solve(self, train_loader, val_loader, metadata: dict = None) -> torch.nn.Module:
        input_dim = metadata.get("input_dim", 384)
        num_classes = metadata.get("num_classes", 128)
        device = metadata.get("device", "cpu")
        
        # Set seeds for reproducibility
        torch.manual_seed(42)
        np.random.seed(42)
        
        # Initialize model with calculated hidden dimension to stay under 2.5M
        # Calculation:
        # Input BN: 384*2 = 768
        # Proj In: 384*525 + 525*2 (BN) = 202,650
        # 4 Blocks (525 dim): 4 * (2*(525*525 + 1050)) = 4 * 553350 = 2,213,400
        # Proj Out: 525*128 + 128 = 67,328
        # Total: ~2.484M < 2.5M
        hidden_dim = 525
        model = ParetoModel(input_dim, num_classes, hidden_dim=hidden_dim)
        model = model.to(device)
        
        # Safety check for parameter count
        param_count = sum(p.numel() for p in model.parameters() if p.requires_grad)
        if param_count > 2500000:
            # Fallback to 512 if somehow over limit (e.g. diff internal impl)
            model = ParetoModel(input_dim, num_classes, hidden_dim=512)
            model = model.to(device)

        # Training Hyperparameters
        epochs = 70
        lr = 0.001
        weight_decay = 1e-3
        
        optimizer = optim.AdamW(model.parameters(), lr=lr, weight_decay=weight_decay)
        scheduler = optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=epochs)
        criterion = nn.CrossEntropyLoss()
        
        best_acc = -1.0
        best_state = None
        
        for epoch in range(epochs):
            model.train()
            for inputs, targets in train_loader:
                inputs, targets = inputs.to(device), targets.to(device)
                
                # Mixup augmentation
                inputs, targets_a, targets_b, lam = self.mixup_data(inputs, targets, alpha=0.4, device=device)
                
                optimizer.zero_grad()
                outputs = model(inputs)
                loss = self.mixup_criterion(criterion, outputs, targets_a, targets_b, lam)
                
                loss.backward()
                optimizer.step()
            
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
                    total += targets.size(0)
            
            val_acc = correct / total
            if val_acc > best_acc:
                best_acc = val_acc
                best_state = {k: v.cpu() for k, v in model.state_dict().items()}
        
        # Load best performing model
        if best_state is not None:
            model.load_state_dict(best_state)
            
        return model

    def mixup_data(self, x, y, alpha=1.0, device='cpu'):
        if alpha > 0:
            lam = np.random.beta(alpha, alpha)
        else:
            lam = 1
        batch_size = x.size(0)
        index = torch.randperm(batch_size).to(device)
        mixed_x = lam * x + (1 - lam) * x[index, :]
        y_a, y_b = y, y[index]
        return mixed_x, y_a, y_b, lam

    def mixup_criterion(self, criterion, pred, y_a, y_b, lam):
        return lam * criterion(pred, y_a) + (1 - lam) * criterion(pred, y_b)
