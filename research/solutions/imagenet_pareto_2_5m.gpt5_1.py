import math
import copy
import random
from typing import Tuple

import torch
import torch.nn as nn
import torch.nn.functional as F


def set_seed(seed: int = 42):
    random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)


def count_parameters(model: nn.Module) -> int:
    return sum(p.numel() for p in model.parameters() if p.requires_grad)


class DropPath(nn.Module):
    def __init__(self, drop_prob: float = 0.0):
        super().__init__()
        self.drop_prob = float(drop_prob)

    def forward(self, x):
        if self.drop_prob == 0.0 or not self.training:
            return x
        keep_prob = 1.0 - self.drop_prob
        shape = (x.shape[0],) + (1,) * (x.ndim - 1)
        random_tensor = x.new_empty(shape).bernoulli_(keep_prob)
        random_tensor = random_tensor.div(keep_prob)
        return x * random_tensor


class BottleneckBlock(nn.Module):
    def __init__(self, dim: int, hidden_dim: int, drop: float = 0.0, drop_path: float = 0.0, layer_scale_init: float = 1.0):
        super().__init__()
        self.norm = nn.LayerNorm(dim)
        self.fc1 = nn.Linear(dim, hidden_dim, bias=True)
        self.act = nn.GELU()
        self.fc2 = nn.Linear(hidden_dim, dim, bias=True)
        self.drop = nn.Dropout(drop)
        self.drop_path = DropPath(drop_path)
        self.gamma = nn.Parameter(torch.ones(dim) * layer_scale_init)

    def forward(self, x):
        residual = x
        y = self.norm(x)
        y = self.fc1(y)
        y = self.act(y)
        y = self.drop(y)
        y = self.fc2(y)
        y = self.drop(y)
        y = y * self.gamma
        y = self.drop_path(y)
        return residual + y


class MLPResNet(nn.Module):
    def __init__(
        self,
        input_dim: int,
        num_classes: int,
        width: int = 1024,
        num_blocks: int = 3,
        bottleneck_dim: int = 256,
        dropout: float = 0.1,
        drop_path_rate: float = 0.05,
    ):
        super().__init__()
        self.ln_in = nn.LayerNorm(input_dim)
        self.fc_in = nn.Linear(input_dim, width)
        self.act = nn.GELU()
        self.drop_in = nn.Dropout(dropout)

        dpr = [drop_path_rate * i / max(1, num_blocks - 1) for i in range(num_blocks)] if num_blocks > 0 else []
        blocks = []
        for i in range(num_blocks):
            blocks.append(BottleneckBlock(width, bottleneck_dim, drop=dropout, drop_path=dpr[i] if i < len(dpr) else 0.0, layer_scale_init=1.0))
        self.blocks = nn.ModuleList(blocks)

        self.ln_out = nn.LayerNorm(width)
        self.fc_out = nn.Linear(width, num_classes)

    def forward(self, x):
        x = self.ln_in(x)
        x = self.fc_in(x)
        x = self.act(x)
        x = self.drop_in(x)
        for blk in self.blocks:
            x = blk(x)
        x = self.ln_out(x)
        x = self.fc_out(x)
        return x


