import math
import os
import random
import copy
from typing import Optional, Tuple, Dict

import torch
import torch.nn as nn
import torch.nn.functional as F


def _count_trainable_params(m: nn.Module) -> int:
    return sum(p.numel() for p in m.parameters() if p.requires_grad)


def _loader_to_tensors(loader) -> Tuple[torch.Tensor, torch.Tensor]:
    xs = []
    ys = []
    for xb, yb in loader:
        if not torch.is_tensor(xb):
            xb = torch.as_tensor(xb)
        if not torch.is_tensor(yb):
            yb = torch.as_tensor(yb)
        xb = xb.float()
        if yb.ndim > 1:
            yb = yb.argmax(dim=-1)
        yb = yb.long()
        xs.append(xb)
        ys.append(yb)
    if not xs:
        return torch.empty(0), torch.empty(0, dtype=torch.long)
    x = torch.cat(xs, dim=0).contiguous()
    y = torch.cat(ys, dim=0).contiguous()
    return x, y


def _iterate_minibatches(x: torch.Tensor, y: torch.Tensor, batch_size: int, shuffle: bool) -> Tuple[torch.Tensor, torch.Tensor]:
    n = x.shape[0]
    if shuffle:
        idx = torch.randperm(n, device=x.device)
    else:
        idx = torch.arange(n, device=x.device)
    for start in range(0, n, batch_size):
        sl = idx[start:start + batch_size]
        yield x[sl], y[sl]


def _ce_with_label_smoothing(logits: torch.Tensor, targets: torch.Tensor, eps: float) -> torch.Tensor:
    if eps <= 0.0:
        return F.cross_entropy(logits, targets)
    log_probs = F.log_softmax(logits, dim=1)
    nll = -log_probs.gather(1, targets.view(-1, 1)).squeeze(1).mean()
    smooth = -log_probs.mean(dim=1).mean()
    return (1.0 - eps) * nll + eps * smooth


@torch.no_grad()
def _ema_update(model: nn.Module, ema_model: nn.Module, decay: float) -> None:
    msd = model.state_dict()
    esd = ema_model.state_dict()
    for k, v in esd.items():
        mv = msd[k]
        if torch.is_floating_point(v):
            v.mul_(decay).add_(mv, alpha=1.0 - decay)
        else:
            v.copy_(mv)


@torch.inference_mode()
def _accuracy(model: nn.Module, x: torch.Tensor, y: torch.Tensor, batch_size: int = 512) -> float:
    if x.numel() == 0:
        return 0.0
    model.eval()
    n = x.shape[0]
    correct = 0
    for i in range(0, n, batch_size):
        xb = x[i:i + batch_size]
        yb = y[i:i + batch_size]
        logits = model(xb)
        pred = logits.argmax(dim=1)
        correct += (pred == yb).sum().item()
    return correct / n


class _CosineHead(nn.Module):
    def __init__(self, in_features: int, out_features: int, init_scale: float = 12.0):
        super().__init__()
        self.weight = nn.Parameter(torch.empty(out_features, in_features))
        self.scale = nn.Parameter(torch.tensor(float(init_scale)))
        nn.init.kaiming_uniform_(self.weight, a=math.sqrt(5))

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = F.normalize(x, dim=-1)
        w = F.normalize(self.weight, dim=-1)
        return (x @ w.t()) * self.scale


class _BottleneckResidualBlock(nn.Module):
    def __init__(self, width: int, bottleneck: int, dropout: float):
        super().__init__()
        self.ln = nn.LayerNorm(width)
        self.fc1 = nn.Linear(width, bottleneck, bias=True)
        self.fc2 = nn.Linear(bottleneck, width, bias=True)
        self.drop1 = nn.Dropout(dropout)
        self.drop2 = nn.Dropout(dropout)
        self.skip_scale = nn.Parameter(torch.tensor(1.0))

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        y = self.ln(x)
        y = self.fc1(y)
        y = F.gelu(y)
        y = self.drop1(y)
        y = self.fc2(y)
        y = self.drop2(y)
        return x + self.skip_scale * y


