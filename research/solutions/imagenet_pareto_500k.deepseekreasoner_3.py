import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.optim import AdamW
from torch.optim.lr_scheduler import CosineAnnealingLR
import math

class EfficientMLP(nn.Module):
    def __init__(self, input_dim=384, num_classes=128, param_limit=500000):
        super().__init__()
        self.input_dim = input_dim
        self.num_classes = num_classes
        
        # Carefully designed architecture to maximize capacity within budget
        # Using residual connections and bottleneck layers
        hidden1 = 512
        hidden2 = 512
        hidden3 = 384
        hidden4 = 256
        
        # Calculate current parameters
        params = 0
        params += input_dim * hidden1 + hidden1  # fc1
        params += hidden1 * hidden2 + hidden2    # fc2
        params += hidden2 * hidden3 + hidden3    # fc3
        params += hidden3 * hidden4 + hidden4    # fc4
        params += hidden4 * num_classes + num_classes  # fc_out
        
        # Add batch norm params (2 per feature)
        params += 4 * hidden1 * 2 + 4 * hidden2 * 2 + 4 * hidden3 * 2 + 4 * hidden4 * 2
        
        # If we're under budget, we can increase capacity
        if params < param_limit:
            # Increase hidden dimensions proportionally
            scale = math.sqrt(param_limit / params)
            hidden1 = min(768, int(hidden1 * scale))
            hidden2 = min(768, int(hidden2 * scale))
            hidden3 = min(512, int(hidden3 * scale))
            hidden4 = min(384, int(hidden4 * scale))
        
        # Main layers with residual connections
        self.fc1 = nn.Linear(input_dim, hidden1)
        self.bn1 = nn.BatchNorm1d(hidden1)
        
        self.fc2 = nn.Linear(hidden1, hidden2)
        self.bn2 = nn.BatchNorm1d(hidden2)
        
        self.fc3 = nn.Linear(hidden2, hidden3)
        self.bn3 = nn.BatchNorm1d(hidden3)
        
        self.fc4 = nn.Linear(hidden3, hidden4)
        self.bn4 = nn.BatchNorm1d(hidden4)
        
        self.fc_out = nn.Linear(hidden4, num_classes)
        
        # Dropout for regularization
        self.dropout = nn.Dropout(0.3)
        
        # Initialize weights properly
        self._initialize_weights()
    
    def _initialize_weights(self):
        for m in self.modules():
            if isinstance(m, nn.Linear):
                nn.init.kaiming_normal_(m.weight, mode='fan_out', nonlinearity='relu')
                if m.bias is not None:
                    nn.init.constant_(m.bias, 0)
            elif isinstance(m, nn.BatchNorm1d):
                nn.init.constant_(m.weight, 1)
                nn.init.constant_(m.bias, 0)
    
    def forward(self, x):
        # Residual block 1
        identity = x
        if x.shape[1] != self.fc1.out_features:
            identity = self.fc1(x)  # Project residual
        
        out = F.relu(self.bn1(self.fc1(x)))
        out = self.dropout(out)
        
        # Residual block 2
        out = F.relu(self.bn2(self.fc2(out) + identity))
        out = self.dropout(out)
        
        # Continue through network
        out = F.relu(self.bn3(self.fc3(out)))
        out = self.dropout(out)
        
        out = F.relu(self.bn4(self.fc4(out)))
        out = self.dropout(out)
        
        out = self.fc_out(out)
        return out

class Solution:
    def solve(self, train_loader, val_loader, metadata: dict = None) -> torch.nn.Module:
        # Extract metadata
        num_classes = metadata["num_classes"]
        input_dim = metadata["input_dim"]
        param_limit = metadata["param_limit"]
        device = metadata["device"]
        
        # Create model with parameter constraint
        model = EfficientMLP(input_dim=input_dim, num_classes=num_classes, param_limit=param_limit)
        model.to(device)
        
        # Verify parameter count
        total_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
        if total_params > param_limit:
            # If somehow over limit, reduce capacity
            model = nn.Sequential(
                nn.Linear(input_dim, 512),
                nn.BatchNorm1d(512),
                nn.ReLU(),
                nn.Dropout(0.3),
                nn.Linear(512, 256),
                nn.BatchNorm1d(256),
                nn.ReLU(),
                nn.Dropout(0.3),
                nn.Linear(256, num_classes)
            )
            model.to(device)
        
        # Training setup
        criterion = nn.CrossEntropyLoss()
        optimizer = AdamW(model.parameters(), lr=0.001, weight_decay=0.01)
        scheduler = CosineAnnealingLR(optimizer, T_max=100, eta_min=1e-5)
        
        # Early stopping
        best_val_acc = 0
        best_model_state = None
        patience = 20
        patience_counter = 0
        
        # Training loop
        num_epochs = 200
        for epoch in range(num_epochs):
            # Training phase
            model.train()
            train_loss = 0
            train_correct = 0
            train_total = 0
            
            for batch_idx, (inputs, targets) in enumerate(train_loader):
                inputs, targets = inputs.to(device), targets.to(device)
                
                optimizer.zero_grad()
                outputs = model(inputs)
                loss = criterion(outputs, targets)
                loss.backward()
                
                # Gradient clipping
                torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
                
                optimizer.step()
                
                train_loss += loss.item()
                _, predicted = outputs.max(1)
                train_total += targets.size(0)
                train_correct += predicted.eq(targets).sum().item()
            
            scheduler.step()
            
            # Validation phase
            model.eval()
            val_correct = 0
            val_total = 0
            
            with torch.no_grad():
                for inputs, targets in val_loader:
                    inputs, targets = inputs.to(device), targets.to(device)
                    outputs = model(inputs)
                    _, predicted = outputs.max(1)
                    val_total += targets.size(0)
                    val_correct += predicted.eq(targets).sum().item()
            
            val_acc = val_correct / val_total
            
            # Early stopping check
            if val_acc > best_val_acc:
                best_val_acc = val_acc
                best_model_state = model.state_dict().copy()
                patience_counter = 0
            else:
                patience_counter += 1
            
            if patience_counter >= patience:
                break
        
        # Load best model
        if best_model_state is not None:
            model.load_state_dict(best_model_state)
        
        # Final training on combined data for a few more epochs
        model.train()
        combined_loader = torch.utils.data.ConcatDataset([
            train_loader.dataset, 
            val_loader.dataset
        ])
        combined_loader = torch.utils.data.DataLoader(
            combined_loader, 
            batch_size=train_loader.batch_size,
            shuffle=True
        )
        
        # Short fine-tuning on combined data
        fine_tune_epochs = 20
        optimizer = AdamW(model.parameters(), lr=0.0001)
        
        for _ in range(fine_tune_epochs):
            for inputs, targets in combined_loader:
                inputs, targets = inputs.to(device), targets.to(device)
                optimizer.zero_grad()
                outputs = model(inputs)
                loss = criterion(outputs, targets)
                loss.backward()
                optimizer.step()
        
        model.eval()
        return model
