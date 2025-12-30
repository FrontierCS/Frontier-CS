import torch
import torch.nn as nn
import torch.optim as optim

class Solution:
    def solve(self, train_loader, val_loader, metadata: dict = None) -> torch.nn.Module:
        metadata = metadata or {}
        input_dim = metadata.get("input_dim", 384)
        num_classes = metadata.get("num_classes", 128)
        device = metadata.get("device", "cpu")
        
        # Architecture Design:
        # We need to maximize parameter usage within 500,000 limit.
        # Input Dim: 384
        # Hidden Dim: 384
        # Structure: InputBN -> Stem(Lin) -> ResBlock -> ResBlock -> HeadBN -> Head(Lin)
        
        # Parameter Count Calculation (assuming input_dim=384):
        # 1. InputBN(384): 2 * 384 = 768 params
        # 2. Stem Linear(384, 384): 384 * 384 + 384 = 147,840 params
        # 3. ResBlock 1:
        #    - BN(384): 768
        #    - Linear(384, 384): 147,840
        #    - Total Block: 148,608 params
        # 4. ResBlock 2: 148,608 params
        # 5. HeadBN(384): 768 params
        # 6. Head Linear(384, 128): 384 * 128 + 128 = 49,280 params
        
        # Total Sum: 768 + 147840 + 148608 + 148608 + 768 + 49280
        # = 495,872 parameters.
        # This is strictly < 500,000.
        
        class ResBlock(nn.Module):
            def __init__(self, dim, dropout=0.25):
                super().__init__()
                self.norm = nn.BatchNorm1d(dim)
                self.linear = nn.Linear(dim, dim)
                self.act = nn.GELU()
                self.drop = nn.Dropout(dropout)

            def forward(self, x):
                # Residual connection
                identity = x
                out = self.norm(x)
                out = self.linear(out)
                out = self.act(out)
                out = self.drop(out)
                return identity + out

        class ParamEfficientNet(nn.Module):
            def __init__(self, in_dim, n_classes):
                super().__init__()
                self.input_norm = nn.BatchNorm1d(in_dim)
                
                # Stem
                self.stem = nn.Linear(in_dim, 384)
                self.stem_act = nn.GELU()
                self.stem_drop = nn.Dropout(0.25)
                
                # Residual Layers
                self.layer1 = ResBlock(384)
                self.layer2 = ResBlock(384)
                
                # Head
                self.head_norm = nn.BatchNorm1d(384)
                self.head = nn.Linear(384, n_classes)

            def forward(self, x):
                x = self.input_norm(x)
                x = self.stem(x)
                x = self.stem_act(x)
                x = self.stem_drop(x)
                
                x = self.layer1(x)
                x = self.layer2(x)
                
                x = self.head_norm(x)
                x = self.head(x)
                return x

        # Initialize model
        model = ParamEfficientNet(input_dim, num_classes).to(device)
        
        # Training Hyperparameters
        epochs = 80
        # Use a high weight decay for the small dataset (2048 samples)
        optimizer = optim.AdamW(model.parameters(), lr=0.002, weight_decay=0.02)
        
        # OneCycleLR for fast convergence
        steps_per_epoch = len(train_loader)
        scheduler = optim.lr_scheduler.OneCycleLR(
            optimizer, 
            max_lr=0.002, 
            epochs=epochs, 
            steps_per_epoch=steps_per_epoch,
            pct_start=0.2
        )
        
        # Label smoothing helps with synthetic/noisy data
        criterion = nn.CrossEntropyLoss(label_smoothing=0.1)
        
        best_acc = 0.0
        best_weights = None
        
        # Training Loop
        for epoch in range(epochs):
            model.train()
            for inputs, targets in train_loader:
                inputs, targets = inputs.to(device), targets.to(device)
                
                # Input noise injection for regularization
                # Stop noise in the last few epochs to refine features
                if epoch < epochs - 5:
                    noise = torch.randn_like(inputs) * 0.05
                    inputs = inputs + noise
                
                optimizer.zero_grad()
                outputs = model(inputs)
                loss = criterion(outputs, targets)
                loss.backward()
                optimizer.step()
                scheduler.step()
            
            # Validation
            # Validate in second half of training to save time
            if epoch >= epochs // 2 and epoch % 2 == 0:
                model.eval()
                correct = 0
                total = 0
                with torch.no_grad():
                    for inputs, targets in val_loader:
                        inputs, targets = inputs.to(device), targets.to(device)
                        outputs = model(inputs)
                        _, preds = outputs.max(1)
                        correct += (preds == targets).sum().item()
                        total += targets.size(0)
                
                acc = correct / total
                if acc > best_acc:
                    best_acc = acc
                    best_weights = model.state_dict()
        
        # Return best model found
        if best_weights is not None:
            model.load_state_dict(best_weights)
            
        return model