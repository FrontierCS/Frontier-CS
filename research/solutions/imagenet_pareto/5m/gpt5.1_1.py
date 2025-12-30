import torch
import torch.nn as nn
import torch.optim as optim
import random
import numpy as np


class ResidualBottleneckBlock(nn.Module):
    def __init__(self, dim, hidden_dim, dropout=0.1):
        super().__init__()
        self.norm = nn.LayerNorm(dim)
        self.fc1 = nn.Linear(dim, hidden_dim)
        self.act = nn.GELU()
        self.fc2 = nn.Linear(hidden_dim, dim)
        self.dropout = nn.Dropout(dropout)

    def forward(self, x):
        residual = x
        x = self.norm(x)
        x = self.fc1(x)
        x = self.act(x)
        x = self.dropout(x)
        x = self.fc2(x)
        x = self.dropout(x)
        return x + residual


class MLPResNet(nn.Module):
    def __init__(self, input_dim, num_classes, embed_dim, bottleneck_dim, num_blocks, dropout=0.1):
        super().__init__()
        self.input_layer = nn.Linear(input_dim, embed_dim)
        self.input_act = nn.GELU()
        self.blocks = nn.ModuleList(
            [ResidualBottleneckBlock(embed_dim, bottleneck_dim, dropout=dropout) for _ in range(num_blocks)]
        )
        self.norm_out = nn.LayerNorm(embed_dim)
        self.dropout_out = nn.Dropout(dropout)
        self.head = nn.Linear(embed_dim, num_classes)

    def forward(self, x):
        x = self.input_act(self.input_layer(x))
        for block in self.blocks:
            x = block(x)
        x = self.norm_out(x)
        x = self.dropout_out(x)
        x = self.head(x)
        return x


class Solution:
    def _set_seed(self, seed: int = 42):
        random.seed(seed)
        np.random.seed(seed)
        torch.manual_seed(seed)

    def _estimate_params(self, input_dim, num_classes, embed_dim, bottleneck_dim, num_blocks):
        # Input layer
        input_params = input_dim * embed_dim + embed_dim
        # Residual blocks
        block_params_per = (
            embed_dim * bottleneck_dim  # fc1 weights
            + bottleneck_dim            # fc1 bias
            + bottleneck_dim * embed_dim  # fc2 weights
            + embed_dim                 # fc2 bias
            + 2 * embed_dim             # LayerNorm (weight + bias)
        )
        block_params = num_blocks * block_params_per
        # Output norm
        norm_out_params = 2 * embed_dim
        # Head
        head_params = embed_dim * num_classes + num_classes
        return input_params + block_params + norm_out_params + head_params

    def _build_model_under_limit(self, input_dim, num_classes, param_limit):
        # Candidate embed dims (larger first)
        embed_dims = [1024, 896, 768, 640, 512, 384, 256]
        max_blocks = 12
        best_cfg = None

        for embed_dim in embed_dims:
            bottleneck_dim = max(embed_dim // 4, 64)
            for num_blocks in range(max_blocks, 0, -1):
                total_params = self._estimate_params(
                    input_dim, num_classes, embed_dim, bottleneck_dim, num_blocks
                )
                if total_params <= param_limit:
                    best_cfg = (embed_dim, bottleneck_dim, num_blocks, total_params)
                    break
            if best_cfg is not None:
                break

        # Fallback very small model if nothing fits (should not happen for given limits)
        if best_cfg is None:
            embed_dim = min(256, input_dim * 2)
            bottleneck_dim = max(embed_dim // 4, 32)
            num_blocks = 1
        else:
            embed_dim, bottleneck_dim, num_blocks, _ = best_cfg

        model = MLPResNet(
            input_dim=input_dim,
            num_classes=num_classes,
            embed_dim=embed_dim,
            bottleneck_dim=bottleneck_dim,
            num_blocks=num_blocks,
            dropout=0.1,
        )
        return model

    def solve(self, train_loader, val_loader, metadata: dict = None) -> torch.nn.Module:
        if metadata is None:
            metadata = {}
        input_dim = int(metadata.get("input_dim", 384))
        num_classes = int(metadata.get("num_classes", 128))
        param_limit = int(metadata.get("param_limit", 5_000_000))
        device_str = metadata.get("device", "cpu")
        device = torch.device(device_str)

        self._set_seed(42)

        model = self._build_model_under_limit(input_dim, num_classes, param_limit)
        model.to(device)

        # Double-check parameter limit
        param_count = sum(p.numel() for p in model.parameters() if p.requires_grad)
        if param_count > param_limit:
            # As a hard safety fallback, use a smaller simple MLP
            hidden_dim = min(512, input_dim * 2)
            model = nn.Sequential(
                nn.Linear(input_dim, hidden_dim),
                nn.GELU(),
                nn.Linear(hidden_dim, hidden_dim),
                nn.GELU(),
                nn.Linear(hidden_dim, num_classes),
            )
            model.to(device)

        lr = 5e-4
        weight_decay = 1e-2
        num_epochs = 250
        patience = 40

        optimizer = optim.AdamW(model.parameters(), lr=lr, weight_decay=weight_decay)
        scheduler = optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=num_epochs)
        criterion = nn.CrossEntropyLoss(label_smoothing=0.05)

        best_val_acc = 0.0
        best_state = None
        epochs_no_improve = 0

        for epoch in range(num_epochs):
            model.train()
            train_correct = 0
            train_total = 0

            for inputs, targets in train_loader:
                inputs = inputs.to(device=device, dtype=torch.float32, non_blocking=False)
                targets = targets.to(device=device, dtype=torch.long, non_blocking=False)

                optimizer.zero_grad()
                outputs = model(inputs)
                loss = criterion(outputs, targets)
                loss.backward()
                nn.utils.clip_grad_norm_(model.parameters(), max_norm=5.0)
                optimizer.step()

                with torch.no_grad():
                    preds = outputs.argmax(dim=1)
                    train_correct += (preds == targets).sum().item()
                    train_total += targets.numel()

            model.eval()
            val_correct = 0
            val_total = 0
            with torch.no_grad():
                for inputs, targets in val_loader:
                    inputs = inputs.to(device=device, dtype=torch.float32, non_blocking=False)
                    targets = targets.to(device=device, dtype=torch.long, non_blocking=False)
                    outputs = model(inputs)
                    preds = outputs.argmax(dim=1)
                    val_correct += (preds == targets).sum().item()
                    val_total += targets.numel()

            val_acc = val_correct / max(1, val_total)

            if epoch == 0 or val_acc > best_val_acc + 1e-4:
                best_val_acc = val_acc
                epochs_no_improve = 0
                best_state = {k: v.cpu().clone() for k, v in model.state_dict().items()}
            else:
                epochs_no_improve += 1
                if epochs_no_improve >= patience:
                    break

            scheduler.step()

        if best_state is not None:
            model.load_state_dict(best_state)

        model.to(torch.device("cpu"))
        return model