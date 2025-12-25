import math
import time
import copy
import random
from typing import Tuple, Optional

import torch
import torch.nn as nn
import torch.nn.functional as F


def set_seed(seed: int = 42):
    random.seed(seed)
    torch.manual_seed(seed)


def count_trainable_params(model: nn.Module) -> int:
    return sum(p.numel() for p in model.parameters() if p.requires_grad)


class ResidualMLPBlock(nn.Module):
    def __init__(self, width: int, dropout: float = 0.1):
        super().__init__()
        self.norm = nn.LayerNorm(width)
        self.fc1 = nn.Linear(width, width, bias=True)
        self.act = nn.GELU()
        self.drop1 = nn.Dropout(dropout)
        self.fc2 = nn.Linear(width, width, bias=True)
        self.drop2 = nn.Dropout(dropout)

        # Initialization for stability
        nn.init.kaiming_normal_(self.fc1.weight, nonlinearity='gelu')
        nn.init.zeros_(self.fc1.bias)
        nn.init.kaiming_normal_(self.fc2.weight, nonlinearity='linear')
        nn.init.zeros_(self.fc2.bias)

    def forward(self, x):
        h = self.norm(x)
        h = self.fc1(h)
        h = self.act(h)
        h = self.drop1(h)
        h = self.fc2(h)
        h = self.drop2(h)
        return x + h


class MLPClassifier(nn.Module):
    def __init__(self, input_dim: int, num_classes: int, width: int, depth: int, dropout: float = 0.1,
                 use_input_ln: bool = True):
        super().__init__()
        self.use_input_ln = use_input_ln
        if use_input_ln:
            self.in_ln = nn.LayerNorm(input_dim)
        self.in_proj = nn.Linear(input_dim, width, bias=True)
        blocks = []
        for _ in range(depth):
            blocks.append(ResidualMLPBlock(width, dropout))
        self.blocks = nn.Sequential(*blocks)
        self.out_ln = nn.LayerNorm(width)
        self.head = nn.Linear(width, num_classes, bias=True)

        nn.init.kaiming_normal_(self.in_proj.weight, nonlinearity='linear')
        nn.init.zeros_(self.in_proj.bias)
        nn.init.zeros_(self.head.bias)

    def forward(self, x):
        if self.use_input_ln:
            x = self.in_ln(x)
        x = self.in_proj(x)
        x = self.blocks(x)
        x = self.out_ln(x)
        x = self.head(x)
        return x


class EMAHelper:
    def __init__(self, model: nn.Module, decay: float = 0.999):
        self.decay = decay
        self.ema_model = copy.deepcopy(model).eval()
        for p in self.ema_model.parameters():
            p.requires_grad_(False)

    @torch.no_grad()
    def update(self, model: nn.Module):
        msd = model.state_dict()
        for (k, v) in self.ema_model.state_dict().items():
            v.copy_(v * self.decay + msd[k] * (1.0 - self.decay))

    def state_dict(self):
        return self.ema_model.state_dict()

    def load_state_dict(self, sd):
        self.ema_model.load_state_dict(sd)

    def to(self, device):
        self.ema_model.to(device)
        return self

    def module(self):
        return self.ema_model


def param_count_formula(input_dim: int, num_classes: int, width: int, depth: int, use_input_ln: bool = True) -> int:
    # in_ln params
    total = 0
    if use_input_ln:
        total += 2 * input_dim  # gamma and beta

    # input projection
    total += input_dim * width + width  # weight + bias

    # residual blocks
    for _ in range(depth):
        # LayerNorm in block: 2*width
        total += 2 * width
        # fc1 and fc2: each width*width + width bias
        total += width * width + width
        total += width * width + width

    # output ln
    total += 2 * width

    # head
    total += width * num_classes + num_classes

    return total


