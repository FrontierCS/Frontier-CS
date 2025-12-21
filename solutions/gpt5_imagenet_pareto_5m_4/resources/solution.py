import math
import random
import copy
import time
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F


def set_seed(seed: int = 42):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)


def count_trainable_params(model: nn.Module) -> int:
    return sum(p.numel() for p in model.parameters() if p.requires_grad)


class ResidualSingle(nn.Module):
    def __init__(self, dim: int, pdrop: float = 0.1):
        super().__init__()
        self.norm = nn.LayerNorm(dim)
        self.linear = nn.Linear(dim, dim, bias=False)
        self.act = nn.GELU()
        self.drop = nn.Dropout(pdrop)

    def forward(self, x):
        y = self.norm(x)
        y = self.linear(y)
        y = self.act(y)
        y = self.drop(y)
        return x + y


class MLPResNet(nn.Module):
    def __init__(self, input_dim: int, num_classes: int, width: int, blocks: int, pdrop: float = 0.1):
        super().__init__()
        self.in_norm = nn.LayerNorm(input_dim)
        self.in_proj = nn.Linear(input_dim, width, bias=False)
        self.post_in_norm = nn.LayerNorm(width)
        self.blocks = nn.ModuleList([ResidualSingle(width, pdrop=pdrop) for _ in range(blocks)])
        self.pre_head_norm = nn.LayerNorm(width)
        self.head = nn.Linear(width, num_classes, bias=True)
        self.drop_in = nn.Dropout(pdrop * 0.5)

    def forward(self, x):
        # x: (batch, input_dim)
        x = self.in_norm(x)
        x = self.in_proj(x)
        x = self.post_in_norm(x)
        x = self.drop_in(x)
        for blk in self.blocks:
            x = blk(x)
        x = self.pre_head_norm(x)
        x = self.head(x)
        return x


def estimate_params_formula(input_dim: int, num_classes: int, width: int, blocks: int) -> int:
    # Trainable parameter estimate (exact for our architecture)
    # Params = 2*input_dim (input LayerNorm) +
    #          input_dim*width (in_proj, no bias) +
    #          2*width (post_in_norm) +
    #          blocks*(width*width + 2*width) (linear no bias + LayerNorm) +
    #          2*width (pre_head_norm) +
    #          width*num_classes + num_classes (head weights + bias)
    return (
        2 * input_dim +
        input_dim * width +
        2 * width +
        blocks * (width * width + 2 * width) +
        2 * width +
        width * num_classes +
        num_classes
    )


