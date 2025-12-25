import torch
import torch.nn as nn
import torch.optim as optim
from copy import deepcopy

class Solution:
    def solve(self, train_loader, val_loader, metadata: dict = None) -> torch.nn.Module:
        """
        Train a model and return it.
        
        Args:
            train_loader: PyTorch DataLoader with training data
            val_loader: PyTorch DataLoader with validation data
            metadata: Dict with keys:
                - num_classes: int (128)
                - input_dim: int (384)
                - param_limit: int (1,000,000)
                - baseline_accuracy: float (0.8)
                - train_samples: int
                - val_samples: int
                - test_samples: int
                - device: str ("cpu")
        
        Returns:
            Trained torch.nn.Module ready for evaluation
        """
        
        class ResidualBlock(nn.Module):
            """A residual block for an MLP."""
            def __init__(self, size, dropout_p=0.3):
                super().__init__()
                self.ffn = nn.Sequential(
                    nn.Linear(size, size),
                    nn.BatchNorm1d(size),
                    nn.GELU(),
                    nn.Dropout(p=dropout_p),
                    nn.Linear(size, size),
                    nn.BatchNorm1d(size),
                )
                self.act = nn.GELU()

            def forward(self, x):
                residual = x
                out = self.ffn(x)
                out += residual
                out = self.act(out)
                return out

        class DeepMLP(nn.Module):
            """A deep MLP with residual connections, designed to maximize parameters."""
            def __init__(self, input_dim, num_classes, d_model=438, num_blocks=2, dropout_p=0.3):
                super().__init__()
                
                self.pre_proc = nn.Sequential(
                    nn.Linear(input_dim, d_model),
                    nn.BatchNorm1d(d_model),
                    nn.GELU(),
                )
                
                blocks = [ResidualBlock(d_model, dropout_p=dropout_p) for _ in range(num_blocks)]
                self.blocks = nn.Sequential(*blocks)
                
                self.classifier = nn.Linear(d_model, num_classes)
                
            def forward(self, x):
                x = self.pre_proc(x)
                x = self.blocks(x)
                x = self.classifier(x)
                return x

        device = metadata.get("device", "cpu")
        input_dim = metadata["input_dim"]
        num_classes = metadata["num_classes"]

        model = DeepMLP(input_dim=input_dim, num_classes=num_classes).to(device)
        
        # Hyperparameters
        EPOCHS = 250
        LEARNING_RATE = 3e-4
        WEIGHT_DECAY = 1e-4
        LABEL_SMOOTHING = 0.1
        PATIENCE = 30
        WARMUP_EPOCHS = 10

        criterion = nn.CrossEntropyLoss(label_smoothing=LABEL_SMOOTHING)
        optimizer = optim.AdamW(model.parameters(), lr=LEARNING_RATE, weight_decay=WEIGHT_DECAY)
        
        warmup_scheduler = optim.lr_scheduler.LinearLR(optimizer, start_factor=0.1, total_iters=WARMUP_EPOCHS)
        main_scheduler = optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=EPOCHS - WARMUP_EPOCHS, eta_min=1e-6)
        scheduler = optim.lr_scheduler.SequentialLR(optimizer, schedulers=[warmup_scheduler, main_scheduler], milestones=[WARMUP_EPOCHS])

        best_val_acc = 0.0
        epochs_no_improve = 0
        best_model_state = None

        for epoch in range(EPOCHS):
            model.train()
            for inputs, targets in train_loader:
                inputs, targets = inputs.to(device), targets.to(device)

                optimizer.zero_grad()
                outputs = model(inputs)
                loss = criterion(outputs, targets)
                loss.backward()
                optimizer.step()

            model.eval()
            val_correct = 0
            val_total = 0
            with torch.no_grad():
                for inputs, targets in val_loader:
                    inputs, targets = inputs.to(device), targets.to(device)
                    outputs = model(inputs)
                    _, predicted = torch.max(outputs.data, 1)
                    val_total += targets.size(0)
                    val_correct += (predicted == targets).sum().item()
            
            val_acc = val_correct / val_total if val_total > 0 else 0.0

            if val_acc > best_val_acc:
                best_val_acc = val_acc
                best_model_state = deepcopy(model.state_dict())
                epochs_no_improve = 0
            else:
                epochs_no_improve += 1
            
            if epochs_no_improve >= PATIENCE:
                break
            
            scheduler.step()

        if best_model_state:
            model.load_state_dict(best_model_state)

        model.eval()
        return model
