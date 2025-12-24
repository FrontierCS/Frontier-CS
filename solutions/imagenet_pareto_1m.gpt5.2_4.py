import os
import math
import time
from typing import Dict, Tuple, List, Optional

import torch
import torch.nn as nn
from torch.utils.data import TensorDataset, DataLoader


def _count_trainable_params(model: nn.Module) -> int:
    return sum(p.numel() for p in model.parameters() if p.requires_grad)


def _unpack_batch(batch):
    if isinstance(batch, (list, tuple)):
        if len(batch) >= 2:
            return batch[0], batch[1]
    raise ValueError("Unsupported batch format")


@torch.no_grad()
def _materialize_loader(loader) -> Tuple[torch.Tensor, torch.Tensor]:
    xs = []
    ys = []
    for batch in loader:
        x, y = _unpack_batch(batch)
        if not torch.is_tensor(x):
            x = torch.as_tensor(x)
        if not torch.is_tensor(y):
            y = torch.as_tensor(y)
        xs.append(x.detach().cpu())
        ys.append(y.detach().cpu())
    x_all = torch.cat(xs, dim=0)
    y_all = torch.cat(ys, dim=0)
    return x_all, y_all


@torch.no_grad()
def _compute_mean_std(x: torch.Tensor, eps: float = 1e-6) -> Tuple[torch.Tensor, torch.Tensor]:
    x = x.float()
    mean = x.mean(dim=0)
    var = x.var(dim=0, unbiased=False)
    std = torch.sqrt(var + eps)
    std = torch.clamp(std, min=eps)
    return mean, std


class _BottleneckResBlock(nn.Module):
    def __init__(self, width: int, bottleneck: int, dropout: float):
        super().__init__()
        self.ln = nn.LayerNorm(width)
        self.fc1 = nn.Linear(width, bottleneck, bias=True)
        self.fc2 = nn.Linear(bottleneck, width, bias=True)
        self.act = nn.GELU()
        self.drop = nn.Dropout(dropout)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        y = self.ln(x)
        y = self.fc1(y)
        y = self.act(y)
        y = self.drop(y)
        y = self.fc2(y)
        y = self.drop(y)
        return x + y


class _NormalizedMLP(nn.Module):
    def __init__(
        self,
        input_dim: int,
        num_classes: int,
        width: int,
        bottleneck: int,
        n_blocks: int,
        dropout: float,
        noise_std: float,
        mean: torch.Tensor,
        std: torch.Tensor,
    ):
        super().__init__()
        self.input_dim = int(input_dim)
        self.num_classes = int(num_classes)
        self.width = int(width)
        self.bottleneck = int(bottleneck)
        self.n_blocks = int(n_blocks)
        self.dropout_p = float(dropout)
        self.noise_std = float(noise_std)

        self.register_buffer("mean", mean.float().view(1, -1), persistent=True)
        self.register_buffer("std", std.float().view(1, -1), persistent=True)

        self.ln0 = nn.LayerNorm(input_dim)
        self.fc_in = nn.Linear(input_dim, width, bias=True)
        self.act = nn.GELU()
        self.drop = nn.Dropout(dropout)

        self.blocks = nn.ModuleList([_BottleneckResBlock(width, bottleneck, dropout) for _ in range(n_blocks)])
        self.ln_final = nn.LayerNorm(width)
        self.fc_out = nn.Linear(width, num_classes, bias=True)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        if x.dim() > 2:
            x = x.view(x.size(0), -1)
        x = x.float()
        x = (x - self.mean) / self.std

        if self.training and self.noise_std > 0.0:
            x = x + torch.randn_like(x) * self.noise_std

        x = self.ln0(x)
        x = self.fc_in(x)
        x = self.act(x)
        x = self.drop(x)

        for blk in self.blocks:
            x = blk(x)

        x = self.ln_final(x)
        x = self.fc_out(x)
        return x


class _EMA:
    def __init__(self, model: nn.Module, decay: float = 0.995):
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
            if p.requires_grad:
                self.shadow[name].mul_(d).add_(p.detach(), alpha=(1.0 - d))

    @torch.no_grad()
    def apply_shadow(self, model: nn.Module):
        self.backup = {}
        for name, p in model.named_parameters():
            if p.requires_grad:
                self.backup[name] = p.detach().clone()
                p.data.copy_(self.shadow[name])

    @torch.no_grad()
    def restore(self, model: nn.Module):
        for name, p in model.named_parameters():
            if p.requires_grad and name in self.backup:
                p.data.copy_(self.backup[name])
        self.backup = {}


@torch.no_grad()
def _accuracy(model: nn.Module, loader: DataLoader, device: torch.device) -> float:
    model.eval()
    correct = 0
    total = 0
    for x, y in loader:
        x = x.to(device, non_blocking=False)
        y = y.to(device, non_blocking=False)
        logits = model(x)
        pred = logits.argmax(dim=1)
        correct += (pred == y).sum().item()
        total += y.numel()
    return float(correct) / float(total) if total > 0 else 0.0


