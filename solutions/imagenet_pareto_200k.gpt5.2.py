import math
import random
from typing import Dict, Optional, Tuple

import torch
import torch.nn as nn
import torch.nn.functional as F


def _count_trainable_params(model: nn.Module) -> int:
    return sum(p.numel() for p in model.parameters() if p.requires_grad)


@torch.no_grad()
def _compute_input_norm(train_loader, input_dim: int, device: torch.device) -> Tuple[torch.Tensor, torch.Tensor]:
    s = torch.zeros(input_dim, dtype=torch.float64, device=device)
    ss = torch.zeros(input_dim, dtype=torch.float64, device=device)
    n = 0
    for xb, _ in train_loader:
        xb = xb.to(device=device)
        xb = xb.view(xb.size(0), -1).to(dtype=torch.float64)
        if xb.size(1) != input_dim:
            input_dim = xb.size(1)
            s = torch.zeros(input_dim, dtype=torch.float64, device=device)
            ss = torch.zeros(input_dim, dtype=torch.float64, device=device)
        s += xb.sum(dim=0)
        ss += (xb * xb).sum(dim=0)
        n += xb.size(0)
    if n == 0:
        mean = torch.zeros(input_dim, dtype=torch.float32, device=device)
        std = torch.ones(input_dim, dtype=torch.float32, device=device)
        return mean, std
    mean = s / n
    var = (ss / n) - mean * mean
    var = torch.clamp(var, min=1e-12)
    std = torch.sqrt(var + 1e-6)
    std = torch.where(std > 1e-6, std, torch.ones_like(std))
    return mean.to(dtype=torch.float32), std.to(dtype=torch.float32)


class _CosineClassifier(nn.Module):
    def __init__(self, in_features: int, num_classes: int, init_scale: float = 12.0):
        super().__init__()
        self.weight = nn.Parameter(torch.empty(num_classes, in_features))
        nn.init.normal_(self.weight, mean=0.0, std=0.02)
        self.log_scale = nn.Parameter(torch.tensor(float(init_scale)))

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = F.normalize(x, dim=1, eps=1e-8)
        w = F.normalize(self.weight, dim=1, eps=1e-8)
        scale = F.softplus(self.log_scale)
        return (x @ w.t()) * scale


class _ResMLP(nn.Module):
    def __init__(
        self,
        input_dim: int,
        num_classes: int,
        hidden_dim: int,
        num_blocks: int,
        dropout: float,
        in_mean: torch.Tensor,
        in_std: torch.Tensor,
    ):
        super().__init__()
        self.input_dim = int(input_dim)
        self.num_classes = int(num_classes)
        self.hidden_dim = int(hidden_dim)
        self.num_blocks = int(num_blocks)

        self.register_buffer("in_mean", in_mean.view(1, -1).clone())
        self.register_buffer("in_std", in_std.view(1, -1).clone())

        self.fc_in = nn.Linear(self.input_dim, self.hidden_dim, bias=True)
        self.ln_in = nn.LayerNorm(self.hidden_dim)

        self.blocks = nn.ModuleList()
        for _ in range(self.num_blocks):
            self.blocks.append(nn.Linear(self.hidden_dim, self.hidden_dim, bias=True))
            self.blocks.append(nn.LayerNorm(self.hidden_dim))

        self.act = nn.GELU()
        self.drop_in = nn.Dropout(dropout)
        self.drop = nn.Dropout(dropout)

        self.head = _CosineClassifier(self.hidden_dim, self.num_classes, init_scale=12.0)

        self._init_weights()

    def _init_weights(self):
        nn.init.kaiming_normal_(self.fc_in.weight, nonlinearity="linear")
        nn.init.zeros_(self.fc_in.bias)
        for m in self.blocks:
            if isinstance(m, nn.Linear):
                nn.init.kaiming_normal_(m.weight, nonlinearity="linear")
                nn.init.zeros_(m.bias)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = x.view(x.size(0), -1).to(dtype=torch.float32)
        if x.size(1) != self.in_mean.size(1):
            # Fallback: adapt by trunc/pad with zeros if inconsistent (should not happen)
            d = self.in_mean.size(1)
            if x.size(1) > d:
                x = x[:, :d]
            else:
                x = F.pad(x, (0, d - x.size(1)))
        x = (x - self.in_mean) / self.in_std

        h = self.fc_in(x)
        h = self.act(self.ln_in(h))
        h = self.drop_in(h)

        idx = 0
        for _ in range(self.num_blocks):
            lin = self.blocks[idx]
            ln = self.blocks[idx + 1]
            idx += 2
            r = self.act(ln(lin(h)))
            r = self.drop(r)
            h = h + r

        return self.head(h)


