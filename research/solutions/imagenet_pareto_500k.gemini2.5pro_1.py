import torch
import torch.nn as nn
from torch.utils.data import DataLoader, ConcatDataset

class CustomNet(nn.Module):
    def __init__(self, input_dim: int, num_classes: int):
        super().__init__()
        
        h_size = 495
        dropout_rate = 0.3

        self.entry_block = nn.Sequential(
            nn.Linear(input_dim, h_size),
            nn.BatchNorm1d(h_size),
            nn.GELU(),
            nn.Dropout(p=dropout_rate)
        )
        
        self.residual_block = nn.Sequential(
            nn.Linear(h_size, h_size),
            nn.BatchNorm1d(h_size),
            nn.GELU(),
            nn.Dropout(p=dropout_rate)
        )
        
        self.output_layer = nn.Linear(h_size, num_classes)
        
        self._initialize_weights()

    def _initialize_weights(self):
        for m in self.modules():
            if isinstance(m, nn.Linear):
                nn.init.kaiming_normal_(m.weight, mode='fan_in', nonlinearity='relu')
                if m.bias is not None:
                    nn.init.constant_(m.bias, 0)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x_entry = self.entry_block(x)
        x_res = self.residual_block(x_entry)
        x_out = x_entry + x_res
        return self.output_layer(x_out)

class Solution:
    def solve(self, train_loader: DataLoader, val_loader: DataLoader, metadata: dict = None) -> nn.Module:
        device = torch.device(metadata.get("device", "cpu"))
        input_dim = metadata["input_dim"]
        num_classes = metadata["num_classes"]

        model = CustomNet(input_dim, num_classes).to(device)

        combined_dataset = ConcatDataset([train_loader.dataset, val_loader.dataset])
        
        batch_size = train_loader.batch_size if train_loader.batch_size is not None else 64
        
        num_workers = 4 
        
        combined_loader = DataLoader(
            combined_dataset,
            batch_size=batch_size,
            shuffle=True,
            num_workers=num_workers,
            pin_memory=False,
            drop_last=True
        )

        NUM_EPOCHS = 200
        MAX_LR = 3e-3
        WEIGHT_DECAY = 0.01
        LABEL_SMOOTHING = 0.1

        optimizer = torch.optim.AdamW(model.parameters(), lr=MAX_LR, weight_decay=WEIGHT_DECAY)
        
        criterion = nn.CrossEntropyLoss(label_smoothing=LABEL_SMOOTHING)
        
        total_steps = NUM_EPOCHS * len(combined_loader)
        scheduler = torch.optim.lr_scheduler.OneCycleLR(
            optimizer,
            max_lr=MAX_LR,
            total_steps=total_steps,
            pct_start=0.25,
            anneal_strategy='cos'
        )

        model.train()
        for _ in range(NUM_EPOCHS):
            for inputs, targets in combined_loader:
                inputs, targets = inputs.to(device), targets.to(device)

                outputs = model(inputs)
                loss = criterion(outputs, targets)

                optimizer.zero_grad(set_to_none=True)
                loss.backward()
                optimizer.step()
                
                scheduler.step()

        model.eval()
        return model