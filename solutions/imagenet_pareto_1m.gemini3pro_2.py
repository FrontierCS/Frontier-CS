import torch
import torch.nn as nn
import torch.optim as optim
import copy
import math

class ResBlock(nn.Module):
    def __init__(self, dim, dropout):
        super().__init__()
        self.block = nn.Sequential(
            nn.Linear(dim, dim),
            nn.BatchNorm1d(dim),
            nn.SiLU(),
            nn.Dropout(dropout)
        )

    def forward(self, x):
        return x + self.block(x)

class SingleModel(nn.Module):
    def __init__(self, input_dim, hidden_dim, num_classes, dropout):
        super().__init__()
        self.stem = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.BatchNorm1d(hidden_dim),
            nn.SiLU(),
            nn.Dropout(dropout)
        )
        self.res1 = ResBlock(hidden_dim, dropout)
        self.res2 = ResBlock(hidden_dim, dropout)
        self.head = nn.Linear(hidden_dim, num_classes)

    def forward(self, x):
        x = self.stem(x)
        x = self.res1(x)
        x = self.res2(x)
        return self.head(x)

class EnsembleModel(nn.Module):
    def __init__(self, models):
        super().__init__()
        self.models = nn.ModuleList(models)

    def forward(self, x):
        outputs = [m(x) for m in self.models]
        return torch.stack(outputs).mean(dim=0)

class Solution:
    def solve(self, train_loader, val_loader, metadata: dict = None) -> torch.nn.Module:
        """
        Train a model and return it.
        """
        input_dim = metadata.get("input_dim", 384)
        num_classes = metadata.get("num_classes", 128)
        param_limit = metadata.get("param_limit", 1000000)
        device = metadata.get("device", "cpu")
        
        # Configuration
        dropout = 0.3
        num_epochs = 45
        num_models = 2
        
        # Dynamic architecture scaling to fit budget
        # We aim to fit num_models within param_limit with a safety margin
        # Param count approximation for SingleModel:
        # 1. Stem Linear: 384*H + H
        # 2. Res1 Linear: H*H + H
        # 3. Res2 Linear: H*H + H
        # 4. Head Linear: H*128 + 128
        # 5. BN params (3 layers): 3 * 2*H
        # Total ~= 2H^2 + (384 + 128 + 3 + 3 + 6)H + 128
        # Total ~= 2H^2 + 524H
        
        target_per_model = (param_limit * 0.98) / num_models # 2% safety buffer
        
        # Solving 2H^2 + 524H - target = 0
        a = 2
        b = 524
        c = -target_per_model
        h_approx = (-b + math.sqrt(b**2 - 4*a*c)) / (2*a)
        hidden_dim = int(h_approx)
        
        models = []
        seeds = [42, 101, 2024, 7][:num_models]
        
        for i, seed in enumerate(seeds):
            torch.manual_seed(seed)
            model = SingleModel(input_dim, hidden_dim, num_classes, dropout).to(device)
            
            # Verify parameter constraint on first instantiation
            if i == 0:
                current_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
                if current_params * num_models > param_limit:
                    # Reduce hidden dim if calculation was slightly off due to overhead
                    ratio = param_limit / (current_params * num_models)
                    hidden_dim = int(hidden_dim * math.sqrt(ratio) * 0.95)
                    model = SingleModel(input_dim, hidden_dim, num_classes, dropout).to(device)
            
            optimizer = optim.AdamW(model.parameters(), lr=1e-3, weight_decay=1e-2)
            criterion = nn.CrossEntropyLoss(label_smoothing=0.1)
            
            scheduler = optim.lr_scheduler.OneCycleLR(
                optimizer,
                max_lr=1e-3,
                epochs=num_epochs,
                steps_per_epoch=len(train_loader)
            )
            
            best_acc = 0.0
            best_state = copy.deepcopy(model.state_dict())
            
            for epoch in range(num_epochs):
                model.train()
                for inputs, targets in train_loader:
                    inputs, targets = inputs.to(device), targets.to(device)
                    
                    optimizer.zero_grad()
                    outputs = model(inputs)
                    loss = criterion(outputs, targets)
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
                        _, predicted = torch.max(outputs.data, 1)
                        total += targets.size(0)
                        correct += (predicted == targets).sum().item()
                
                acc = correct / total
                if acc > best_acc:
                    best_acc = acc
                    best_state = copy.deepcopy(model.state_dict())
            
            # Restore best model
            model.load_state_dict(best_state)
            models.append(model)
            
        return EnsembleModel(models)