def choose_width_and_depth(input_dim: int, num_classes: int, param_limit: int, use_input_ln: bool = True) -> Tuple[int, int]:
    # Try depths in order: prefer more depth but ensure width large; choose configuration with max parameters under limit
    candidate_depths = [4, 3, 5, 2]
    best = (3, 864)  # default fallback
    best_params = -1
    for depth in candidate_depths:
        lo, hi = 64, 3072
        # Binary search maximum width that fits
        while lo <= hi:
            mid = (lo + hi) // 2
            # Round to multiple of 16 for stability
            width = max(16, (mid // 16) * 16)
            p = param_count_formula(input_dim, num_classes, width, depth, use_input_ln)
            if p <= param_limit:
                lo = width + 16
                if p > best_params:
                    best_params = p
                    best = (depth, width)
            else:
                hi = width - 16
    return best[1], best[0]


class LabelSmoothingLoss(nn.Module):
    def __init__(self, smoothing: float = 0.05):
        super().__init__()
        self.smoothing = smoothing

    def forward(self, logits, targets):
        n_classes = logits.size(-1)
        log_probs = F.log_softmax(logits, dim=-1)
        with torch.no_grad():
            true_dist = torch.zeros_like(logits)
            true_dist.fill_(self.smoothing / (n_classes - 1))
            true_dist.scatter_(1, targets.unsqueeze(1), 1.0 - self.smoothing)
        loss = (-true_dist * log_probs).sum(dim=1).mean()
        return loss


def evaluate_accuracy(model: nn.Module, data_loader, device: torch.device) -> float:
    model.eval()
    correct = 0
    total = 0
    with torch.no_grad():
        for xb, yb in data_loader:
            xb = xb.to(device)
            yb = yb.to(device)
            logits = model(xb)
            preds = logits.argmax(dim=1)
            correct += (preds == yb).sum().item()
            total += yb.numel()
    return correct / max(1, total)


class Solution:
    def solve(self, train_loader, val_loader, metadata: dict = None) -> torch.nn.Module:
        set_seed(42)
        device = torch.device(metadata.get("device", "cpu") if metadata is not None else "cpu")
        torch.set_num_threads(min(8, max(1, torch.get_num_threads())))
        input_dim = int(metadata.get("input_dim", 384))
        num_classes = int(metadata.get("num_classes", 128))
        param_limit = int(metadata.get("param_limit", 5_000_000))

        # Architecture selection
        use_input_ln = True
        width, depth = choose_width_and_depth(input_dim, num_classes, param_limit, use_input_ln=use_input_ln)
        dropout = 0.10 if depth >= 4 else 0.15

        model = MLPClassifier(input_dim=input_dim, num_classes=num_classes, width=width, depth=depth,
                              dropout=dropout, use_input_ln=use_input_ln).to(device)

        # Ensure parameter limit is respected; if exceeded, shrink width
        param_count = count_trainable_params(model)
        while param_count > param_limit and width > 64:
            width -= 16
            model = MLPClassifier(input_dim=input_dim, num_classes=num_classes, width=width, depth=depth,
                                  dropout=dropout, use_input_ln=use_input_ln).to(device)
            param_count = count_trainable_params(model)

        # Training configuration
        epochs = 160
        steps_per_epoch = max(1, len(train_loader))
        total_steps = steps_per_epoch * epochs

        # Optimizer and scheduler
        base_lr = 1e-3
        max_lr = 5e-3 if width >= 736 else 6e-3
        weight_decay = 5e-4 if width >= 736 else 3e-4
        optimizer = torch.optim.AdamW(model.parameters(), lr=base_lr, weight_decay=weight_decay)
        try:
            scheduler = torch.optim.lr_scheduler.OneCycleLR(
                optimizer,
                max_lr=max_lr,
                total_steps=total_steps,
                pct_start=0.15,
                anneal_strategy='cos',
                div_factor=max(max_lr / base_lr, 10.0),
                final_div_factor=100.0
            )
        except Exception:
            scheduler = None

        # Loss with label smoothing
        try:
            criterion = nn.CrossEntropyLoss(label_smoothing=0.05)
        except TypeError:
            criterion = LabelSmoothingLoss(smoothing=0.05)

        # EMA for better generalization
        ema = EMAHelper(model, decay=0.999)
        ema.to(device)

        best_val_acc = 0.0
        best_state = copy.deepcopy(ema.state_dict())
        patience = 40
        epochs_no_improve = 0

        model.train()
        step_count = 0
        for epoch in range(epochs):
            model.train()
            for xb, yb in train_loader:
                xb = xb.to(device)
                yb = yb.to(device)

                optimizer.zero_grad(set_to_none=True)
                logits = model(xb)
                loss = criterion(logits, yb)
                loss.backward()
                nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
                optimizer.step()
                if scheduler is not None:
                    scheduler.step()
                ema.update(model)
                step_count += 1

            # Evaluate on validation with EMA weights
            val_acc = evaluate_accuracy(ema.module(), val_loader, device)
            if val_acc > best_val_acc + 1e-5:
                best_val_acc = val_acc
                best_state = copy.deepcopy(ema.state_dict())
                epochs_no_improve = 0
            else:
                epochs_no_improve += 1
                if epochs_no_improve >= patience:
                    break

        # Load best EMA weights
        ema.load_state_dict(best_state)
        final_model = ema.module()
        final_model.eval()
        return final_model
