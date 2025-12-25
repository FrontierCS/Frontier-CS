import math
import random
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim


class ResidualBlock(nn.Module):
    def __init__(self, dim: int, dropout: float = 0.1):
        super().__init__()
        self.norm = nn.LayerNorm(dim)
        self.fc = nn.Linear(dim, dim)
        self.act = nn.GELU()
        self.dropout = nn.Dropout(dropout)

    def forward(self, x):
        residual = x
        out = self.norm(x)
        out = self.fc(out)
        out = self.act(out)
        out = self.dropout(out)
        return residual + out


class ResMLP(nn.Module):
    def __init__(self, input_dim: int, num_classes: int, width: int, num_blocks: int, dropout: float = 0.1):
        super().__init__()
        self.input = nn.Linear(input_dim, width)
        self.blocks = nn.ModuleList([ResidualBlock(width, dropout=dropout) for _ in range(num_blocks)])
        self.norm = nn.LayerNorm(width)
        self.classifier = nn.Linear(width, num_classes)

    def forward(self, x):
        x = self.input(x)
        for block in self.blocks:
            x = block(x)
        x = self.norm(x)
        x = self.classifier(x)
        return x


class Solution:
    def __init__(self):
        # Set seeds for reproducibility
        seed = 42
        random.seed(seed)
        np.random.seed(seed)
        torch.manual_seed(seed)

    def _param_count_resmlp(self, input_dim: int, num_classes: int, width: int, num_blocks: int) -> int:
        # Input linear: input_dim * width + width
        # Each block: LayerNorm(width) -> 2*width params, Linear(width,width) -> width*width + width
        #   => per block: width*width + 3*width
        # Final LayerNorm: 2*width
        # Classifier: width * num_classes + num_classes
        d = input_dim
        c = num_classes
        w = width
        n = num_blocks
        return n * w * w + w * (d + c + 3 * n + 3) + c

    def _select_architecture(self, input_dim: int, num_classes: int, param_limit: int):
        # Prefer 4 blocks, then 3, then 2, then 1
        preferred_blocks = [4, 3, 2, 1]
        chosen_width = None
        chosen_blocks = None

        for num_blocks in preferred_blocks:
            # Upper bound for width search
            approx_max_width = int(math.sqrt(max(param_limit // max(num_blocks, 1), 1))) + 256
            hi = max(16, min(4096, approx_max_width))
            best_w = None
            for w in range(hi, 3, -1):
                p = self._param_count_resmlp(input_dim, num_classes, w, num_blocks)
                if p <= param_limit:
                    best_w = w
                    break
            if best_w is not None:
                chosen_width = best_w
                chosen_blocks = num_blocks
                break

        if chosen_width is None or chosen_blocks is None:
            # Fallback very small model if param_limit is extremely tiny (not expected in this task)
            chosen_width = min(64, max(4, input_dim))
            chosen_blocks = 1

        return chosen_width, chosen_blocks

    def solve(self, train_loader, val_loader, metadata: dict = None) -> torch.nn.Module:
        if metadata is None:
            metadata = {}
        input_dim = int(metadata.get("input_dim", 384))
        num_classes = int(metadata.get("num_classes", 128))
        param_limit = int(metadata.get("param_limit", 5_000_000))
        device_str = metadata.get("device", "cpu")
        device = torch.device(device_str)

        width, num_blocks = self._select_architecture(input_dim, num_classes, param_limit)

        model = ResMLP(input_dim=input_dim, num_classes=num_classes, width=width, num_blocks=num_blocks, dropout=0.1)
        model.to(device)

        # Safety check on parameter count
        param_count = sum(p.numel() for p in model.parameters() if p.requires_grad)
        if param_count > param_limit:
            # If for some numerical reason we exceed the limit, shrink width until we fit.
            while param_count > param_limit and width > 4:
                width -= 1
                model = ResMLP(input_dim=input_dim, num_classes=num_classes, width=width, num_blocks=num_blocks,
                               dropout=0.1).to(device)
                param_count = sum(p.numel() for p in model.parameters() if p.requires_grad)

        # Training setup
        # Slightly aggressive LR with cosine decay, AdamW optimizer, label smoothing for robustness
        base_lr = 1e-3
        weight_decay = 1e-4
        max_epochs = 200
        patience = 30

        optimizer = optim.AdamW(model.parameters(), lr=base_lr, weight_decay=weight_decay)
        scheduler = optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=max_epochs, eta_min=1e-5)

        # Use label smoothing for better generalization
        try:
            criterion = nn.CrossEntropyLoss(label_smoothing=0.05)
        except TypeError:
            criterion = nn.CrossEntropyLoss()

        best_val_acc = -1.0
        best_epoch = -1
        best_state = None

        # Some metadata might include sample counts
        train_samples = metadata.get("train_samples", None)
        val_samples = metadata.get("val_samples", None)

        for epoch in range(max_epochs):
            model.train()
            for inputs, targets in train_loader:
                inputs = inputs.to(device)
                targets = targets.to(device)

                if inputs.dim() > 2:
                    inputs = inputs.view(inputs.size(0), -1)

                optimizer.zero_grad()
                outputs = model(inputs)
                loss = criterion(outputs, targets)
                loss.backward()
                nn.utils.clip_grad_norm_(model.parameters(), max_norm=5.0)
                optimizer.step()

            # Validation
            if val_loader is not None:
                model.eval()
                correct = 0
                total = 0
                with torch.no_grad():
                    for inputs, targets in val_loader:
                        inputs = inputs.to(device)
                        targets = targets.to(device)

                        if inputs.dim() > 2:
                            inputs = inputs.view(inputs.size(0), -1)

                        outputs = model(inputs)
                        preds = outputs.argmax(dim=1)
                        correct += (preds == targets).sum().item()
                        total += targets.size(0)

                if total > 0:
                    val_acc = correct / total
                else:
                    val_acc = 0.0

                if val_acc > best_val_acc + 1e-6:
                    best_val_acc = val_acc
                    best_epoch = epoch
                    best_state = {k: v.cpu().clone() for k, v in model.state_dict().items()}

                if epoch - best_epoch >= patience:
                    scheduler.step()
                    break

            scheduler.step()

        if best_state is not None:
            model.load_state_dict(best_state)

        model.to("cpu")
        return model
