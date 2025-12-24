import math
import os
import random
from copy import deepcopy
from typing import Dict, Optional, Tuple

import torch
import torch.nn as nn


def _count_trainable_params(model: nn.Module) -> int:
    return sum(p.numel() for p in model.parameters() if p.requires_grad)


class _EMA:
    def __init__(self, model: nn.Module, decay: float = 0.999):
        self.decay = float(decay)
        self.shadow = {}
        self.backup = {}
        with torch.no_grad():
            for name, p in model.named_parameters():
                if p.requires_grad:
                    self.shadow[name] = p.detach().clone()

    @torch.no_grad()
    def update(self, model: nn.Module):
        d = self.decay
        for name, p in model.named_parameters():
            if not p.requires_grad:
                continue
            sp = self.shadow.get(name, None)
            if sp is None:
                self.shadow[name] = p.detach().clone()
            else:
                sp.mul_(d).add_(p.detach(), alpha=(1.0 - d))

    @torch.no_grad()
    def apply_to(self, model: nn.Module):
        self.backup = {}
        for name, p in model.named_parameters():
            if not p.requires_grad:
                continue
            self.backup[name] = p.detach().clone()
            p.copy_(self.shadow[name])

    @torch.no_grad()
    def restore(self, model: nn.Module):
        for name, p in model.named_parameters():
            if not p.requires_grad:
                continue
            bp = self.backup.get(name, None)
            if bp is not None:
                p.copy_(bp)
        self.backup = {}

    def state_dict(self):
        return {k: v.clone() for k, v in self.shadow.items()}

    @torch.no_grad()
    def load_state_dict(self, state):
        self.shadow = {k: v.clone() for k, v in state.items()}


class _ResidualLinearBlock(nn.Module):
    def __init__(self, dim: int, dropout: float):
        super().__init__()
        self.ln = nn.LayerNorm(dim)
        self.fc = nn.Linear(dim, dim)
        self.act = nn.GELU()
        self.drop = nn.Dropout(dropout)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        y = self.ln(x)
        y = self.fc(y)
        y = self.act(y)
        y = self.drop(y)
        x = x + y
        x = self.act(x)
        return x


class _MLPNet(nn.Module):
    def __init__(self, input_dim: int, num_classes: int, h1: int, h2: int, num_blocks: int = 2,
                 dropout: float = 0.10, input_dropout: float = 0.05):
        super().__init__()
        self.input_dim = int(input_dim)
        self.num_classes = int(num_classes)

        self.register_buffer("x_mean", torch.zeros(self.input_dim, dtype=torch.float32))
        self.register_buffer("x_std", torch.ones(self.input_dim, dtype=torch.float32))

        self.in_drop = nn.Dropout(input_dropout)
        self.ln0 = nn.LayerNorm(self.input_dim)
        self.fc1 = nn.Linear(self.input_dim, h1)
        self.drop1 = nn.Dropout(dropout)

        self.ln1 = nn.LayerNorm(h1)
        self.fc2 = nn.Linear(h1, h2)
        self.drop2 = nn.Dropout(dropout)

        self.blocks = nn.ModuleList([_ResidualLinearBlock(h2, dropout) for _ in range(int(num_blocks))])
        self.ln_out = nn.LayerNorm(h2)
        self.head = nn.Linear(h2, self.num_classes)

        self._init_weights()

    def _init_weights(self):
        for m in self.modules():
            if isinstance(m, nn.Linear):
                nn.init.kaiming_normal_(m.weight, nonlinearity="relu")
                if m.bias is not None:
                    nn.init.zeros_(m.bias)

    def set_input_stats(self, mean: torch.Tensor, std: torch.Tensor):
        with torch.no_grad():
            mean = mean.to(dtype=torch.float32).view(-1)
            std = std.to(dtype=torch.float32).view(-1)
            if mean.numel() != self.input_dim or std.numel() != self.input_dim:
                return
            self.x_mean.copy_(mean)
            self.x_std.copy_(std)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        if x.dim() > 2:
            x = x.view(x.size(0), -1)
        x = x.to(dtype=torch.float32)
        x = (x - self.x_mean) / (self.x_std + 1e-6)

        if self.training:
            x = self.in_drop(x)

        x = self.ln0(x)
        x = self.fc1(x)
        x = torch.nn.functional.gelu(x)
        x = self.drop1(x)

        x = self.ln1(x)
        x = self.fc2(x)
        x = torch.nn.functional.gelu(x)
        x = self.drop2(x)

        for blk in self.blocks:
            x = blk(x)

        x = self.ln_out(x)
        logits = self.head(x)
        return logits


