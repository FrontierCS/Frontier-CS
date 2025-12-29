import torch
import torch.nn as nn
import torch.optim as optim
import copy

class SubModel(nn.Module):
    def __init__(self, input_dim, num_classes):
        super().__init__()
        # Architecture designed to be parameter efficient
        # Width 248 allows for ~315k parameters per model
        # 3 models in ensemble = ~945k parameters (< 1M limit)
        self.width = 248
        
        # Initial batch norm to handle unnormalized inputs
        self.input_bn = nn.BatchNorm1d(input_dim)
        
        # Projection to hidden dimension
        self.proj = nn.Sequential(
            nn.Linear(input_dim, self.width),
            nn.BatchNorm1d(self.width),
            nn.SiLU()
        )
        
        # Residual blocks for depth
        self.layers = nn.ModuleList([
            nn.Sequential(
                nn.Linear(self.width, self.width),
                nn.BatchNorm1d(self.width),
                nn.SiLU(),
                nn.Dropout(0.25)
            ) for _ in range(3)
        ])
        
        # Classification head
        self.head = nn.Linear(self.width, num_classes)

    def forward(self, x):
        x = self.input_bn(x)
        x = self.proj(x)
        for layer in self.layers:
            # Residual connection
            x = x + layer(x)
        return self.head(x)

class EnsembleModel(nn.Module):
    def __init__(self, models):
        super().__init__()
        self.models = nn.ModuleList(models)
    
    def forward(self, x):
        # Average probabilities across ensemble members
        # SubModels return logits, so we apply softmax first
        probs = [torch.softmax(m(x), dim=1) for m in self.models]
        avg_prob = torch.stack(probs).mean(dim=0)
        return avg_prob

class Solution:
    def solve(self, train_loader, val_loader, metadata: dict = None) -> torch.nn.Module:
        """
        Train a 3-model ensemble within the 1M parameter budget.
        """
        # Extract metadata
        input_dim = metadata.get("input_dim", 384)
        num_classes = metadata.get("num_classes", 128)
        device_str = metadata.get("device", "cpu")
        device = torch.device(device_str)
        
        # Configuration
        # We train 3 models. Total params will be ~946k, well within 1M limit.
        num_models = 3
        epochs = 45 
        
        best_models = []
        
        for i in range(num_models):
            # Initialize model
            model = SubModel(input_dim, num_classes).to(device)
            
            # Optimizer settings with weight decay for regularization
            optimizer = optim.AdamW(model.parameters(), lr=0.001, weight_decay=0.02)
            scheduler = optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=epochs)
            # Label smoothing helps with generalization on synthetic data
            criterion = nn.CrossEntropyLoss(label_smoothing=0.1)
            
            best_val_acc = -1.0
            best_model_state = copy.deepcopy(model.state_dict())
            
            for epoch in range(epochs):
                # Training phase
                model.train()
                for inputs, targets in train_loader:
                    inputs, targets = inputs.to(device), targets.to(device)
                    optimizer.zero_grad()
                    outputs = model(inputs)
                    loss = criterion(outputs, targets)
                    loss.backward()
                    optimizer.step()
                
                scheduler.step()
                
                # Validation phase
                model.eval()
                correct = 0
                total = 0
                with torch.no_grad():
                    for inputs, targets in val_loader:
                        inputs, targets = inputs.to(device), targets.to(device)
                        outputs = model(inputs)
                        _, preds = outputs.max(1)
                        correct += preds.eq(targets).sum().item()
                        total += targets.size(0)
                
                # Save best model based on validation accuracy
                if total > 0:
                    val_acc = correct / total
                    if val_acc >= best_val_acc:
                        best_val_acc = val_acc
                        best_model_state = copy.deepcopy(model.state_dict())
            
            # Retrieve best state for this ensemble member
            model.load_state_dict(best_model_state)
            model.cpu() # Move to CPU to assemble later
            best_models.append(model)
            
        # Create and return the ensemble
        ensemble = EnsembleModel(best_models)
        ensemble.to(device)
        
        # Verify parameter count (internal check)
        # param_count = sum(p.numel() for p in ensemble.parameters() if p.requires_grad)
        # assert param_count <= 1000000
        
        return ensemble