class _Net(nn.Module):
    def __init__(
        self,
        input_dim: int,
        num_classes: int,
        width: int,
        bottleneck: int,
        num_blocks: int,
        num_heads: int,
        dropout: float,
    ):
        super().__init__()
        self.register_buffer("mu", torch.zeros(input_dim))
        self.register_buffer("sigma", torch.ones(input_dim))

        self.fc_in = nn.Linear(input_dim, width, bias=True)
        self.drop_in = nn.Dropout(dropout)

        self.blocks = nn.ModuleList([
            _BottleneckResidualBlock(width, bottleneck, dropout) for _ in range(num_blocks)
        ])

        self.ln_out = nn.LayerNorm(width)
        self.heads = nn.ModuleList([_CosineHead(width, num_classes) for _ in range(num_heads)])

    def set_normalization(self, mu: torch.Tensor, sigma: torch.Tensor) -> None:
        with torch.no_grad():
            self.mu.copy_(mu)
            self.sigma.copy_(sigma)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = x.float()
        x = (x - self.mu) / self.sigma
        x = self.fc_in(x)
        x = F.gelu(x)
        x = self.drop_in(x)
        for blk in self.blocks:
            x = blk(x)
        x = self.ln_out(x)
        x = F.gelu(x)
        if len(self.heads) == 1:
            return self.heads[0](x)
        logits = None
        for h in self.heads:
            z = h(x)
            logits = z if logits is None else (logits + z)
        return logits / float(len(self.heads))


