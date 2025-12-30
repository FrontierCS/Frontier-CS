import os
import math
import copy
import time
from typing import Dict, Optional, Tuple, List

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F


def _set_torch_threads():
    try:
        n = os.cpu_count() or 8
        torch.set_num_threads(min(8, max(1, n)))
        torch.set_num_interop_threads(1)
    except Exception:
        pass


def _count_trainable_params(model: nn.Module) -> int:
    return sum(p.numel() for p in model.parameters() if p.requires_grad)


class InputNorm(nn.Module):
    def __init__(self, mean: torch.Tensor, std: torch.Tensor):
        super().__init__()
        self.register_buffer("mean", mean)
        self.register_buffer("std", std)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        if x.dim() > 2:
            x = x.view(x.size(0), -1)
        return (x - self.mean) / self.std


class WideMLPNet(nn.Module):
    def __init__(self, input_dim: int, num_classes: int, h1: int, h2: int, dropout: float = 0.10):
        super().__init__()
        self.fc1 = nn.Linear(input_dim, h1, bias=True)
        self.ln1 = nn.LayerNorm(h1)
        self.fc2 = nn.Linear(h1, h2, bias=True)
        self.ln2 = nn.LayerNorm(h2)
        self.fc3 = nn.Linear(h2, num_classes, bias=True)
        self.drop = nn.Dropout(dropout)
        self.act = nn.GELU()

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        if x.dim() > 2:
            x = x.view(x.size(0), -1)
        x = self.fc1(x)
        x = self.ln1(x)
        x = self.act(x)
        x = self.drop(x)
        x = self.fc2(x)
        x = self.ln2(x)
        x = self.act(x)
        x = self.drop(x)
        x = self.fc3(x)
        return x


class ResidualFFNBlock(nn.Module):
    def __init__(self, d: int, expansion: int = 2, dropout: float = 0.10):
        super().__init__()
        h = d * expansion
        self.ln = nn.LayerNorm(d)
        self.fc1 = nn.Linear(d, h, bias=True)
        self.fc2 = nn.Linear(h, d, bias=True)
        self.act = nn.GELU()
        self.drop = nn.Dropout(dropout)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        r = x
        x = self.ln(x)
        x = self.fc1(x)
        x = self.act(x)
        x = self.drop(x)
        x = self.fc2(x)
        x = self.drop(x)
        return r + x


class ResMLPNet(nn.Module):
    def __init__(self, input_dim: int, num_classes: int, d: int, n_blocks: int, expansion: int = 2, dropout: float = 0.10):
        super().__init__()
        self.inp = nn.Linear(input_dim, d, bias=True)
        self.blocks = nn.ModuleList([ResidualFFNBlock(d, expansion=expansion, dropout=dropout) for _ in range(n_blocks)])
        self.out_ln = nn.LayerNorm(d)
        self.head = nn.Linear(d, num_classes, bias=True)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        if x.dim() > 2:
            x = x.view(x.size(0), -1)
        x = self.inp(x)
        for b in self.blocks:
            x = b(x)
        x = self.out_ln(x)
        x = self.head(x)
        return x


class EMA:
    def __init__(self, model: nn.Module, decay: float = 0.995):
        self.decay = float(decay)
        self.shadow = {}
        self.backup = {}
        for n, p in model.named_parameters():
            if p.requires_grad:
                self.shadow[n] = p.detach().clone()

    @torch.no_grad()
    def update(self, model: nn.Module):
        d = self.decay
        for n, p in model.named_parameters():
            if p.requires_grad:
                self.shadow[n].mul_(d).add_(p.detach(), alpha=(1.0 - d))

    @torch.no_grad()
    def store(self, model: nn.Module):
        if not self.backup:
            for n, p in model.named_parameters():
                if p.requires_grad:
                    self.backup[n] = p.detach().clone()
        else:
            for n, p in model.named_parameters():
                if p.requires_grad:
                    self.backup[n].copy_(p.detach())

    @torch.no_grad()
    def copy_to(self, model: nn.Module):
        for n, p in model.named_parameters():
            if p.requires_grad:
                p.data.copy_(self.shadow[n])

    @torch.no_grad()
    def restore(self, model: nn.Module):
        for n, p in model.named_parameters():
            if p.requires_grad:
                p.data.copy_(self.backup[n])


