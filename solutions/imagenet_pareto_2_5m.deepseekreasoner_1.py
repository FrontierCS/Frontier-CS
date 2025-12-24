import torch
import torch.nn as nn
import torch.optim as optim
import torch.nn.functional as F
from torch.optim.lr_scheduler import CosineAnnealingLR, ReduceLROnPlateau
import time
import math

def count_parameters(model):
    return sum(p.numel() for p in model.parameters() if p.requires_grad)

class ResidualBlock(nn.Module):
    def __init__(self, in_dim, out_dim, dropout_rate=0.2, use_bn=True):
        super().__init__()
        self.use_bn = use_bn
        self.dropout_rate = dropout_rate
        
        self.fc1 = nn.Linear(in_dim, out_dim)
        self.fc2 = nn.Linear(out_dim, out_dim)
        
        if use_bn:
            self.bn1 = nn.BatchNorm1d(out_dim)
            self.bn2 = nn.BatchNorm1d(out_dim)
        
        self.dropout = nn.Dropout(dropout_rate)
        
        self.shortcut = nn.Identity()
        if in_dim != out_dim:
            self.shortcut = nn.Sequential(
                nn.Linear(in_dim, out_dim, bias=False),
                nn.BatchNorm1d(out_dim) if use_bn else nn.Identity()
            )
    
    def forward(self, x):
        residual = self.shortcut(x)
        
        out = self.fc1(x)
        if self.use_bn:
            out = self.bn1(out)
        out = F.gelu(out)
        out = self.dropout(out)
        
        out = self.fc2(out)
        if self.use_bn:
            out = self.bn2(out)
        
        out = out + residual
        out = F.gelu(out)
        out = self.dropout(out)
        
        return out