def _estimate_params(input_dim: int, num_classes: int, width: int, bottleneck: int, n_blocks: int) -> int:
    # ln0: 2*input_dim
    # fc_in: input_dim*width + width
    # each block: ln 2*width + fc1 (width*b + b) + fc2 (b*width + width) = 2*width*b + 3*width + b
    # ln_final: 2*width
    # fc_out: width*num_classes + num_classes
    return (
        2 * input_dim
        + (input_dim * width + width)
        + n_blocks * (2 * width * bottleneck + 3 * width + bottleneck)
        + 2 * width
        + (width * num_classes + num_classes)
    )


def _select_configs(input_dim: int, num_classes: int, param_limit: int) -> List[Tuple[int, int, int, int]]:
    n_blocks_candidates = [2, 3, 4]
    bottleneck_candidates = [96, 128, 160, 192, 224, 240, 256, 288]
    max_width = 1024
    width_step = 16

    configs = []
    for n_blocks in n_blocks_candidates:
        for b in bottleneck_candidates:
            best_w = None
            best_p = None
            for w in range(256, max_width + 1, width_step):
                p = _estimate_params(input_dim, num_classes, w, b, n_blocks)
                if p <= param_limit:
                    best_w = w
                    best_p = p
                else:
                    break
            if best_w is None:
                continue
            util = best_p / float(param_limit)
            capacity = (best_w * b * n_blocks)
            heuristic = capacity * (0.25 + 0.75 * util)
            configs.append((heuristic, best_p, best_w, b, n_blocks))

    if not configs:
        # fallback minimal
        w, b, n_blocks = 256, 128, 2
        p = _estimate_params(input_dim, num_classes, w, b, n_blocks)
        return [(p, w, b, n_blocks)]

    configs.sort(reverse=True, key=lambda t: t[0])

    chosen = []
    seen = set()
    for _, p, w, b, n in configs:
        key = (w, b, n)
        if key in seen:
            continue
        seen.add(key)
        chosen.append((p, w, b, n))
        if len(chosen) >= 3:
            break
    return chosen


def _make_mem_loader(x: torch.Tensor, y: torch.Tensor, batch_size: int, shuffle: bool) -> DataLoader:
    ds = TensorDataset(x, y)
    return DataLoader(ds, batch_size=batch_size, shuffle=shuffle, num_workers=0, pin_memory=False, drop_last=False)


