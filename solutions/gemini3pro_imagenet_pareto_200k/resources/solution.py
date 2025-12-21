import torch
import torch.nn as nn
import torch.optim as optim

class ResidualBlock(nn.Module):
    def __init__(self, in_features, out_features, dropout=0.25):
        super().__init__()
        self.linear = nn.Linear(in_features, out_features)
        self.bn = nn.BatchNorm1d(out_features)
        self.act = nn.SiLU()
        self.dropout = nn.Dropout(dropout)
        self.has_skip = (in_features == out_features)
        
    def forward(self, x):
        out = self.linear(x)
        out = self.bn(out)
        out = self.act(out)
        out = self.dropout(out)
        if self.has_skip:
            return out + x
        return out

class ParameterConstrainedModel(nn.Module):
    def __init__(self, input_dim, num_classes):
        super().__init__()
        # Architecture designed to maximize capacity within 200,000 parameter budget
        # Calculation assumes input_dim=384, num_classes=128
        
        # Normalize input features
        self.input_bn = nn.BatchNorm1d(input_dim)
        
        # Layer 1: 384 -> 256
        # Params: 384*256 + 256 (bias) + 256*2 (BN) = 99,072
        self.l1 = nn.Sequential(
            nn.Linear(input_dim, 256),
            nn.BatchNorm1d(256),
            nn.SiLU(),
            nn.Dropout(0.25)
        )
        
        # Layer 2: 256 -> 160
        # Params: 256*160 + 160 + 160*2 = 41,440
        self.l2 = nn.Sequential(
            nn.Linear(256, 160),
            nn.BatchNorm1d(160),
            nn.SiLU(),
            nn.Dropout(0.25)
        )
        
        # Layer 3: 160 -> 128
        # Params: 160*128 + 128 + 128*2 = 20,864
        self.l3 = nn.Sequential(
            nn.Linear(160, 128),
            nn.BatchNorm1d(128),
            nn.SiLU(),
            nn.Dropout(0.25)
        )
        
        # Layer 4: 128 -> 128 (Residual)
        # Params: 128*128 + 128 + 128*2 = 16,768
        self.l4 = ResidualBlock(128, 128, dropout=0.25)
        
        # Output Head: 128 -> 128
        # Params: 128*128 + 128 = 16,512
        self.head = nn.Linear(128, num_classes)
        
        # Total Estimated: ~195,424 parameters (Safe under 200k limit)

    def forward(self, x):
        x = self.input_bn(x)
        x = self.l1(x)
        x = self.l2(x)
        x = self.l3(x)
        x = self.l4(x)
        x = self.head(x)
        return x

class Solution:
    def solve(self, train_loader, val_loader, metadata: dict = None) -> torch.nn.Module:
        """
        Train a model and return it.
        """
        device = metadata.get("device", "cpu")
        input_dim = metadata.get("input_dim", 384)
        num_classes = metadata.get("num_classes", 128)
        
        # Instantiate the model
        model = ParameterConstrainedModel(input_dim, num_classes)
        model = model.to(device)
        
        # Training Hyperparameters
        epochs = 45
        lr = 0.002
        weight_decay = 0.02
        
        # Optimizer and Scheduler
        optimizer = optim.AdamW(model.parameters(), lr=lr, weight_decay=weight_decay)
        
        # OneCycleLR for efficient training within limited epochs
        scheduler = optim.lr_scheduler.OneCycleLR(
            optimizer,
            max_lr=lr,
            epochs=epochs,
            steps_per_epoch=len(train_loader),
            pct_start=0.3,
            div_factor=25.0,
            final_div_factor=1000.0
        )
        
        # Loss function with label smoothing for regularization
        criterion = nn.CrossEntropyLoss(label_smoothing=0.1)
        
        best_acc = 0.0
        best_model_state = None
        
        # Training Loop
        for epoch in range(epochs):
            model.train()
            for inputs, targets in train_loader:
                inputs, targets = inputs.to(device), targets.to(device)
                
                # Data Augmentation: Feature noise injection
                # Helps prevent overfitting on small synthetic dataset
                if epoch < int(epochs * 0.8):
                    noise = torch.randn_like(inputs) * 0.05
                    inputs = inputs + noise
                
                optimizer.zero_grad()
                outputs = model(inputs)
                loss = criterion(outputs, targets)
                loss.backward()
                
                # Gradient Clipping
                nn.utils.clip_grad_norm_(model.parameters(), 1.0)
                
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
            
            # Save best state
            if val_acc >= best_acc:
                best_acc = val_acc
                best_model_state = {k: v.cpu() for k, v in model.state_dict().items()}
        
        # Restore best model
        if best_model_state is not None:
            model.load_state_dict(best_model_state)
            
        return model
