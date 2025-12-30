import torch
import torch.nn as nn
import torch.optim as optim
import numpy as np
import copy

class Solution:
    def solve(self, train_loader, val_loader, metadata: dict = None) -> torch.nn.Module:
        """
        Train a model for the ImageNet Pareto Optimization - 5M Variant.
        Architecture uses a deep Residual MLP with ~4.75M parameters.
        """
        # 1. Setup & Metadata
        input_dim = metadata.get("input_dim", 384)
        num_classes = metadata.get("num_classes", 128)
        device = metadata.get("device", "cpu")
        
        # 2. Configuration (tuned for 5M budget and small dataset)
        config = {
            'hidden_dim': 512,       # Width 512 fits ~17 deep blocks
            'num_blocks': 17,        # Max depth under 5M constraint
            'dropout': 0.15,         # Regularization for small N=2048 dataset
            'lr': 1e-3,
            'weight_decay': 2e-2,
            'epochs': 120,           # Sufficient for convergence with Mixup
            'mixup_prob': 0.7,       # High mixup probability for regularization
            'mixup_alpha': 0.4
        }

        # 3. Model Architecture
        class ResBlock(nn.Module):
            """Pre-activation Residual Block with LayerNorm"""
            def __init__(self, dim, dropout):
                super().__init__()
                self.ln = nn.LayerNorm(dim)
                self.fc = nn.Linear(dim, dim)
                self.act = nn.GELU()
                self.drop = nn.Dropout(dropout)

            def forward(self, x):
                # x + Dropout(GELU(Linear(LN(x))))
                return x + self.drop(self.act(self.fc(self.ln(x))))

        class ParetoNet(nn.Module):
            def __init__(self, in_dim, out_dim, hidden_dim, num_blocks, dropout):
                super().__init__()
                # Input projection
                self.input_norm = nn.LayerNorm(in_dim)
                self.embedding = nn.Linear(in_dim, hidden_dim)
                
                # Deep Residual Backbone
                layers = []
                for _ in range(num_blocks):
                    layers.append(ResBlock(hidden_dim, dropout))
                self.blocks = nn.Sequential(*layers)
                
                # Output Head
                self.final_norm = nn.LayerNorm(hidden_dim)
                self.head = nn.Linear(hidden_dim, out_dim)
                
                self._init_weights()

            def _init_weights(self):
                for m in self.modules():
                    if isinstance(m, nn.Linear):
                        nn.init.orthogonal_(m.weight)
                        if m.bias is not None:
                            nn.init.zeros_(m.bias)

            def forward(self, x):
                x = self.input_norm(x)
                x = self.embedding(x)
                x = self.blocks(x)
                x = self.final_norm(x)
                return self.head(x)

        # 4. Instantiate Model
        model = ParetoNet(
            input_dim, 
            num_classes, 
            config['hidden_dim'], 
            config['num_blocks'], 
            config['dropout']
        ).to(device)

        # Parameter safety check
        # Calculation:
        # Emb: 384*512 + 512 = 197,120
        # Blocks: 17 * (512*512 + 512 + 2*512(LN)) = 17 * 263,680 = 4,482,560
        # Head: 512*128 + 128 + 2*512(LN) = 66,688
        # Total: ~4.75M < 5.00M
        
        # 5. Optimization
        optimizer = optim.AdamW(
            model.parameters(), 
            lr=config['lr'], 
            weight_decay=config['weight_decay']
        )
        scheduler = optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=config['epochs'])
        criterion = nn.CrossEntropyLoss(label_smoothing=0.1)

        # 6. Training Loop
        best_acc = 0.0
        best_state = copy.deepcopy(model.state_dict())
        
        for epoch in range(config['epochs']):
            model.train()
            
            for inputs, targets in train_loader:
                inputs, targets = inputs.to(device), targets.to(device)
                
                # Mixup Augmentation
                if inputs.size(0) > 1 and np.random.random() < config['mixup_prob']:
                    lam = np.random.beta(config['mixup_alpha'], config['mixup_alpha'])
                    index = torch.randperm(inputs.size(0)).to(device)
                    
                    mixed_inputs = lam * inputs + (1 - lam) * inputs[index]
                    target_a, target_b = targets, targets[index]
                    
                    outputs = model(mixed_inputs)
                    loss = lam * criterion(outputs, target_a) + (1 - lam) * criterion(outputs, target_b)
                else:
                    outputs = model(inputs)
                    loss = criterion(outputs, targets)
                
                optimizer.zero_grad()
                loss.backward()
                optimizer.step()
            
            scheduler.step()
            
            # Validation logic to keep best checkpoint
            # Evaluating every epoch since training is fast (small data)
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
            # Save if strictly better or first epoch
            if val_acc > best_acc:
                best_acc = val_acc
                best_state = copy.deepcopy(model.state_dict())

        # Return best performing model
        model.load_state_dict(best_state)
        return model