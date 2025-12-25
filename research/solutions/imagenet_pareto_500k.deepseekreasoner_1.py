import torch
import torch.nn as nn
import torch.optim as optim
from torch.optim.lr_scheduler import ReduceLROnPlateau
import copy
import time

class Solution:
    def solve(self, train_loader, val_loader, metadata: dict = None) -> torch.nn.Module:
        device = metadata.get("device", "cpu")
        input_dim = metadata["input_dim"]
        num_classes = metadata["num_classes"]
        param_limit = metadata["param_limit"]
        
        # Design model architecture within 500K parameters
        # Using depthwise separable convolutions-inspired structure for efficiency
        hidden1 = 512
        hidden2 = 512
        hidden3 = 256
        hidden4 = 256
        hidden5 = 128
        
        model = nn.Sequential(
            nn.Linear(input_dim, hidden1),
            nn.BatchNorm1d(hidden1),
            nn.ReLU(),
            nn.Dropout(0.3),
            
            nn.Linear(hidden1, hidden2),
            nn.BatchNorm1d(hidden2),
            nn.ReLU(),
            nn.Dropout(0.3),
            
            nn.Linear(hidden2, hidden3),
            nn.BatchNorm1d(hidden3),
            nn.ReLU(),
            nn.Dropout(0.2),
            
            nn.Linear(hidden3, hidden4),
            nn.BatchNorm1d(hidden4),
            nn.ReLU(),
            nn.Dropout(0.2),
            
            nn.Linear(hidden4, hidden5),
            nn.BatchNorm1d(hidden5),
            nn.ReLU(),
            nn.Dropout(0.1),
            
            nn.Linear(hidden5, num_classes)
        )
        
        # Verify parameter count
        total_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
        
        # Adjust architecture if needed to stay under limit
        if total_params > param_limit:
            # Reduce dimensions to stay under limit
            hidden1 = 384
            hidden2 = 384
            hidden3 = 256
            hidden4 = 192
            hidden5 = 128
            
            model = nn.Sequential(
                nn.Linear(input_dim, hidden1),
                nn.BatchNorm1d(hidden1),
                nn.ReLU(),
                nn.Dropout(0.3),
                
                nn.Linear(hidden1, hidden2),
                nn.BatchNorm1d(hidden2),
                nn.ReLU(),
                nn.Dropout(0.3),
                
                nn.Linear(hidden2, hidden3),
                nn.BatchNorm1d(hidden3),
                nn.ReLU(),
                nn.Dropout(0.2),
                
                nn.Linear(hidden3, hidden4),
                nn.BatchNorm1d(hidden4),
                nn.ReLU(),
                nn.Dropout(0.2),
                
                nn.Linear(hidden4, hidden5),
                nn.BatchNorm1d(hidden5),
                nn.ReLU(),
                nn.Dropout(0.1),
                
                nn.Linear(hidden5, num_classes)
            )
        
        model = model.to(device)
        
        # Training parameters
        criterion = nn.CrossEntropyLoss()
        optimizer = optim.AdamW(model.parameters(), lr=0.001, weight_decay=1e-4)
        scheduler = ReduceLROnPlateau(optimizer, mode='max', factor=0.5, patience=10, verbose=False)
        
        # Early stopping
        best_val_acc = 0.0
        best_model_state = None
        patience = 20
        patience_counter = 0
        
        num_epochs = 150
        
        for epoch in range(num_epochs):
            # Training
            model.train()
            train_loss = 0.0
            correct = 0
            total = 0
            
            for inputs, targets in train_loader:
                inputs, targets = inputs.to(device), targets.to(device)
                
                optimizer.zero_grad()
                outputs = model(inputs)
                loss = criterion(outputs, targets)
                loss.backward()
                
                # Gradient clipping
                torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
                
                optimizer.step()
                
                train_loss += loss.item()
                _, predicted = outputs.max(1)
                total += targets.size(0)
                correct += predicted.eq(targets).sum().item()
            
            train_acc = 100. * correct / total
            
            # Validation
            model.eval()
            val_loss = 0.0
            correct = 0
            total = 0
            
            with torch.no_grad():
                for inputs, targets in val_loader:
                    inputs, targets = inputs.to(device), targets.to(device)
                    outputs = model(inputs)
                    loss = criterion(outputs, targets)
                    
                    val_loss += loss.item()
                    _, predicted = outputs.max(1)
                    total += targets.size(0)
                    correct += predicted.eq(targets).sum().item()
            
            val_acc = 100. * correct / total
            
            # Update learning rate
            scheduler.step(val_acc)
            
            # Early stopping check
            if val_acc > best_val_acc:
                best_val_acc = val_acc
                best_model_state = copy.deepcopy(model.state_dict())
                patience_counter = 0
            else:
                patience_counter += 1
            
            if patience_counter >= patience:
                break
        
        # Load best model
        if best_model_state is not None:
            model.load_state_dict(best_model_state)
        
        return model