def _compute_input_stats(train_loader, input_dim: int, device: torch.device) -> Tuple[torch.Tensor, torch.Tensor]:
    s = torch.zeros(input_dim, dtype=torch.float64, device=device)
    ss = torch.zeros(input_dim, dtype=torch.float64, device=device)
    n = 0
    for xb, _ in train_loader:
        if xb.dim() > 2:
            xb = xb.view(xb.size(0), -1)
        xb = xb.to(device=device, dtype=torch.float64)
        if xb.size(1) != input_dim:
            xb = xb[:, :input_dim] if xb.size(1) > input_dim else torch.nn.functional.pad(xb, (0, input_dim - xb.size(1)))
        s += xb.sum(dim=0)
        ss += (xb * xb).sum(dim=0)
        n += xb.size(0)
    if n <= 1:
        mean = torch.zeros(input_dim, dtype=torch.float32, device=device)
        std = torch.ones(input_dim, dtype=torch.float32, device=device)
        return mean, std
    mean = s / float(n)
    var = (ss / float(n)) - mean * mean
    var = torch.clamp(var, min=1e-6)
    std = torch.sqrt(var)
    return mean.to(dtype=torch.float32), std.to(dtype=torch.float32)


@torch.no_grad()
def _accuracy(model: nn.Module, loader, device: torch.device) -> float:
    model.eval()
    correct = 0
    total = 0
    for xb, yb in loader:
        if xb.dim() > 2:
            xb = xb.view(xb.size(0), -1)
        xb = xb.to(device=device, dtype=torch.float32)
        yb = yb.to(device=device, dtype=torch.long)
        logits = model(xb)
        pred = logits.argmax(dim=1)
        correct += (pred == yb).sum().item()
        total += yb.numel()
    return float(correct) / float(max(1, total))