def choose_architecture(input_dim: int, num_classes: int, param_limit: int) -> Tuple[int, int, int]:
    # Return (width, num_blocks, bottleneck_dim) within param limit
    def base_params(W: int) -> int:
        # 2*input_dim (LN in) + W*(input_dim+1) (fc_in) + 2*W (LN out) + W*num_classes + num_classes (head)
        return 2 * input_dim + W * (input_dim + 1) + 2 * W + W * num_classes + num_classes

    def block_params(W: int, r: int) -> int:
        # LayerNorm (2*W) + Linear1 (W*r + r) + Linear2 (r*W + W)
        return 2 * W + (W * r + r) + (r * W + W)

    # Candidate widths prioritized from larger to smaller
    candidate_widths = [1280, 1152, 1024, 896, 768, 640, 512, 448, 384, 320, 256, 192, 160]
    best = None

    for W in candidate_widths:
        p0 = base_params(W)
        if p0 > param_limit:
            continue

        # Target blocks
        for B in [4, 3, 2, 1, 0]:
            if B == 0:
                # simple MLP without residual blocks
                total = p0
                if total <= param_limit:
                    # Keep best by preferring higher W
                    cand = (W, 0, 0)
                    if best is None:
                        best = cand
                    else:
                        if W > best[0]:
                            best = cand
                continue

            # Choose r as large as possible
            # Pblock(W, r) = (2W + 1)r + 3W
            leftover = param_limit - p0
            per_block_fixed = 3 * W
            per_block_coeff = 2 * W + 1
            max_r = (leftover // B - per_block_fixed) // per_block_coeff
            # Minimal reasonable r
            r_min = max(64, W // 8)
            if max_r < r_min:
                continue
            # Avoid overly large r; keep r <= W
            r = int(min(max_r, W))
            # ensure under limit
            total = p0 + B * block_params(W, r)
            while total > param_limit and r > r_min:
                r -= 1
                total = p0 + B * block_params(W, r)
            if total <= param_limit and r >= r_min:
                cand = (W, B, r)
                if best is None:
                    best = cand
                else:
                    # Prefer more params usage and higher W
                    # Compute params usage
                    cur_total = base_params(best[0]) + best[1] * block_params(best[0], best[2]) if best[1] > 0 else base_params(best[0])
                    new_total = total
                    if (new_total > cur_total) or (new_total == cur_total and W > best[0]):
                        best = cand
                break  # found a good config for this width; move on

    if best is None:
        # Fallback: minimal width using just a single hidden layer - fit under limit
        # Solve for W in base_params(W) <= limit => W <= (param_limit - (2*D + C)) / (D + C + 3)
        denom = input_dim + num_classes + 3
        numerator = param_limit - (2 * input_dim + num_classes)
        W = max(64, min(1024, int(numerator // denom))) if denom > 0 else 256
        W = max(64, W)
        return W, 0, 0

    return best


def build_model(input_dim: int, num_classes: int, param_limit: int) -> nn.Module:
    width, num_blocks, bottleneck_dim = choose_architecture(input_dim, num_classes, param_limit)
    model = MLPResNet(
        input_dim=input_dim,
        num_classes=num_classes,
        width=width,
        num_blocks=num_blocks,
        bottleneck_dim=bottleneck_dim if bottleneck_dim > 0 else max(64, width // 8),
        dropout=0.12,
        drop_path_rate=0.05 if num_blocks > 1 else 0.0,
    )
    # Ensure under limit; adjust if necessary
    current_params = count_parameters(model)
    if current_params > param_limit:
        # Try reducing bottleneck_dim down to fit
        if num_blocks > 0:
            r = model.blocks[0].fc1.out_features
            while current_params > param_limit and r > 32:
                r -= 1
                model = MLPResNet(input_dim, num_classes, width, num_blocks, r, dropout=0.12, drop_path_rate=0.05 if num_blocks > 1 else 0.0)
                current_params = count_parameters(model)
        # If still over, reduce width
        width = model.fc_in.out_features
        while current_params > param_limit and width > 128:
            width -= 32
            r = max(32, width // 8)
            model = MLPResNet(input_dim, num_classes, width, num_blocks, r, dropout=0.12, drop_path_rate=0.05 if num_blocks > 1 else 0.0)
            current_params = count_parameters(model)
    return model


def get_optimizer(model: nn.Module, lr: float = 0.003, weight_decay: float = 0.02) -> torch.optim.Optimizer:
    decay_params = []
    no_decay_params = []
    for n, p in model.named_parameters():
        if not p.requires_grad:
            continue
        if p.ndim <= 1:
            no_decay_params.append(p)
        else:
            decay_params.append(p)

    optimizer = torch.optim.AdamW(
        [
            {"params": decay_params, "weight_decay": weight_decay},
            {"params": no_decay_params, "weight_decay": 0.0},
        ],
        lr=lr,
        betas=(0.9, 0.999),
        eps=1e-8,
    )
    return optimizer


def evaluate(model: nn.Module, loader, device: str) -> float:
    model.eval()
    correct = 0
    total = 0
    with torch.no_grad():
        for inputs, targets in loader:
            inputs = inputs.to(device)
            targets = targets.to(device)
            outputs = model(inputs.float())
            preds = outputs.argmax(dim=1)
            correct += (preds == targets).sum().item()
            total += targets.numel()
    return correct / total if total > 0 else 0.0


class EMAHelper:
    def __init__(self, model: nn.Module, decay: float = 0.997):
        self.ema_model = copy.deepcopy(model)
        for p in self.ema_model.parameters():
            p.requires_grad_(False)
        self.decay = decay

    def to(self, device):
        self.ema_model.to(device)

    @torch.no_grad()
    def update(self, model: nn.Module):
        ema_params = [p for p in self.ema_model.parameters() if p.requires_grad is False]
        model_params = [p for p in model.parameters() if p.requires_grad]
        # Use state dict to include all params, not just requires_grad
        with torch.no_grad():
            for ema_p, p in zip(self.ema_model.parameters(), model.parameters()):
                ema_p.mul_(self.decay).add_(p.data, alpha=1.0 - self.decay)
            for ema_b, b in zip(self.ema_model.buffers(), model.buffers()):
                ema_b.copy_(b)

    def state_dict(self):
        return self.ema_model.state_dict()

    def load_state_dict(self, state_dict):
        self.ema_model.load_state_dict(state_dict)


class Solution:
    def solve(self, train_loader, val_loader, metadata: dict = None) -> torch.nn.Module:
        set_seed(42)
        device = metadata.get("device", "cpu") if metadata else "cpu"
        input_dim = metadata.get("input_dim", 384) if metadata else 384
        num_classes = metadata.get("num_classes", 128) if metadata else 128
        param_limit = metadata.get("param_limit", 2_500_000) if metadata else 2_500_000
        train_samples = metadata.get("train_samples", None) if metadata else None

        model = build_model(input_dim, num_classes, param_limit)
        model.to(device)

        # Double-check parameter constraint
        if count_parameters(model) > param_limit:
            # As last resort, return a smaller baseline model
            width = 768
            model = MLPResNet(input_dim, num_classes, width=width, num_blocks=2, bottleneck_dim=max(64, width // 8), dropout=0.1, drop_path_rate=0.03)
            model.to(device)

        # Training hyperparameters
        epochs = 80 if (train_samples is None or train_samples <= 5000) else 50
        lr = 0.003
        weight_decay = 0.02
        grad_clip = 1.0
        label_smoothing = 0.05

        optimizer = get_optimizer(model, lr=lr, weight_decay=weight_decay)
        steps_per_epoch = max(1, len(train_loader))
        try:
            scheduler = torch.optim.lr_scheduler.OneCycleLR(
                optimizer,
                max_lr=lr,
                epochs=epochs,
                steps_per_epoch=steps_per_epoch,
                pct_start=0.15,
                div_factor=10.0,
                final_div_factor=1000.0,
                three_phase=False,
            )
        except Exception:
            scheduler = None

        criterion = nn.CrossEntropyLoss(label_smoothing=label_smoothing)

        ema = EMAHelper(model, decay=0.997)
        ema.to(device)

        best_acc = 0.0
        best_state = None
        best_ema_state = None
        patience = 20
        patience_counter = 0

        for epoch in range(epochs):
            model.train()
            for inputs, targets in train_loader:
                inputs = inputs.to(device)
                targets = targets.to(device)

                optimizer.zero_grad(set_to_none=True)
                outputs = model(inputs.float())
                loss = criterion(outputs, targets)
                loss.backward()
                if grad_clip is not None and grad_clip > 0.0:
                    nn.utils.clip_grad_norm_(model.parameters(), grad_clip)
                optimizer.step()
                if scheduler is not None:
                    scheduler.step()
                ema.update(model)

            # Evaluate using EMA model
            val_acc = evaluate(ema.ema_model, val_loader, device)
            if val_acc > best_acc:
                best_acc = val_acc
                best_state = copy.deepcopy(model.state_dict())
                best_ema_state = copy.deepcopy(ema.state_dict())
                patience_counter = 0
            else:
                patience_counter += 1

            if patience_counter >= patience:
                break

        # Load best EMA weights into a fresh model instance
        final_model = build_model(input_dim, num_classes, param_limit)
        final_model.to(device)
        if best_ema_state is not None:
            final_model.load_state_dict(best_ema_state)
        else:
            final_model.load_state_dict(model.state_dict())

        final_model.eval()
        return final_model