def _compute_dataset_norm(train_loader, input_dim: int, device: torch.device) -> Tuple[torch.Tensor, torch.Tensor]:
    s = torch.zeros(input_dim, dtype=torch.float64)
    ss = torch.zeros(input_dim, dtype=torch.float64)
    n = 0
    for xb, _ in train_loader:
        xb = xb.detach()
        if xb.dim() > 2:
            xb = xb.view(xb.size(0), -1)
        xb = xb.to(dtype=torch.float64, device="cpu")
        if xb.size(1) != input_dim:
            xb = xb[:, :input_dim]
        s += xb.sum(dim=0)
        ss += (xb * xb).sum(dim=0)
        n += xb.size(0)
    mean = (s / max(1, n)).to(dtype=torch.float32)
    var = (ss / max(1, n) - mean.to(dtype=torch.float64) ** 2).to(dtype=torch.float32)
    std = torch.sqrt(torch.clamp(var, min=1e-6))
    mean = mean.to(device=device)
    std = std.to(device=device)
    return mean, std


def _accuracy(model: nn.Module, loader, device: torch.device) -> float:
    model.eval()
    correct = 0
    total = 0
    with torch.inference_mode():
        for xb, yb in loader:
            xb = xb.to(device=device, dtype=torch.float32)
            yb = yb.to(device=device, dtype=torch.long)
            logits = model(xb)
            pred = torch.argmax(logits, dim=1)
            correct += (pred == yb).sum().item()
            total += yb.numel()
    return float(correct) / float(max(1, total))


def _set_lr(optimizer: torch.optim.Optimizer, lr: float):
    for pg in optimizer.param_groups:
        pg["lr"] = lr