def _train_model(
    input_dim: int,
    num_classes: int,
    param_limit: int,
    train_x: torch.Tensor,
    train_y: torch.Tensor,
    val_x: torch.Tensor,
    val_y: torch.Tensor,
    width: int,
    bottleneck: int,
    n_blocks: int,
    mean: torch.Tensor,
    std: torch.Tensor,
    device: torch.device,
    max_epochs: int,
    patience: int,
    lr: float,
    weight_decay: float,
    dropout: float,
    noise_std: float,
    label_smoothing: float,
    ema_decay: float,
    time_limit_s: Optional[float] = None,
) -> Tuple[nn.Module, float]:
    model = _NormalizedMLP(
        input_dim=input_dim,
        num_classes=num_classes,
        width=width,
        bottleneck=bottleneck,
        n_blocks=n_blocks,
        dropout=dropout,
        noise_std=noise_std,
        mean=mean,
        std=std,
    ).to(device)

    pcount = _count_trainable_params(model)
    if pcount > param_limit:
        # emergency shrink
        scale = math.sqrt(param_limit / float(pcount))
        new_width = max(128, int((width * scale) // 16 * 16))
        if new_width < 128:
            new_width = 128
        model = _NormalizedMLP(
            input_dim=input_dim,
            num_classes=num_classes,
            width=new_width,
            bottleneck=min(bottleneck, max(64, new_width // 2)),
            n_blocks=n_blocks,
            dropout=dropout,
            noise_std=noise_std,
            mean=mean,
            std=std,
        ).to(device)
        pcount = _count_trainable_params(model)
        if pcount > param_limit:
            # final fallback: simple 2-layer
            hidden = max(128, min(768, int(math.floor((param_limit / float(input_dim + num_classes))))))
            model = nn.Sequential(
                nn.LayerNorm(input_dim),
                nn.Linear(input_dim, hidden),
                nn.GELU(),
                nn.Dropout(dropout),
                nn.Linear(hidden, num_classes),
            ).to(device)

    pcount = _count_trainable_params(model)
    if pcount > param_limit:
        # cannot proceed
        return model, 0.0

    batch_size = int(min(256, train_x.size(0)))
    train_loader = _make_mem_loader(train_x, train_y, batch_size=batch_size, shuffle=True)
    val_loader = _make_mem_loader(val_x, val_y, batch_size=512, shuffle=False)

    optimizer = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=weight_decay, betas=(0.9, 0.98), eps=1e-8)
    steps_per_epoch = max(1, len(train_loader))
    total_steps = max(1, steps_per_epoch * max_epochs)
    scheduler = torch.optim.lr_scheduler.OneCycleLR(
        optimizer,
        max_lr=lr,
        total_steps=total_steps,
        pct_start=0.12,
        anneal_strategy="cos",
        div_factor=10.0,
        final_div_factor=80.0,
    )
    criterion = nn.CrossEntropyLoss(label_smoothing=label_smoothing)

    ema = _EMA(model, decay=ema_decay)

    best_acc = -1.0
    best_shadow = None
    bad_epochs = 0

    start_t = time.time()
    step_idx = 0

    for epoch in range(max_epochs):
        if time_limit_s is not None and (time.time() - start_t) > time_limit_s:
            break

        model.train()
        for xb, yb in train_loader:
            xb = xb.to(device, non_blocking=False)
            yb = yb.to(device, non_blocking=False)

            optimizer.zero_grad(set_to_none=True)
            logits = model(xb)
            loss = criterion(logits, yb)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
            scheduler.step()
            ema.update(model)

            step_idx += 1
            if time_limit_s is not None and (time.time() - start_t) > time_limit_s:
                break

        ema.apply_shadow(model)
        va = _accuracy(model, val_loader, device)
        ema.restore(model)

        if va > best_acc + 1e-6:
            best_acc = va
            best_shadow = {k: v.detach().clone() for k, v in ema.shadow.items()}
            bad_epochs = 0
        else:
            bad_epochs += 1
            if bad_epochs >= patience:
                break

    if best_shadow is not None and isinstance(model, nn.Module):
        with torch.no_grad():
            for name, p in model.named_parameters():
                if p.requires_grad and name in best_shadow:
                    p.data.copy_(best_shadow[name])

    model.eval()
    return model, float(best_acc)


class Solution:
    def solve(self, train_loader, val_loader, metadata: dict = None) -> torch.nn.Module:
        if metadata is None:
            metadata = {}
        input_dim = int(metadata.get("input_dim", 384))
        num_classes = int(metadata.get("num_classes", 128))
        param_limit = int(metadata.get("param_limit", 1_000_000))
        device_str = str(metadata.get("device", "cpu"))

        try:
            torch.set_num_threads(min(8, os.cpu_count() or 8))
            torch.set_num_interop_threads(1)
        except Exception:
            pass

        device = torch.device(device_str)

        torch.manual_seed(0)

        train_x, train_y = _materialize_loader(train_loader)
        val_x, val_y = _materialize_loader(val_loader)

        mean, std = _compute_mean_std(train_x)

        configs = _select_configs(input_dim, num_classes, param_limit)

        time_budget = 3300.0
        t0 = time.time()

        best_cfg = None
        best_cfg_acc = -1.0

        search_epochs = 35
        search_patience = 10

        for (p, w, b, n) in configs:
            remaining = time_budget - (time.time() - t0)
            if remaining < 300:
                break
            m, acc = _train_model(
                input_dim=input_dim,
                num_classes=num_classes,
                param_limit=param_limit,
                train_x=train_x,
                train_y=train_y,
                val_x=val_x,
                val_y=val_y,
                width=w,
                bottleneck=b,
                n_blocks=n,
                mean=mean,
                std=std,
                device=device,
                max_epochs=search_epochs,
                patience=search_patience,
                lr=3.0e-3,
                weight_decay=8.0e-3,
                dropout=0.10,
                noise_std=0.02,
                label_smoothing=0.06,
                ema_decay=0.995,
                time_limit_s=min(remaining, 900.0),
            )
            del m
            if acc > best_cfg_acc:
                best_cfg_acc = acc
                best_cfg = (w, b, n)

        if best_cfg is None:
            best_cfg = (640, 256, 2)

        w, b, n = best_cfg

        remaining = time_budget - (time.time() - t0)
        final_epochs = 220
        final_patience = 35
        if remaining < 600:
            final_epochs = 140
            final_patience = 25

        model, _ = _train_model(
            input_dim=input_dim,
            num_classes=num_classes,
            param_limit=param_limit,
            train_x=train_x,
            train_y=train_y,
            val_x=val_x,
            val_y=val_y,
            width=w,
            bottleneck=b,
            n_blocks=n,
            mean=mean,
            std=std,
            device=device,
            max_epochs=final_epochs,
            patience=final_patience,
            lr=3.2e-3,
            weight_decay=7.0e-3,
            dropout=0.08,
            noise_std=0.015,
            label_smoothing=0.05,
            ema_decay=0.996,
            time_limit_s=max(60.0, remaining - 60.0),
        )

        if _count_trainable_params(model) > param_limit:
            # absolute safe fallback
            hidden = 768
            fallback = nn.Sequential(
                nn.LayerNorm(input_dim),
                nn.Linear(input_dim, hidden),
                nn.GELU(),
                nn.Linear(hidden, num_classes),
            ).to(device)
            model = fallback

        model.eval()
        return model.to(device)