def solve_width_for_blocks(input_dim: int, num_classes: int, blocks: int, param_limit: int) -> int:
    # Solve quadratic: a*H^2 + b*H + c <= limit
    # a = blocks
    # b = input_dim + num_classes + 2*blocks + 4
    # c = 2*input_dim + num_classes
    a = blocks
    b = input_dim + num_classes + 2 * blocks + 4
    c = 2 * input_dim + num_classes
    # Solve a*H^2 + b*H + c - param_limit <= 0
    # H = floor((-b + sqrt(b^2 - 4*a*(c - param_limit))) / (2a))
    if a == 0:
        # No H^2 term; degenerate, but shouldn't happen since blocks>=1
        max_h = (param_limit - c) // max(b, 1)
        return max(1, int(max_h))
    disc = b * b - 4 * a * (c - param_limit)
    if disc < 0:
        return 0
    h = int(( -b + math.isqrt(int(disc)) ) // (2 * a))
    if h < 0:
        return 0
    return h


def build_best_model(input_dim: int, num_classes: int, param_limit: int, pdrop: float = 0.1):
    # Search over number of residual single-layer blocks; choose configuration that
    # fits under param limit and maximizes parameter usage.
    # Reasonable range for blocks: 3..6
    best = None
    best_params = -1
    best_cfg = None

    for blocks in [6, 5, 4, 3]:
        est_h = solve_width_for_blocks(input_dim, num_classes, blocks, param_limit)
        # Ensure we step down a bit to account for integer rounding
        width = max(8, est_h)
        # Try decreasing width until actual params <= limit
        while width >= 8:
            params_est = estimate_params_formula(input_dim, num_classes, width, blocks)
            if params_est <= param_limit:
                # Construct model and double-check count
                model = MLPResNet(input_dim, num_classes, width, blocks, pdrop=pdrop)
                actual = count_trainable_params(model)
                if actual <= param_limit:
                    if actual > best_params:
                        best = model
                        best_params = actual
                        best_cfg = (width, blocks)
                    break
            width -= 1

    if best is None:
        # Fallback minimal model
        blocks = 2
        width = 256
        best = MLPResNet(input_dim, num_classes, width, blocks, pdrop=pdrop)
    return best


@torch.no_grad()
def update_ema_model(ema_model: nn.Module, model: nn.Module, decay: float = 0.99):
    for ema_p, p in zip(ema_model.parameters(), model.parameters()):
        ema_p.mul_(decay).add_(p.detach(), alpha=1.0 - decay)
    # Copy buffers (LayerNorm has no running stats, but for completeness)
    for ema_buf, buf in zip(ema_model.buffers(), model.buffers()):
        ema_buf.copy_(buf)


def evaluate_accuracy(model: nn.Module, data_loader, device: torch.device) -> float:
    model.eval()
    correct = 0
    total = 0
    with torch.no_grad():
        for inputs, targets in data_loader:
            inputs = inputs.to(device)
            targets = targets.to(device)
            outputs = model(inputs)
            preds = outputs.argmax(dim=1)
            correct += (preds == targets).sum().item()
            total += targets.numel()
    if total == 0:
        return 0.0
    return correct / total


class Solution:
    def solve(self, train_loader, val_loader, metadata: dict = None) -> torch.nn.Module:
        set_seed(42)
        if metadata is None:
            metadata = {}
        input_dim = int(metadata.get("input_dim", 384))
        num_classes = int(metadata.get("num_classes", 128))
        param_limit = int(metadata.get("param_limit", 5_000_000))
        device_str = metadata.get("device", "cpu")
        device = torch.device(device_str if torch.cuda.is_available() else "cpu")

        # Build model near parameter limit
        model = build_best_model(input_dim, num_classes, param_limit, pdrop=0.15)
        model.to(device)
        # Double-check parameter constraint
        if count_trainable_params(model) > param_limit:
            # As safety fallback, reduce width
            width = 768
            blocks = 3
            model = MLPResNet(input_dim, num_classes, width, blocks, pdrop=0.15).to(device)

        # EMA model
        ema_model = copy.deepcopy(model).to(device)
        for p in ema_model.parameters():
            p.requires_grad_(False)

        # Training setup
        epochs = 180
        patience = 35
        steps_per_epoch = max(1, len(train_loader))
        total_steps = epochs * steps_per_epoch

        # Optimizer
        optimizer = torch.optim.AdamW(model.parameters(), lr=3e-3, weight_decay=5e-4, betas=(0.9, 0.98))
        # OneCycleLR scheduler
        scheduler = torch.optim.lr_scheduler.OneCycleLR(
            optimizer,
            max_lr=3e-3,
            total_steps=total_steps,
            pct_start=0.15,
            div_factor=25.0,
            final_div_factor=1000.0,
            anneal_strategy='cos'
        )
        criterion = nn.CrossEntropyLoss(label_smoothing=0.05)

        best_acc = -1.0
        best_state = None
        best_ema_state = None
        epochs_no_improve = 0

        start_time = time.time()
        max_time = 55 * 60  # safety: 55 minutes

        for epoch in range(epochs):
            model.train()
            for inputs, targets in train_loader:
                inputs = inputs.to(device)
                targets = targets.to(device)

                optimizer.zero_grad(set_to_none=True)
                outputs = model(inputs)
                loss = criterion(outputs, targets)
                loss.backward()
                torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
                optimizer.step()
                scheduler.step()

                # EMA update
                update_ema_model(ema_model, model, decay=0.99)

            # Validation
            if val_loader is not None:
                ema_model.eval()
                val_acc = evaluate_accuracy(ema_model, val_loader, device)
                if val_acc > best_acc:
                    best_acc = val_acc
                    best_state = copy.deepcopy(model.state_dict())
                    best_ema_state = copy.deepcopy(ema_model.state_dict())
                    epochs_no_improve = 0
                else:
                    epochs_no_improve += 1

                if epochs_no_improve >= patience:
                    break

            # Time safety
            if (time.time() - start_time) > max_time:
                break

        # Load best EMA weights if available
        if best_ema_state is not None:
            ema_model.load_state_dict(best_ema_state)
            final_model = ema_model
        else:
            final_model = model

        final_model.to(device)
        final_model.eval()
        return final_model
