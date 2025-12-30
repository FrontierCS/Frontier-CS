import torch
import torch.nn as nn
import torch.optim as optim
import copy

class ResBlock(nn.Module):
    def __init__(self, main_dim: int, bottleneck_dim: int, dropout_rate: float):
        super().__init__()
        self.block = nn.Sequential(
            nn.Linear(main_dim, bottleneck_dim),
            nn.BatchNorm1d(bottleneck_dim),
            nn.ReLU(inplace=True),
            nn.Dropout(p=dropout_rate),
            nn.Linear(bottleneck_dim, main_dim),
            nn.BatchNorm1d(main_dim),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return x + self.block(x)

class DeepResMLP(nn.Module):
    def __init__(self, 
                 input_dim: int, 
                 num_classes: int, 
                 main_dim: int = 1200, 
                 bottleneck_dim: int = 256, 
                 num_blocks: int = 3,
                 stem_dropout: float = 0.4,
                 block_dropout: float = 0.2):
        super().__init__()
        
        self.stem = nn.Sequential(
            nn.Linear(input_dim, main_dim),
            nn.BatchNorm1d(main_dim),
            nn.ReLU(inplace=True),
            nn.Dropout(p=stem_dropout),
        )
        
        blocks = []
        for _ in range(num_blocks):
            blocks.append(ResBlock(main_dim, bottleneck_dim, block_dropout))
            blocks.append(nn.ReLU(inplace=True))
        self.body = nn.Sequential(*blocks)
        
        self.head = nn.Linear(main_dim, num_classes)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self.stem(x)
        x = self.body(x)
        x = self.head(x)
        return x

class Solution:
    def solve(self, train_loader, val_loader, metadata: dict = None) -> torch.nn.Module:
        device = torch.device(metadata.get("device", "cpu"))
        input_dim = metadata["input_dim"]
        num_classes = metadata["num_classes"]

        model = DeepResMLP(
            input_dim=input_dim,
            num_classes=num_classes,
            main_dim=1200,
            bottleneck_dim=256,
            num_blocks=3,
            stem_dropout=0.4,
            block_dropout=0.2
        ).to(device)

        epochs = 400
        patience = 40
        max_lr = 2e-3
        weight_decay = 1e-4
        label_smoothing = 0.1

        criterion = nn.CrossEntropyLoss(label_smoothing=label_smoothing)
        optimizer = optim.AdamW(model.parameters(), lr=max_lr, weight_decay=weight_decay)
        
        scheduler = optim.lr_scheduler.OneCycleLR(
            optimizer, 
            max_lr=max_lr, 
            epochs=epochs, 
            steps_per_epoch=len(train_loader)
        )

        best_val_loss = float('inf')
        best_model_state = None
        patience_counter = 0

        for epoch in range(epochs):
            model.train()
            for inputs, targets in train_loader:
                inputs, targets = inputs.to(device), targets.to(device)
                
                optimizer.zero_grad()
                outputs = model(inputs)
                loss = criterion(outputs, targets)
                loss.backward()
                optimizer.step()
                scheduler.step()

            model.eval()
            current_val_loss = 0.0
            with torch.no_grad():
                for inputs, targets in val_loader:
                    inputs, targets = inputs.to(device), targets.to(device)
                    outputs = model(inputs)
                    loss = criterion(outputs, targets)
                    current_val_loss += loss.item() * inputs.size(0)

            current_val_loss /= len(val_loader.dataset)

            if current_val_loss < best_val_loss:
                best_val_loss = current_val_loss
                best_model_state = copy.deepcopy(model.state_dict())
                patience_counter = 0
            else:
                patience_counter += 1
                if patience_counter >= patience:
                    break
        
        if best_model_state:
            model.load_state_dict(best_model_state)
            
        return model.to(torch.device("cpu"))