import math
import random
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F


class ResBlock(nn.Module):
    def __init__(self, dim, dropout=0.1):
        super().__init__()
        self.norm1 = nn.LayerNorm(dim)
        self.fc1 = nn.Linear(dim, dim)
        self.act = nn.GELU()
        self.drop1 = nn.Dropout(dropout)
        self.norm2 = nn.LayerNorm(dim)
        self.fc2 = nn.Linear(dim, dim)
        self.drop2 = nn.Dropout(dropout)

    def forward(self, x):
        residual = x
        out = self.norm1(x)
        out = self.fc1(out)
        out = self.act(out)
        out = self.drop1(out)
        out = self.norm2(out)
        out = self.fc2(out)
        out = self.drop2(out)
        return out + residual


class ResMLP(nn.Module):
    def __init__(self, input_dim, num_classes, num_blocks=3, dropout=0.1):
        super().__init__()
        self.dim = input_dim
        self.blocks = nn.ModuleList([ResBlock(input_dim, dropout=dropout) for _ in range(num_blocks)])
        self.head_norm = nn.LayerNorm(input_dim)
        self.classifier = nn.Linear(input_dim, num_classes)

    def forward(self, x):
        for blk in self.blocks:
            x = blk(x)
        x = self.head_norm(x)
        return self.classifier(x)


def count_trainable_params(model: nn.Module) -> int:
    return sum(p.numel() for p in model.parameters() if p.requires_grad)


def evaluate_model(model, loader, device):
    model.eval()
    correct = 0
    total = 0
    with torch.no_grad():
        for inputs, targets in loader:
            inputs = inputs.to(device, non_blocking=False).float()
            targets = targets.to(device, non_blocking=False).long()
            outputs = model(inputs)
            preds = outputs.argmax(dim=1)
            correct += (preds == targets).sum().item()
            total += targets.numel()
    acc = correct / total if total > 0 else 0.0
    return acc


class Solution:
    def solve(self, train_loader, val_loader, metadata: dict = None) -> torch.nn.Module:
        if metadata is None:
            metadata = {}
        # Reproducibility
        seed = 42
        random.seed(seed)
        np.random.seed(seed)
        torch.manual_seed(seed)

        device = metadata.get("device", "cpu")
        input_dim = int(metadata.get("input_dim", 384))
        num_classes = int(metadata.get("num_classes", 128))
        param_limit = int(metadata.get("param_limit", 1_000_000))

        # Build model respecting parameter budget
        # Start with 3 residual blocks at width=input_dim (no projection)
        num_blocks = 3
        dropout = 0.10
        model = ResMLP(input_dim, num_classes, num_blocks=num_blocks, dropout=dropout)

        # Reduce blocks if exceeding param limit
        while count_trainable_params(model) > param_limit and num_blocks > 1:
            num_blocks -= 1
            model = ResMLP(input_dim, num_classes, num_blocks=num_blocks, dropout=dropout)

        # If still exceeding (unlikely for provided metadata), fallback to compact 2-layer MLP
        if count_trainable_params(model) > param_limit:
            # Heuristic hidden size under budget
            # params = in*h + h + h*c + c ~ h*(in + c) + (h + c)
            # Solve for h <= (P - c) / (in + c + 1), keep margin
            P = param_limit - num_classes
            h = max(64, min(512, (P // (input_dim + num_classes + 1)) - 1))
            model = nn.Sequential(
                nn.LayerNorm(input_dim),
                nn.Linear(input_dim, h),
                nn.GELU(),
                nn.Dropout(0.1),
                nn.Linear(h, num_classes),
            )

        model.to(device)

        # Double-check hard limit
        assert count_trainable_params(model) <= param_limit, "Parameter budget exceeded"

        # Optimizer and training setup
        # Hyperparameters tuned for small synthetic dataset
        max_epochs = 120
        steps_per_epoch = max(1, len(train_loader))
        total_steps = max_epochs * steps_per_epoch

        # Use AdamW with OneCycleLR
        optimizer = torch.optim.AdamW(model.parameters(), lr=3e-3, weight_decay=1e-4, betas=(0.9, 0.999))
        try:
            scheduler = torch.optim.lr_scheduler.OneCycleLR(
                optimizer,
                max_lr=3e-3,
                steps_per_epoch=steps_per_epoch,
                epochs=max_epochs,
                pct_start=0.15,
                anneal_strategy="cos",
                div_factor=25.0,
                final_div_factor=1e3,
            )
        except Exception:
            scheduler = None

        # Loss with mild label smoothing
        criterion = nn.CrossEntropyLoss(label_smoothing=0.05)

        best_val_acc = 0.0
        best_state = None
        no_improve_epochs = 0
        patience = 20

        for epoch in range(max_epochs):
            model.train()
            for inputs, targets in train_loader:
                inputs = inputs.to(device, non_blocking=False).float()
                targets = targets.to(device, non_blocking=False).long()

                optimizer.zero_grad(set_to_none=True)
                outputs = model(inputs)
                loss = criterion(outputs, targets)
                loss.backward()
                nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
                optimizer.step()
                if scheduler is not None:
                    scheduler.step()

            # Validation
            val_acc = evaluate_model(model, val_loader, device)

            if val_acc > best_val_acc + 1e-6:
                best_val_acc = val_acc
                best_state = {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}
                no_improve_epochs = 0
            else:
                no_improve_epochs += 1

            if no_improve_epochs >= patience:
                break

        # Load best state if available
        if best_state is not None:
            model.load_state_dict(best_state)

        model.eval()
        return model