class Solution:
    def solve(self, train_loader, val_loader, metadata: dict = None) -> torch.nn.Module:
        if metadata is None:
            metadata = {}
        device = torch.device(str(metadata.get("device", "cpu")))
        input_dim = int(metadata.get("input_dim", 384))
        num_classes = int(metadata.get("num_classes", 128))
        param_limit = int(metadata.get("param_limit", 5_000_000))

        try:
            torch.set_num_threads(min(8, os.cpu_count() or 8))
        except Exception:
            pass

        torch.manual_seed(0)
        random.seed(0)

        x_train, y_train = _loader_to_tensors(train_loader)
        x_val, y_val = _loader_to_tensors(val_loader) if val_loader is not None else (torch.empty(0), torch.empty(0, dtype=torch.long))

        x_train = x_train.to(device=device, dtype=torch.float32, non_blocking=False)
        y_train = y_train.to(device=device, dtype=torch.long, non_blocking=False)
        x_val = x_val.to(device=device, dtype=torch.float32, non_blocking=False)
        y_val = y_val.to(device=device, dtype=torch.long, non_blocking=False)

        with torch.no_grad():
            mu = x_train.mean(dim=0)
            sigma = x_train.std(dim=0).clamp_min(1e-4)

        width = 1536
        bottleneck = 320
        num_blocks = 4
        num_heads = 2
        dropout = 0.06

        def build_model(w: int, b: int, nb: int, nh: int) -> _Net:
            m = _Net(
                input_dim=input_dim,
                num_classes=num_classes,
                width=w,
                bottleneck=b,
                num_blocks=nb,
                num_heads=nh,
                dropout=dropout,
            ).to(device)
            m.set_normalization(mu, sigma)
            return m

        model = build_model(width, bottleneck, num_blocks, num_heads)

        while _count_trainable_params(model) > param_limit:
            if num_heads > 1:
                num_heads -= 1
            elif bottleneck > 256:
                bottleneck -= 32
            elif num_blocks > 2:
                num_blocks -= 1
            elif width > 1024:
                width -= 64
            else:
                break
            model = build_model(width, bottleneck, num_blocks, num_heads)

        if _count_trainable_params(model) > param_limit:
            num_heads = 1
            num_blocks = 2
            bottleneck = 256
            width = 1024
            model = build_model(width, bottleneck, num_blocks, num_heads)

        ema_model = copy.deepcopy(model).to(device)
        for p in ema_model.parameters():
            p.requires_grad_(False)

        batch_size = 256
        if x_train.shape[0] >= 1024:
            batch_size = 256
        elif x_train.shape[0] >= 512:
            batch_size = 128
        else:
            batch_size = 64

        lr = 2.5e-3
        weight_decay = 1.5e-2
        label_smoothing = 0.02
        mixup_alpha = 0.12
        ema_decay = 0.995

        epochs = 220
        patience = 28
        min_epochs = 50

        steps_per_epoch = max(1, (x_train.shape[0] + batch_size - 1) // batch_size)
        total_steps = epochs * steps_per_epoch
        warmup_steps = max(10, int(0.06 * total_steps))

        optimizer = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=weight_decay, betas=(0.9, 0.99))

        def lr_lambda(step: int) -> float:
            if step < warmup_steps:
                return float(step + 1) / float(warmup_steps)
            t = (step - warmup_steps) / float(max(1, total_steps - warmup_steps))
            return 0.5 * (1.0 + math.cos(math.pi * t))

        scheduler = torch.optim.lr_scheduler.LambdaLR(optimizer, lr_lambda=lr_lambda)

        best_val = -1.0
        best_state = None
        bad = 0
        global_step = 0

        for epoch in range(epochs):
            model.train()
            for xb, yb in _iterate_minibatches(x_train, y_train, batch_size, shuffle=True):
                if mixup_alpha > 0.0 and xb.shape[0] >= 2:
                    lam = random.betavariate(mixup_alpha, mixup_alpha)
                    perm = torch.randperm(xb.shape[0], device=xb.device)
                    xmix = xb.mul(lam).add_(xb[perm], alpha=(1.0 - lam))
                    ya = yb
                    yb2 = yb[perm]
                    logits = model(xmix)
                    loss = lam * _ce_with_label_smoothing(logits, ya, label_smoothing) + (1.0 - lam) * _ce_with_label_smoothing(logits, yb2, label_smoothing)
                else:
                    logits = model(xb)
                    loss = _ce_with_label_smoothing(logits, yb, label_smoothing)

                optimizer.zero_grad(set_to_none=True)
                loss.backward()
                torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
                optimizer.step()
                scheduler.step()
                global_step += 1

                _ema_update(model, ema_model, ema_decay)

            val_acc = _accuracy(ema_model, x_val, y_val, batch_size=512) if x_val.numel() else _accuracy(ema_model, x_train, y_train, batch_size=512)

            if val_acc > best_val + 1e-6:
                best_val = val_acc
                best_state = copy.deepcopy(ema_model.state_dict())
                bad = 0
            else:
                bad += 1

            if epoch + 1 >= min_epochs and bad >= patience:
                break

        if best_state is not None:
            ema_model.load_state_dict(best_state, strict=True)
            model.load_state_dict(best_state, strict=True)

        if x_val.numel() > 0:
            x_ft = torch.cat([x_train, x_val], dim=0)
            y_ft = torch.cat([y_train, y_val], dim=0)
        else:
            x_ft, y_ft = x_train, y_train

        ft_epochs = 35
        ft_lr = lr * 0.35
        ft_weight_decay = weight_decay * 0.8
        ft_label_smoothing = 0.01
        ft_mixup_alpha = 0.08
        ft_ema_decay = 0.996

        optimizer = torch.optim.AdamW(model.parameters(), lr=ft_lr, weight_decay=ft_weight_decay, betas=(0.9, 0.99))
        steps_per_epoch = max(1, (x_ft.shape[0] + batch_size - 1) // batch_size)
        total_steps = ft_epochs * steps_per_epoch
        warmup_steps = max(5, int(0.08 * total_steps))

        def lr_lambda2(step: int) -> float:
            if step < warmup_steps:
                return float(step + 1) / float(warmup_steps)
            t = (step - warmup_steps) / float(max(1, total_steps - warmup_steps))
            return 0.5 * (1.0 + math.cos(math.pi * t))

        scheduler = torch.optim.lr_scheduler.LambdaLR(optimizer, lr_lambda=lr_lambda2)

        for epoch in range(ft_epochs):
            model.train()
            for xb, yb in _iterate_minibatches(x_ft, y_ft, batch_size, shuffle=True):
                if ft_mixup_alpha > 0.0 and xb.shape[0] >= 2:
                    lam = random.betavariate(ft_mixup_alpha, ft_mixup_alpha)
                    perm = torch.randperm(xb.shape[0], device=xb.device)
                    xmix = xb.mul(lam).add_(xb[perm], alpha=(1.0 - lam))
                    ya = yb
                    yb2 = yb[perm]
                    logits = model(xmix)
                    loss = lam * _ce_with_label_smoothing(logits, ya, ft_label_smoothing) + (1.0 - lam) * _ce_with_label_smoothing(logits, yb2, ft_label_smoothing)
                else:
                    logits = model(xb)
                    loss = _ce_with_label_smoothing(logits, yb, ft_label_smoothing)

                optimizer.zero_grad(set_to_none=True)
                loss.backward()
                torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
                optimizer.step()
                scheduler.step()
                _ema_update(model, ema_model, ft_ema_decay)

        model.load_state_dict(ema_model.state_dict(), strict=True)
        model.eval()
        return model