import math
import random
import time
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F


def set_seed(seed: int = 42):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)


def count_parameters(model: torch.nn.Module) -> int:
    return sum(p.numel() for p in model.parameters() if p.requires_grad)


def evaluate_accuracy(model: torch.nn.Module, data_loader, device: torch.device) -> float:
    model.eval()
    correct = 0
    total = 0
    with torch.no_grad():
        for x, y in data_loader:
            x = x.to(device, non_blocking=True)
            y = y.to(device, non_blocking=True)
            logits = model(x)
            preds = logits.argmax(dim=1)
            correct += (preds == y).sum().item()
            total += y.numel()
    return correct / max(1, total)


class ResidualFFN(nn.Module):
    def __init__(self, dim: int, expansion: int = 4, dropout: float = 0.1):
        super().__init__()
        hidden = dim * expansion
        self.norm = nn.LayerNorm(dim)
        self.fc1 = nn.Linear(dim, hidden)
        self.act = nn.GELU()
        self.drop1 = nn.Dropout(dropout)
        self.fc2 = nn.Linear(hidden, dim)
        self.drop2 = nn.Dropout(dropout)

    def forward(self, x):
        residual = x
        y = self.norm(x)
        y = self.fc1(y)
        y = self.act(y)
        y = self.drop1(y)
        y = self.fc2(y)
        y = self.drop2(y)
        return residual + y


class ResMLP(nn.Module):
    def __init__(self, input_dim: int, num_classes: int, width: int = 384, depth: int = 4, expansion: int = 4, dropout: float = 0.1):
        super().__init__()
        self.in_proj = nn.Linear(input_dim, width)
        self.blocks = nn.ModuleList([ResidualFFN(width, expansion=expansion, dropout=dropout) for _ in range(depth)])
        self.out_norm = nn.LayerNorm(width)
        self.head = nn.Linear(width, num_classes)
        self._init_weights()

    def _init_weights(self):
        for m in self.modules():
            if isinstance(m, nn.Linear):
                fan_in = m.weight.size(1)
                std = math.sqrt(2.0 / fan_in)
                nn.init.trunc_normal_(m.weight, std=std * 0.5, a=-2*std, b=2*std)
                if m.bias is not None:
                    nn.init.zeros_(m.bias)
            elif isinstance(m, nn.LayerNorm):
                nn.init.ones_(m.weight)
                nn.init.zeros_(m.bias)

    def forward(self, x):
        x = self.in_proj(x)
        for blk in self.blocks:
            x = blk(x)
        x = self.out_norm(x)
        x = self.head(x)
        return x


class Solution:
    def solve(self, train_loader, val_loader, metadata: dict = None) -> torch.nn.Module:
        set_seed(1234)

        device = torch.device(metadata.get("device", "cpu") if metadata is not None else "cpu")
        num_classes = int(metadata.get("num_classes", 128)) if metadata is not None else 128
        input_dim = int(metadata.get("input_dim", 384)) if metadata is not None else 384
        param_limit = int(metadata.get("param_limit", 5_000_000)) if metadata is not None else 5_000_000

        # Build a strong yet efficient architecture under the parameter budget
        # Start with high-capacity configuration, then shrink if needed.
        width = 384
        depth = 4
        expansion = 4
        dropout = 0.1

        # Try to fit within the param limit; reduce width if needed
        def build_model_with(width_try, depth_try):
            return ResMLP(input_dim=input_dim, num_classes=num_classes, width=width_try, depth=depth_try, expansion=expansion, dropout=dropout)

        model = build_model_with(width, depth)
        params = count_parameters(model)
        while params > param_limit:
            if depth > 1:
                depth -= 1
            elif width > 64:
                width -= 16
            else:
                break
            model = build_model_with(width, depth)
            params = count_parameters(model)

        model.to(device)

        # Training setup
        epochs = 200
        if metadata is not None:
            train_samples = metadata.get("train_samples", None)
            if train_samples is not None:
                if train_samples <= 2048:
                    epochs = 220
                elif train_samples <= 4096:
                    epochs = 180
                else:
                    epochs = 120

        base_lr = 3e-3
        weight_decay = 1e-2
        label_smoothing = 0.05
        patience = 30
        grad_clip_norm = 1.0

        optimizer = torch.optim.AdamW(model.parameters(), lr=base_lr, weight_decay=weight_decay, betas=(0.9, 0.95))
        scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=epochs, eta_min=base_lr * 1e-2)
        criterion = nn.CrossEntropyLoss(label_smoothing=label_smoothing)

        best_acc = -1.0
        best_state = None
        no_improve = 0

        for epoch in range(epochs):
            model.train()
            for xb, yb in train_loader:
                xb = xb.to(device, non_blocking=True)
                yb = yb.to(device, non_blocking=True)

                optimizer.zero_grad(set_to_none=True)
                logits = model(xb)
                loss = criterion(logits, yb)
                loss.backward()
                if grad_clip_norm is not None:
                    torch.nn.utils.clip_grad_norm_(model.parameters(), grad_clip_norm)
                optimizer.step()

            scheduler.step()

            # Validation
            val_acc = evaluate_accuracy(model, val_loader, device)
            if val_acc > best_acc:
                best_acc = val_acc
                best_state = {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}
                no_improve = 0
            else:
                no_improve += 1

            if no_improve >= patience:
                break

        if best_state is not None:
            model.load_state_dict(best_state, strict=True)
        model.to(device)
        model.eval()
        return model