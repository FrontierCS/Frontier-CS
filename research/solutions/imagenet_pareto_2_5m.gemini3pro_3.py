import torch
import torch.nn as nn
import torch.optim as optim
import numpy as np
import copy

class Solution:
    def solve(self, train_loader, val_loader, metadata: dict = None) -> torch.nn.Module:
        """
        Train a model and return it.
        """
        if metadata is None:
            metadata = {}
            
        input_dim = metadata.get("input_dim", 384)
        num_classes = metadata.get("num_classes", 128)
        device = metadata.get("device", "cpu")
        
        # ---------------------------------------------------------------------
        # Architecture Design
        # Target: < 2,500,000 parameters.
        # Design: Wide MLP with Residual Connections (ResMLP).
        # Width: 960 neurons.
        #
        # Parameter Breakdown:
        # 1. Stem (384 -> 960): 384*960 + 960 + BN(2*960) = ~371k
        # 2. Block1 (960 -> 960): 960*960 + 960 + BN(2*960) = ~924k
        # 3. Block2 (960 -> 960): 960*960 + 960 + BN(2*960) = ~924k
        # 4. Head (960 -> 128): 960*128 + 128 = ~123k
        # Total Sum: ~2.34M.
        # Margin: ~150k parameters safe from 2.5M limit.
        # ---------------------------------------------------------------------
        
        class ResMLP(nn.Module):
            def __init__(self, in_features, num_classes, hidden_dim=960, dropout=0.3):
                super().__init__()
                self.stem = nn.Sequential(
                    nn.Linear(in_features, hidden_dim),
                    nn.BatchNorm1d(hidden_dim),
                    nn.ReLU(inplace=True),
                    nn.Dropout(dropout)
                )
                
                self.layer1 = nn.Sequential(
                    nn.Linear(hidden_dim, hidden_dim),
                    nn.BatchNorm1d(hidden_dim),
                    nn.ReLU(inplace=True),
                    nn.Dropout(dropout)
                )
                
                self.layer2 = nn.Sequential(
                    nn.Linear(hidden_dim, hidden_dim),
                    nn.BatchNorm1d(hidden_dim),
                    nn.ReLU(inplace=True),
                    nn.Dropout(dropout)
                )
                
                self.head = nn.Linear(hidden_dim, num_classes)
                
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
                x = self.stem(x)
                x = x + self.layer1(x) # Residual connection
                x = x + self.layer2(x) # Residual connection
                x = self.head(x)
                return x

        # Initialize model
        model = ResMLP(input_dim, num_classes).to(device)
        
        # Training Hyperparameters
        # High epochs since dataset is small (2048 samples) and we use CPU
        epochs = 70
        lr = 1e-3
        weight_decay = 1e-3
        
        optimizer = optim.AdamW(model.parameters(), lr=lr, weight_decay=weight_decay)
        criterion = nn.CrossEntropyLoss(label_smoothing=0.1)
        
        # Scheduler for convergence
        scheduler = optim.lr_scheduler.OneCycleLR(
            optimizer,
            max_lr=lr,
            epochs=epochs,
            steps_per_epoch=len(train_loader),
            pct_start=0.3,
            div_factor=25.0,
            final_div_factor=1000.0
        )
        
        # Variables to track best model
        best_acc = 0.0
        best_model_wts = copy.deepcopy(model.state_dict())
        
        # Mixup augmentation helper
        def mixup_data(x, y, alpha=0.4):
            if alpha > 0:
                lam = np.random.beta(alpha, alpha)
            else:
                lam = 1
            batch_size = x.size(0)
            index = torch.randperm(batch_size).to(device)
            mixed_x = lam * x + (1 - lam) * x[index, :]
            y_a, y_b = y, y[index]
            return mixed_x, y_a, y_b, lam

        def mixup_criterion(pred, y_a, y_b, lam):
            return lam * criterion(pred, y_a) + (1 - lam) * criterion(pred, y_b)
        
        # Training Loop
        for epoch in range(epochs):
            model.train()
            for inputs, targets in train_loader:
                inputs, targets = inputs.to(device), targets.to(device)
                
                # Apply Mixup
                inputs, targets_a, targets_b, lam = mixup_data(inputs, targets)
                
                optimizer.zero_grad()
                outputs = model(inputs)
                loss = mixup_criterion(outputs, targets_a, targets_b, lam)
                
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
                    _, preds = torch.max(outputs, 1)
                    total += targets.size(0)
                    correct += (preds == targets).sum().item()
            
            val_acc = correct / total
            
            # Save best model
            if val_acc > best_acc:
                best_acc = val_acc
                best_model_wts = copy.deepcopy(model.state_dict())
        
        # Load best weights before returning
        model.load_state_dict(best_model_wts)
        return model