class _EMA:
    def __init__(self, model: nn.Module, decay: float = 0.995):
        self.decay = float(decay)
        self.shadow = {}
        self.backup = None
        for name, p in model.named_parameters():
            if p.requires_grad:
                self.shadow[name] = p.detach().clone()

    @torch.no_grad()
    def update(self, model: nn.Module):
        d = self.decay
        for name, p in model.named_parameters():
            if not p.requires_grad:
                continue
            if name not in self.shadow:
                self.shadow[name] = p.detach().clone()
            else:
                self.shadow[name].mul_(d).add_(p.detach(), alpha=(1.0 - d))

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
        if self.backup is None:
            return
        for name, p in model.named_parameters():
            if not p.requires_grad:
                continue
            if name in self.backup:
                p.copy_(self.backup[name])
        self.backup = None

    def shadow_copy(self):
        return {k: v.detach().clone() for k, v in self.shadow.items()}


@torch.no_grad()
def _accuracy(model: nn.Module, loader, device: torch.device) -> float:
    model.eval()
    correct = 0
    total = 0
    with torch.inference_mode():
        for xb, yb in loader:
            xb = xb.to(device=device, dtype=torch.float32)
            yb = yb.to(device=device, dtype=torch.long)
            logits = model(xb)
            pred = logits.argmax(dim=1)
            correct += (pred == yb).sum().item()
            total += yb.numel()
    return float(correct) / float(total) if total > 0 else 0.0


def _soft_cross_entropy(logits: torch.Tensor, y_soft: torch.Tensor) -> torch.Tensor:
    logp = F.log_softmax(logits, dim=1)
    return -(y_soft * logp).sum(dim=1).mean()


def _make_soft_targets(y: torch.Tensor, num_classes: int, smoothing: float) -> torch.Tensor:
    y = y.to(dtype=torch.long)
    y_oh = F.one_hot(y, num_classes=num_classes).to(dtype=torch.float32)
    if smoothing and smoothing > 0.0:
        y_oh = y_oh * (1.0 - smoothing) + (smoothing / float(num_classes))
    return y_oh


def _mixup(x: torch.Tensor, y: torch.Tensor, num_classes: int, alpha: float, smoothing: float) -> Tuple[torch.Tensor, torch.Tensor]:
    if alpha <= 0.0 or x.size(0) <= 1:
        return x, _make_soft_targets(y, num_classes, smoothing)
    dist = torch.distributions.Beta(concentration1=alpha, concentration0=alpha)
    lam = float(dist.sample().item())
    if lam < 0.5:
        lam = 1.0 - lam
    perm = torch.randperm(x.size(0), device=x.device)
    x2 = x[perm]
    y2 = y[perm]
    y1s = _make_soft_targets(y, num_classes, smoothing)
    y2s = _make_soft_targets(y2, num_classes, smoothing)
    xm = x.mul(lam).add(x2, alpha=(1.0 - lam))
    ym = y1s.mul(lam).add(y2s, alpha=(1.0 - lam))
    return xm, ym


def _auto_hidden_dim(input_dim: int, num_classes: int, param_limit: int, num_blocks: int) -> int:
    # Params (trainable) for architecture:
    # fc_in: input_dim*h + h
    # ln_in: 2h
    # blocks: num_blocks * (h*h + h + 2h) = num_blocks*(h*h + 3h)
    # head (cosine): num_classes*h + 1
    # total: num_blocks*h^2 + (input_dim + num_classes + 3 + 3*num_blocks)*h + 1
    a = num_blocks
    b = (input_dim + num_classes + 3 + 3 * num_blocks)
    c = 1 - param_limit
    # Solve a*h^2 + b*h + c <= 0 for h
    if a <= 0:
        h = (param_limit - 1) // max(1, (input_dim + num_classes + 3))
        return max(16, int(h))
    disc = b * b - 4 * a * c
    if disc <= 0:
        return 16
    h = int(((-b + math.sqrt(float(disc))) / (2 * a)))
    return max(16, h)