class EfficientMLP(nn.Module):
    def __init__(self, input_dim, num_classes, hidden_dims, dropout_rate=0.3, use_bn=True):
        super().__init__()
        
        layers = []
        current_dim = input_dim
        
        # Input projection
        layers.append(nn.Linear(input_dim, hidden_dims[0]))
        if use_bn:
            layers.append(nn.BatchNorm1d(hidden_dims[0]))
        layers.append(nn.GELU())
        layers.append(nn.Dropout(dropout_rate))
        
        # Residual blocks
        for i in range(len(hidden_dims) - 1):
            layers.append(
                ResidualBlock(hidden_dims[i], hidden_dims[i+1], 
                            dropout_rate=dropout_rate, use_bn=use_bn)
            )
        
        self.features = nn.Sequential(*layers)
        
        # Final classifier
        self.classifier = nn.Sequential(
            nn.Linear(hidden_dims[-1], hidden_dims[-1] // 2),
            nn.BatchNorm1d(hidden_dims[-1] // 2) if use_bn else nn.Identity(),
            nn.GELU(),
            nn.Dropout(dropout_rate * 0.5),
            nn.Linear(hidden_dims[-1] // 2, num_classes)
        )
        
    def forward(self, x):
        x = self.features(x)
        return self.classifier(x)

class LabelSmoothingLoss(nn.Module):
    def __init__(self, smoothing=0.1, reduction='mean'):
        super().__init__()
        self.smoothing = smoothing
        self.reduction = reduction
    
    def forward(self, logits, targets):
        num_classes = logits.size(-1)
        log_preds = F.log_softmax(logits, dim=-1)
        
        with torch.no_grad():
            smoothed_targets = torch.zeros_like(log_preds)
            smoothed_targets.fill_(self.smoothing / (num_classes - 1))
            smoothed_targets.scatter_(1, targets.unsqueeze(1), 1.0 - self.smoothing)
        
        loss = - (smoothed_targets * log_preds).sum(dim=-1)
        
        if self.reduction == 'mean':
            return loss.mean()
        elif self.reduction == 'sum':
            return loss.sum()
        else:
            return loss

class Mixup:
    def __init__(self, alpha=0.2):
        self.alpha = alpha
    
    def __call__(self, batch_x, batch_y):
        if self.alpha <= 0:
            return batch_x, batch_y, 1.0
        
        lam = torch.distributions.beta.Beta(self.alpha, self.alpha).sample().item()
        batch_size = batch_x.size(0)
        index = torch.randperm(batch_size)
        
        mixed_x = lam * batch_x + (1 - lam) * batch_x[index]
        y_a, y_b = batch_y, batch_y[index]
        
        return mixed_x, y_a, y_b, lam

class Solution:
    def solve(self, train_loader, val_loader, metadata: dict = None):
        device = metadata.get('device', 'cpu')
        input_dim = metadata['input_dim']
        num_classes = metadata['num_classes']
        param_limit = metadata['param_limit']
        
        # Optimize architecture within parameter budget
        # Start with a reasonable base dimension
        base_dim = 768
        hidden_dims = [base_dim, base_dim, base_dim // 2, base_dim // 4]
        
        # Create initial model
        model = EfficientMLP(
            input_dim=input_dim,
            num_classes=num_classes,
            hidden_dims=hidden_dims,
            dropout_rate=0.3,
            use_bn=True
        )
        
        # Adjust architecture if needed to stay within budget
        param_count = count_parameters(model)
        
        if param_count > param_limit:
            # Reduce dimensions progressively
            scale = math.sqrt(param_limit / param_count)
            hidden_dims = [int(dim * scale) for dim in hidden_dims]
            hidden_dims = [max(dim, 128) for dim in hidden_dims]
            
            model = EfficientMLP(
                input_dim=input_dim,
                num_classes=num_classes,
                hidden_dims=hidden_dims,
                dropout_rate=0.3,
                use_bn=True
            )
        
        model = model.to(device)
        
        # Final parameter check
        param_count = count_parameters(model)
        assert param_count <= param_limit, f"Model exceeds parameter limit: {param_count} > {param_limit}"
        
        # Training setup
        criterion = LabelSmoothingLoss(smoothing=0.1)
        optimizer = optim.AdamW(
            model.parameters(),
            lr=0.001,
            weight_decay=0.01,
            betas=(0.9, 0.999)
        )
        
        scheduler = CosineAnnealingLR(
            optimizer,
            T_max=100,
            eta_min=1e-6
        )
        
        plateau_scheduler = ReduceLROnPlateau(
            optimizer,
            mode='max',
            factor=0.5,
            patience=10,
            min_lr=1e-6
        )
        
        mixup = Mixup(alpha=0.2)
        scaler = torch.amp.GradScaler('cpu') if hasattr(torch, 'amp') else None
        
        best_val_acc = 0.0
        best_model_state = None
        patience = 20
        patience_counter = 0
        
        num_epochs = 200
        train_losses = []
        val_accuracies = []
        
        for epoch in range(num_epochs):
            # Training phase
            model.train()
            train_loss = 0.0
            train_correct = 0
            train_total = 0
            
            for batch_idx, (inputs, targets) in enumerate(train_loader):
                inputs, targets = inputs.to(device), targets.to(device)
                
                # Apply mixup
                if torch.rand(1).item() > 0.5:
                    mixed_x, y_a, y_b, lam = mixup(inputs, targets)
                    
                    optimizer.zero_grad()
                    
                    if scaler is not None:
                        with torch.autocast(device_type='cpu', dtype=torch.bfloat16):
                            outputs = model(mixed_x)
                            loss = lam * criterion(outputs, y_a) + (1 - lam) * criterion(outputs, y_b)
                        scaler.scale(loss).backward()
                        scaler.step(optimizer)
                        scaler.update()
                    else:
                        outputs = model(mixed_x)
                        loss = lam * criterion(outputs, y_a) + (1 - lam) * criterion(outputs, y_b)
                        loss.backward()
                        optimizer.step()
                else:
                    optimizer.zero_grad()
                    
                    if scaler is not None:
                        with torch.autocast(device_type='cpu', dtype=torch.bfloat16):
                            outputs = model(inputs)
                            loss = criterion(outputs, targets)
                        scaler.scale(loss).backward()
                        scaler.step(optimizer)
                        scaler.update()
                    else:
                        outputs = model(inputs)
                        loss = criterion(outputs, targets)
                        loss.backward()
                        optimizer.step()
                
                train_loss += loss.item()
                
                # Calculate accuracy for non-mixed batches
                if batch_idx % 10 == 0:
                    with torch.no_grad():
                        _, predicted = outputs.max(1)
                        train_total += targets.size(0)
                        train_correct += predicted.eq(targets).sum().item()
            
            avg_train_loss = train_loss / len(train_loader)
            train_acc = 100. * train_correct / max(train_total, 1)
            train_losses.append(avg_train_loss)
            
            # Validation phase
            model.eval()
            val_correct = 0
            val_total = 0
            
            with torch.no_grad():
                for inputs, targets in val_loader:
                    inputs, targets = inputs.to(device), targets.to(device)
                    
                    if scaler is not None:
                        with torch.autocast(device_type='cpu', dtype=torch.bfloat16):
                            outputs = model(inputs)
                    else:
                        outputs = model(inputs)
                    
                    _, predicted = outputs.max(1)
                    val_total += targets.size(0)
                    val_correct += predicted.eq(targets).sum().item()
            
            val_acc = 100. * val_correct / val_total
            val_accuracies.append(val_acc / 100.0)
            
            # Update learning rate schedulers
            scheduler.step()
            plateau_scheduler.step(val_acc)
            
            # Save best model
            if val_acc > best_val_acc:
                best_val_acc = val_acc
                best_model_state = {k: v.cpu().clone() for k, v in model.state_dict().items()}
                patience_counter = 0
            else:
                patience_counter += 1
            
            # Early stopping
            if patience_counter >= patience:
                print(f"Early stopping at epoch {epoch + 1}")
                break
            
            # Print progress
            if (epoch + 1) % 10 == 0:
                print(f'Epoch [{epoch + 1}/{num_epochs}] - '
                      f'Train Loss: {avg_train_loss:.4f}, '
                      f'Train Acc: {train_acc:.2f}%, '
                      f'Val Acc: {val_acc:.2f}%, '
                      f'LR: {optimizer.param_groups[0]["lr"]:.6f}')
        
        # Load best model
        if best_model_state is not None:
            model.load_state_dict(best_model_state)
        
        # Final training on combined train + val for a few epochs
        model = model.to(device)
        
        # Create combined dataset loader (simple approach)
        combined_loader = torch.utils.data.DataLoader(
            torch.utils.data.ConcatDataset([
                train_loader.dataset,
                val_loader.dataset
            ]),
            batch_size=train_loader.batch_size,
            shuffle=True,
            num_workers=0
        )
        
        # Fine-tune on combined data
        optimizer = optim.AdamW(
            model.parameters(),
            lr=0.0001,
            weight_decay=0.001
        )
        
        fine_tune_epochs = 20
        model.train()
        
        for epoch in range(fine_tune_epochs):
            for inputs, targets in combined_loader:
                inputs, targets = inputs.to(device), targets.to(device)
                
                optimizer.zero_grad()
                
                if scaler is not None:
                    with torch.autocast(device_type='cpu', dtype=torch.bfloat16):
                        outputs = model(inputs)
                        loss = criterion(outputs, targets)
                    scaler.scale(loss).backward()
                    scaler.step(optimizer)
                    scaler.update()
                else:
                    outputs = model(inputs)
                    loss = criterion(outputs, targets)
                    loss.backward()
                    optimizer.step()
        
        model.eval()
        return model