def _pick_arch(input_dim: int, num_classes: int, param_limit: int, num_blocks: int = 2) -> Tuple[int, int, int]:
    D = int(input_dim)
    C = int(num_classes)
    L = int(param_limit)
    k = int(num_blocks)

    def total_params(h1: int, h2: int) -> int:
        # Linear1: D*h1 + h1
        # Linear2: h1*h2 + h2
        # Blocks: k*(h2*h2 + h2)
        # Head: h2*C + C
        # LayerNorms: ln0(D), ln1(h1), each block ln(h2) => k, ln_out(h2) => total D + h1 + (k+1)*h2 dims, each has weight+bias => *2
        return (
            D * h1 + h1 +
            h1 * h2 + h2 +
            k * (h2 * h2 + h2) +
            h2 * C + C +
            2 * (D + h1 + (k + 1) * h2)
        )

    best = None
    best_score = -1.0

    h2_min = max(128, (D * 5) // 12)
    h2_max = min(384, max(h2_min + 8, (D * 11) // 10))

    for h2 in range((h2_min // 8) * 8, h2_max + 1, 8):
        const = (
            h2 +                      # linear2 bias
            k * (h2 * h2 + h2) +      # blocks
            h2 * C + C +              # head
            2 * (D + (k + 1) * h2)    # layernorm constant part (excluding 2*h1)
        )
        denom = D + h2 + 3  # coefficient of h1 in total (D*h1 + h1*h2 + h1 + 2*h1)
        if L <= const + denom * D:
            continue
        h1 = (L - const) // denom
        h1 = int(max(D, min(h1, 1024)))
        p = total_params(h1, h2)
        if p > L:
            while h1 > D and total_params(h1, h2) > L:
                h1 -= 1
            p = total_params(h1, h2)
        if p > L or h1 < D:
            continue

        # prefer slightly expanding first layer and a moderately sized bottleneck
        ratio_penalty = abs((h1 / max(1.0, D)) - 1.35) + 0.35 * abs((h2 / max(1.0, D)) - 0.67)
        utilization = p / float(L)
        score = utilization - 0.15 * ratio_penalty

        if score > best_score:
            best_score = score
            best = (h1, h2, p)

    if best is None:
        h1 = min(512, max(D, 2 * D))
        h2 = min(256, max(128, D // 2))
        while total_params(h1, h2) > L and h1 > D:
            h1 -= 8
        while total_params(h1, h2) > L and h2 > 64:
            h2 -= 8
        return h1, h2, total_params(h1, h2)

    return best[0], best[1], best[2]


class Solution:
    def solve(self, train_loader, val_loader, metadata: dict = None) -> torch.nn.Module:
        if metadata is None:
            metadata = {}
        input_dim = int(metadata.get("input_dim", 384))
        num_classes = int(metadata.get("num_classes", 128))
        param_limit = int(metadata.get("param_limit", 500_000))
        device_str = metadata.get("device", "cpu")
        device = torch.device(device_str if device_str else "cpu")

        try:
            nthreads = min(8, (os.cpu_count() or 8))
            torch.set_num_threads(nthreads)
            torch.set_num_interop_threads(1)
        except Exception:
            pass

        seed = 0
        random.seed(seed)
        torch.manual_seed(seed)

        num_blocks = 2
        h1, h2, _ = _pick_arch(input_dim, num_classes, param_limit, num_blocks=num_blocks)

        model = _MLPNet(
            input_dim=input_dim,
            num_classes=num_classes,
            h1=h1,
            h2=h2,
            num_blocks=num_blocks,
            dropout=0.10,
            input_dropout=0.05,
        ).to(device)

        if _count_trainable_params(model) > param_limit:
            # Safety fallback: reduce widths
            while _count_trainable_params(model) > param_limit and h1 > input_dim:
                h1 = max(input_dim, h1 - 8)
                model = _MLPNet(input_dim, num_classes, h1, h2, num_blocks=num_blocks).to(device)
            while _count_trainable_params(model) > param_limit and h2 > 64:
                h2 = max(64, h2 - 8)
                model = _MLPNet(input_dim, num_classes, h1, h2, num_blocks=num_blocks).to(device)

        mean, std = _compute_input_stats(train_loader, input_dim, device=device)
        model.set_input_stats(mean, std)

        if val_loader is None:
            model.eval()
            return model

        ce = nn.CrossEntropyLoss(label_smoothing=0.10)

        base_lr = 3.5e-3
        weight_decay = 0.02
        optimizer = torch.optim.AdamW(model.parameters(), lr=base_lr, weight_decay=weight_decay, betas=(0.9, 0.98))

        steps_per_epoch = max(1, len(train_loader))
        max_epochs = 180
        total_steps = max_epochs * steps_per_epoch
        warmup_steps = max(20, int(0.08 * total_steps))

        def lr_mult(step: int) -> float:
            if step < warmup_steps:
                return float(step + 1) / float(warmup_steps)
            t = float(step - warmup_steps) / float(max(1, total_steps - warmup_steps))
            return 0.5 * (1.0 + math.cos(math.pi * min(1.0, t)))

        scheduler = torch.optim.lr_scheduler.LambdaLR(optimizer, lr_lambda=lr_mult)

        ema = _EMA(model, decay=0.996)

        best_ema_state = None
        best_val = -1.0
        best_epoch = -1
        patience = 28

        beta_dist = torch.distributions.Beta(torch.tensor(0.4), torch.tensor(0.4))

        global_step = 0
        for epoch in range(max_epochs):
            model.train()
            for xb, yb in train_loader:
                if xb.dim() > 2:
                    xb = xb.view(xb.size(0), -1)
                xb = xb.to(device=device, dtype=torch.float32)
                yb = yb.to(device=device, dtype=torch.long)

                if xb.size(0) >= 2 and random.random() < 0.85:
                    lam = float(beta_dist.sample().item())
                    perm = torch.randperm(xb.size(0), device=device)
                    x2 = xb[perm]
                    y2 = yb[perm]
                    xm = lam * xb + (1.0 - lam) * x2
                    optimizer.zero_grad(set_to_none=True)
                    logits = model(xm)
                    loss = lam * ce(logits, yb) + (1.0 - lam) * ce(logits, y2)
                else:
                    optimizer.zero_grad(set_to_none=True)
                    logits = model(xb)
                    loss = ce(logits, yb)

                loss.backward()
                torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
                optimizer.step()
                ema.update(model)
                scheduler.step()
                global_step += 1

            if (epoch + 1) % 1 == 0:
                ema.apply_to(model)
                val_acc = _accuracy(model, val_loader, device=device)
                ema.restore(model)

                if val_acc > best_val + 1e-6:
                    best_val = val_acc
                    best_epoch = epoch
                    best_ema_state = ema.state_dict()
                elif epoch - best_epoch >= patience:
                    break

        if best_ema_state is not None:
            ema.load_state_dict(best_ema_state)
            ema.apply_to(model)
            ema.restore(model)
            with torch.no_grad():
                for name, p in model.named_parameters():
                    if p.requires_grad and name in best_ema_state:
                        p.copy_(best_ema_state[name].to(device=device))

        model.eval()
        return model