def _train(
    model: nn.Module,
    train_loader,
    val_loader,
    device: torch.device,
    max_epochs: int,
    base_lr: float,
    weight_decay: float,
    mixup_p: float,
    mixup_alpha: float,
    label_smoothing: float,
    grad_clip: float,
    ema_decay: float,
    patience: int,
    eval_every: int = 1,
    max_seconds: Optional[float] = None,
) -> Tuple[nn.Module, float]:
    model.to(device)
    model.train()

    criterion = nn.CrossEntropyLoss(label_smoothing=float(label_smoothing))
    optimizer = torch.optim.AdamW(model.parameters(), lr=base_lr, weight_decay=weight_decay, betas=(0.9, 0.95), eps=1e-8)

    steps_per_epoch = max(1, len(train_loader))
    total_steps = max_epochs * steps_per_epoch
    warmup_steps = min(200, max(20, total_steps // 20))
    min_lr = base_lr * 0.05

    ema = EMA(model, decay=ema_decay)
    best_acc = -1.0
    best_shadow = None
    bad_epochs = 0

    start_time = time.time()
    global_step = 0

    for epoch in range(max_epochs):
        model.train()
        for xb, yb in train_loader:
            if max_seconds is not None and (time.time() - start_time) > max_seconds:
                break

            xb = xb.to(device=device, dtype=torch.float32)
            yb = yb.to(device=device, dtype=torch.long)

            bs = xb.size(0)
            do_mix = (mixup_p > 0.0) and (bs >= 2) and (np.random.rand() < mixup_p)

            if global_step < warmup_steps:
                lr = base_lr * (global_step + 1) / float(warmup_steps)
            else:
                t = (global_step - warmup_steps) / float(max(1, total_steps - warmup_steps))
                lr = min_lr + (base_lr - min_lr) * 0.5 * (1.0 + math.cos(math.pi * min(1.0, t)))
            _set_lr(optimizer, lr)

            optimizer.zero_grad(set_to_none=True)

            if do_mix:
                lam = float(np.random.beta(mixup_alpha, mixup_alpha))
                perm = torch.randperm(bs, device=device)
                xb2 = xb[perm]
                yb2 = yb[perm]
                xmix = xb.mul(lam).add(xb2, alpha=(1.0 - lam))
                logits = model(xmix)
                loss = lam * criterion(logits, yb) + (1.0 - lam) * criterion(logits, yb2)
            else:
                logits = model(xb)
                loss = criterion(logits, yb)

            loss.backward()
            if grad_clip is not None and grad_clip > 0:
                torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=grad_clip)
            optimizer.step()
            ema.update(model)

            global_step += 1

        if max_seconds is not None and (time.time() - start_time) > max_seconds:
            break

        if val_loader is not None and (epoch + 1) % eval_every == 0:
            ema.store(model)
            ema.copy_to(model)
            val_acc = _accuracy(model, val_loader, device)
            ema.restore(model)

            if val_acc > best_acc + 1e-5:
                best_acc = val_acc
                best_shadow = {k: v.detach().clone() for k, v in ema.shadow.items()}
                bad_epochs = 0
            else:
                bad_epochs += 1

            if best_acc >= 0.999:
                break
            if bad_epochs >= patience:
                break

    if best_shadow is not None:
        with torch.no_grad():
            for n, p in model.named_parameters():
                if p.requires_grad and n in best_shadow:
                    p.data.copy_(best_shadow[n])

    return model, best_acc


def _params_wide_mlp(input_dim: int, num_classes: int, h1: int, h2: int) -> int:
    # Linear + LayerNorm each hidden, biases included
    p = 0
    p += input_dim * h1 + h1  # fc1
    p += 2 * h1  # ln1
    p += h1 * h2 + h2  # fc2
    p += 2 * h2  # ln2
    p += h2 * num_classes + num_classes  # fc3
    return int(p)


def _params_resmlp(input_dim: int, num_classes: int, d: int, n_blocks: int, expansion: int = 2) -> int:
    # inp: (input_dim+1)*d
    # each block: ln 2d + fc1 d*(ed)+ed + fc2 (ed)*d + d = 2d + (e d^2 + e d) + (e d^2 + d) = 2d + 2e d^2 + (e+1)d
    # for e=2 => 2d +4d^2 +3d =4d^2 +5d
    e = expansion
    p = 0
    p += (input_dim + 1) * d
    p += n_blocks * (2 * d + 2 * e * d * d + (e + 1) * d)
    p += 2 * d  # out_ln
    p += d * num_classes + num_classes
    return int(p)


def _choose_wide_mlp_dims(input_dim: int, num_classes: int, param_limit: int) -> Tuple[int, int]:
    candidates = [
        (1024, 512),
        (1024, 448),
        (960, 512),
        (896, 512),
        (896, 448),
        (832, 512),
        (768, 512),
        (768, 448),
        (768, 384),
        (704, 448),
        (640, 512),
        (640, 384),
        (576, 384),
    ]
    best = None
    best_p = -1
    for h1, h2 in candidates:
        if h2 < num_classes:
            continue
        p = _params_wide_mlp(input_dim, num_classes, h1, h2)
        if p <= param_limit and p > best_p:
            best_p = p
            best = (h1, h2)
    if best is None:
        # fallback: keep h2 = max(num_classes, 128) and binary search h1
        h2 = max(num_classes, 128)
        lo, hi = h2, 4096
        while lo < hi:
            mid = (lo + hi + 1) // 2
            p = _params_wide_mlp(input_dim, num_classes, mid, h2)
            if p <= param_limit:
                lo = mid
            else:
                hi = mid - 1
        return lo, h2
    return best


def _choose_resmlp_dims(input_dim: int, num_classes: int, param_limit: int, expansion: int = 2) -> Tuple[int, int]:
    best = None
    best_score = -1.0
    for n_blocks in (6, 5, 4, 3, 2, 1):
        lo, hi = max(64, num_classes), 2048
        while lo < hi:
            mid = (lo + hi + 1) // 2
            p = _params_resmlp(input_dim, num_classes, mid, n_blocks, expansion=expansion)
            if p <= param_limit:
                lo = mid
            else:
                hi = mid - 1
        d = lo
        p = _params_resmlp(input_dim, num_classes, d, n_blocks, expansion=expansion)
        if p <= param_limit:
            # heuristic: prefer using param budget, slight preference for depth
            score = float(p) + 1500.0 * float(n_blocks)
            if score > best_score:
                best_score = score
                best = (d, n_blocks)
    if best is None:
        return max(64, num_classes), 1
    return best


def _build_combined_loader(train_loader, val_loader):
    try:
        from torch.utils.data import ConcatDataset, DataLoader
        if train_loader is None or val_loader is None:
            return None
        if not hasattr(train_loader, "dataset") or not hasattr(val_loader, "dataset"):
            return None
        ds = ConcatDataset([train_loader.dataset, val_loader.dataset])
        bs = getattr(train_loader, "batch_size", None) or 64
        num_workers = getattr(train_loader, "num_workers", 0)
        return DataLoader(ds, batch_size=bs, shuffle=True, num_workers=num_workers, drop_last=False)
    except Exception:
        return None


class Solution:
    def solve(self, train_loader, val_loader, metadata: dict = None) -> torch.nn.Module:
        _set_torch_threads()
        if metadata is None:
            metadata = {}

        device = torch.device(metadata.get("device", "cpu"))
        num_classes = int(metadata.get("num_classes", 128))
        input_dim = int(metadata.get("input_dim", 384))
        param_limit = int(metadata.get("param_limit", 1_000_000))

        torch.manual_seed(0)
        np.random.seed(0)

        mean, std = _compute_dataset_norm(train_loader, input_dim=input_dim, device=device)
        norm = InputNorm(mean, std)

        # Candidates
        h1, h2 = _choose_wide_mlp_dims(input_dim, num_classes, param_limit)
        wide = nn.Sequential(norm, WideMLPNet(input_dim, num_classes, h1=h1, h2=h2, dropout=0.10))

        d, n_blocks = _choose_resmlp_dims(input_dim, num_classes, param_limit, expansion=2)
        res = nn.Sequential(norm, ResMLPNet(input_dim, num_classes, d=d, n_blocks=n_blocks, expansion=2, dropout=0.10))

        # Ensure both are within limit
        if _count_trainable_params(wide) > param_limit:
            # fallback smaller
            wide = nn.Sequential(norm, WideMLPNet(input_dim, num_classes, h1=768, h2=384, dropout=0.10))
        if _count_trainable_params(res) > param_limit:
            res = nn.Sequential(norm, ResMLPNet(input_dim, num_classes, d=max(num_classes, 192), n_blocks=2, expansion=2, dropout=0.10))

        # Quick pilot to pick architecture
        pilot_epochs = 40
        pilot_patience = 10

        # Heuristic LR scaling by batch size
        try:
            first_batch = next(iter(train_loader))[0]
            bs = int(first_batch.size(0))
        except Exception:
            bs = 64
        lr_scale = max(0.5, min(2.0, bs / 64.0))

        candidates: List[Tuple[str, nn.Module, float]] = [
            ("wide", wide, 2.5e-3 * lr_scale),
            ("res", res, 3.0e-3 * lr_scale),
        ]

        best_name = None
        best_acc = -1.0
        best_kind = None

        for name, model, lr in candidates:
            model = copy.deepcopy(model)
            if _count_trainable_params(model) > param_limit:
                continue
            model, vacc = _train(
                model=model,
                train_loader=train_loader,
                val_loader=val_loader,
                device=device,
                max_epochs=pilot_epochs,
                base_lr=lr,
                weight_decay=0.015,
                mixup_p=0.35,
                mixup_alpha=0.20,
                label_smoothing=0.05,
                grad_clip=1.0,
                ema_decay=0.995,
                patience=pilot_patience,
                eval_every=1,
                max_seconds=None,
            )
            if vacc > best_acc:
                best_acc = vacc
                best_name = name
                best_kind = (name, model, lr)

        if best_kind is None:
            model = wide
            final_lr = 2.5e-3 * lr_scale
        else:
            # Rebuild a fresh model of chosen architecture for full training
            if best_name == "wide":
                model = nn.Sequential(norm, WideMLPNet(input_dim, num_classes, h1=h1, h2=h2, dropout=0.10))
                final_lr = 2.5e-3 * lr_scale
            else:
                model = nn.Sequential(norm, ResMLPNet(input_dim, num_classes, d=d, n_blocks=n_blocks, expansion=2, dropout=0.10))
                final_lr = 3.0e-3 * lr_scale

        # Full training
        model, _ = _train(
            model=model,
            train_loader=train_loader,
            val_loader=val_loader,
            device=device,
            max_epochs=220,
            base_lr=final_lr,
            weight_decay=0.02,
            mixup_p=0.40,
            mixup_alpha=0.20,
            label_smoothing=0.06,
            grad_clip=1.0,
            ema_decay=0.996,
            patience=25,
            eval_every=1,
            max_seconds=3300.0,  # keep within overall budget
        )

        # Optional fine-tune on train+val with small LR
        combined = _build_combined_loader(train_loader, val_loader)
        if combined is not None:
            model, _ = _train(
                model=model,
                train_loader=combined,
                val_loader=None,
                device=device,
                max_epochs=20,
                base_lr=final_lr * 0.25,
                weight_decay=0.02,
                mixup_p=0.20,
                mixup_alpha=0.15,
                label_smoothing=0.04,
                grad_clip=1.0,
                ema_decay=0.998,
                patience=9999,
                eval_every=9999,
                max_seconds=3500.0,
            )

        # Final safety: if over limit, fall back to a smaller wide MLP
        if _count_trainable_params(model) > param_limit:
            h1s, h2s = _choose_wide_mlp_dims(input_dim, num_classes, param_limit - 4096)
            model = nn.Sequential(norm, WideMLPNet(input_dim, num_classes, h1=h1s, h2=h2s, dropout=0.10)).to(device)
            model, _ = _train(
                model=model,
                train_loader=train_loader,
                val_loader=val_loader,
                device=device,
                max_epochs=160,
                base_lr=2.5e-3 * lr_scale,
                weight_decay=0.02,
                mixup_p=0.35,
                mixup_alpha=0.20,
                label_smoothing=0.06,
                grad_clip=1.0,
                ema_decay=0.996,
                patience=20,
                eval_every=1,
                max_seconds=3500.0,
            )

        model.to(device)
        model.eval()
        return model