class Solution:
    def solve(self, train_loader, val_loader, metadata: dict = None) -> nn.Module:
        if metadata is None:
            metadata = {}
        device_str = metadata.get("device", "cpu")
        device = torch.device(device_str)

        try:
            torch.set_num_threads(min(8, max(1, torch.get_num_threads())))
        except Exception:
            pass

        torch.manual_seed(0)
        random.seed(0)

        # Infer dimensions if missing
        input_dim = int(metadata.get("input_dim", 0) or 0)
        num_classes = int(metadata.get("num_classes", 0) or 0)
        param_limit = int(metadata.get("param_limit", 200000))

        if input_dim <= 0 or num_classes <= 0:
            for xb, yb in train_loader:
                xb = xb.view(xb.size(0), -1)
                if input_dim <= 0:
                    input_dim = int(xb.size(1))
                if num_classes <= 0:
                    num_classes = int(yb.max().item() + 1) if yb.numel() > 0 else 128
                break
            if input_dim <= 0:
                input_dim = 384
            if num_classes <= 0:
                num_classes = 128

        in_mean, in_std = _compute_input_norm(train_loader, input_dim=input_dim, device=device)

        # Architecture choice (fixed blocks, maximize hidden under budget)
        num_blocks = 3
        hidden_dim = _auto_hidden_dim(input_dim, num_classes, param_limit, num_blocks)
        # Nudge to a nice size (keep near max)
        hidden_dim = min(hidden_dim, 256)
        # Make sure within limit
        dropout = 0.10

        model = _ResMLP(
            input_dim=input_dim,
            num_classes=num_classes,
            hidden_dim=hidden_dim,
            num_blocks=num_blocks,
            dropout=dropout,
            in_mean=in_mean.to(device=device),
            in_std=in_std.to(device=device),
        ).to(device)

        # If over limit (unlikely due to formula), back off
        while _count_trainable_params(model) > param_limit and hidden_dim > 16:
            hidden_dim -= 1
            model = _ResMLP(
                input_dim=input_dim,
                num_classes=num_classes,
                hidden_dim=hidden_dim,
                num_blocks=num_blocks,
                dropout=dropout,
                in_mean=in_mean.to(device=device),
                in_std=in_std.to(device=device),
            ).to(device)

        # Training hyperparams
        max_epochs = 320
        patience = 45
        base_lr = 3e-3
        min_lr = 3.5e-4
        weight_decay = 2e-2
        grad_clip = 1.0
        label_smoothing = 0.08
        mixup_alpha_base = 0.35
        ema = _EMA(model, decay=0.995)

        optimizer = torch.optim.AdamW(model.parameters(), lr=base_lr, weight_decay=weight_decay, betas=(0.9, 0.99))

        steps_per_epoch = max(1, len(train_loader))
        total_steps = max(1, max_epochs * steps_per_epoch)
        warmup_steps = max(20, int(0.08 * total_steps))

        def lr_at(step: int) -> float:
            if step < warmup_steps:
                return base_lr * float(step + 1) / float(warmup_steps)
            t = float(step - warmup_steps) / float(max(1, total_steps - warmup_steps))
            t = max(0.0, min(1.0, t))
            cos = 0.5 * (1.0 + math.cos(math.pi * t))
            return min_lr + (base_lr - min_lr) * cos

        best_acc = -1.0
        best_shadow = None
        bad_epochs = 0
        global_step = 0

        for epoch in range(max_epochs):
            model.train()
            # Decay mixup strength over time
            frac = epoch / float(max_epochs)
            mixup_alpha = mixup_alpha_base * max(0.0, 1.0 - frac / 0.9)
            do_mixup = mixup_alpha >= 0.06 and epoch < int(0.85 * max_epochs)
            mixup_prob = 0.85 if do_mixup else 0.0

            for xb, yb in train_loader:
                xb = xb.to(device=device, dtype=torch.float32)
                yb = yb.to(device=device, dtype=torch.long)

                for pg in optimizer.param_groups:
                    pg["lr"] = lr_at(global_step)

                optimizer.zero_grad(set_to_none=True)

                if mixup_prob > 0.0 and xb.size(0) > 1 and random.random() < mixup_prob:
                    xm, ys = _mixup(xb, yb, num_classes=num_classes, alpha=mixup_alpha, smoothing=label_smoothing)
                    logits = model(xm)
                    loss = _soft_cross_entropy(logits, ys)
                else:
                    ys = _make_soft_targets(yb, num_classes=num_classes, smoothing=label_smoothing)
                    logits = model(xb)
                    loss = _soft_cross_entropy(logits, ys)

                loss.backward()
                if grad_clip and grad_clip > 0:
                    torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=grad_clip)
                optimizer.step()
                ema.update(model)

                global_step += 1

            # Validate with EMA weights
            ema.apply_to(model)
            val_acc = _accuracy(model, val_loader, device)
            ema.restore(model)

            if val_acc > best_acc + 1e-4:
                best_acc = val_acc
                best_shadow = ema.shadow_copy()
                bad_epochs = 0
            else:
                bad_epochs += 1
                if bad_epochs >= patience:
                    break

        if best_shadow is not None:
            with torch.no_grad():
                for name, p in model.named_parameters():
                    if p.requires_grad and name in best_shadow:
                        p.copy_(best_shadow[name])

        model.eval()
        return model
