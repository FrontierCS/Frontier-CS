import math
import os
from dataclasses import dataclass
from typing import Optional, Tuple, Dict

import torch
import torch.nn as nn
import torch.nn.functional as F


def _count_trainable_params(model: nn.Module) -> int:
    return sum(p.numel() for p in model.parameters() if p.requires_grad)


def _gather_from_loader(loader) -> Tuple[torch.Tensor, torch.Tensor]:
    xs = []
    ys = []
    for batch in loader:
        if isinstance(batch, (list, tuple)) and len(batch) >= 2:
            x, y = batch[0], batch[1]
        else:
            raise ValueError("Expected loader to yield (inputs, targets).")
        xs.append(x.detach().to(dtype=torch.float32, device="cpu"))
        ys.append(y.detach().to(dtype=torch.long, device="cpu"))
    x = torch.cat(xs, dim=0)
    y = torch.cat(ys, dim=0)
    return x, y


class BottleneckResidual(nn.Module):
    def __init__(self, dim: int, hidden_dim: int, dropout: float):
        super().__init__()
        self.norm = nn.LayerNorm(dim)
        self.fc1 = nn.Linear(dim, hidden_dim, bias=True)
        self.act = nn.GELU()
        self.drop1 = nn.Dropout(dropout)
        self.fc2 = nn.Linear(hidden_dim, dim, bias=True)
        self.drop2 = nn.Dropout(dropout)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        y = self.norm(x)
        y = self.fc1(y)
        y = self.act(y)
        y = self.drop1(y)
        y = self.fc2(y)
        y = self.drop2(y)
        return x + y


class CosineHead(nn.Module):
    def __init__(self, in_dim: int, num_classes: int, init_scale: float = 20.0):
        super().__init__()
        self.weight = nn.Parameter(torch.empty(num_classes, in_dim))
        nn.init.normal_(self.weight, mean=0.0, std=0.02)
        self.logit_scale = nn.Parameter(torch.tensor(float(init_scale)).log())

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = F.normalize(x, dim=1)
        w = F.normalize(self.weight, dim=1)
        scale = self.logit_scale.exp().clamp(1.0, 100.0)
        return scale * (x @ w.t())


class ResMLPClassifier(nn.Module):
    def __init__(
        self,
        input_dim: int,
        num_classes: int,
        width: int,
        num_blocks: int,
        bottleneck: int,
        dropout: float,
        mean: torch.Tensor,
        std: torch.Tensor,
    ):
        super().__init__()
        self.input_dim = input_dim
        self.num_classes = num_classes
        self.width = width
        self.num_blocks = num_blocks
        self.bottleneck = bottleneck

        self.register_buffer("mean", mean.clone().detach().to(dtype=torch.float32), persistent=False)
        self.register_buffer("std", std.clone().detach().to(dtype=torch.float32), persistent=False)

        self.in_norm = nn.LayerNorm(input_dim)
        self.stem = nn.Linear(input_dim, width, bias=True)

        self.blocks = nn.ModuleList(
            [BottleneckResidual(width, bottleneck, dropout=dropout) for _ in range(num_blocks)]
        )

        self.head_norm = nn.LayerNorm(width)
        self.head = CosineHead(width, num_classes, init_scale=25.0)

    def encode(self, x: torch.Tensor) -> torch.Tensor:
        x = x.to(dtype=torch.float32)
        x = (x - self.mean) / self.std
        x = self.in_norm(x)
        x = self.stem(x)
        for blk in self.blocks:
            x = blk(x)
        x = self.head_norm(x)
        return x

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self.encode(x)
        return self.head(x)


def _estimate_params(
    input_dim: int,
    num_classes: int,
    width: int,
    num_blocks: int,
    bottleneck: int,
    use_input_ln: bool = True,
    use_head_ln: bool = True,
    cosine_head: bool = True,
) -> int:
    total = 0
    if use_input_ln:
        total += 2 * input_dim
    total += input_dim * width + width  # stem
    for _ in range(num_blocks):
        total += 2 * width  # LN
        total += width * bottleneck + bottleneck  # fc1
        total += bottleneck * width + width  # fc2
    if use_head_ln:
        total += 2 * width
    if cosine_head:
        total += num_classes * width  # weight
        total += 1  # scale
    else:
        total += num_classes * width + num_classes
    return total


def _choose_architecture(input_dim: int, num_classes: int, param_limit: int) -> Tuple[int, int, int]:
    candidates = []
    for num_blocks in (2, 3, 4):
        for ratio in (0.5,):
            lo, hi = 64, 2048
            best = None
            while lo <= hi:
                mid = (lo + hi) // 2
                mid = max(64, (mid // 8) * 8)
                bottleneck = max(32, int(round(mid * ratio)))
                est = _estimate_params(
                    input_dim=input_dim,
                    num_classes=num_classes,
                    width=mid,
                    num_blocks=num_blocks,
                    bottleneck=bottleneck,
                    use_input_ln=True,
                    use_head_ln=True,
                    cosine_head=True,
                )
                if est <= param_limit:
                    best = (mid, num_blocks, bottleneck, est)
                    lo = mid + 8
                else:
                    hi = mid - 8
            if best is not None:
                width, nb, bottleneck, est = best
                score = width * math.sqrt(nb)  # heuristic
                candidates.append((score, est, width, nb, bottleneck))

    if not candidates:
        width = 256
        bottleneck = 128
        num_blocks = 2
        return width, num_blocks, bottleneck

    candidates.sort(key=lambda t: (t[0], t[1]), reverse=True)
    _, _, width, num_blocks, bottleneck = candidates[0]
    return width, num_blocks, bottleneck


def _accuracy_from_logits(logits: torch.Tensor, y: torch.Tensor) -> float:
    preds = logits.argmax(dim=1)
    return (preds == y).float().mean().item()


class Solution:
    def solve(self, train_loader, val_loader, metadata: dict = None) -> torch.nn.Module:
        if metadata is None:
            metadata = {}
        device = metadata.get("device", "cpu")
        if device != "cpu":
            device = "cpu"

        input_dim = int(metadata.get("input_dim", 384))
        num_classes = int(metadata.get("num_classes", 128))
        param_limit = int(metadata.get("param_limit", 2_500_000))

        try:
            torch.set_num_threads(min(8, os.cpu_count() or 8))
        except Exception:
            pass
        torch.manual_seed(0)

        x_train, y_train = _gather_from_loader(train_loader)
        x_val, y_val = _gather_from_loader(val_loader)

        mean = x_train.mean(dim=0)
        var = (x_train - mean).pow(2).mean(dim=0)
        std = var.sqrt().clamp_min(1e-4)

        width, num_blocks, bottleneck = _choose_architecture(input_dim, num_classes, param_limit)
        dropout = 0.10

        model = ResMLPClassifier(
            input_dim=input_dim,
            num_classes=num_classes,
            width=width,
            num_blocks=num_blocks,
            bottleneck=bottleneck,
            dropout=dropout,
            mean=mean,
            std=std,
        ).to(device)

        # Hard safety: shrink width if any mismatch with estimate
        while _count_trainable_params(model) > param_limit and width >= 128:
            width = max(128, width - 8)
            bottleneck = max(32, bottleneck - 4)
            model = ResMLPClassifier(
                input_dim=input_dim,
                num_classes=num_classes,
                width=width,
                num_blocks=num_blocks,
                bottleneck=bottleneck,
                dropout=dropout,
                mean=mean,
                std=std,
            ).to(device)

        param_count = _count_trainable_params(model)
        if param_count > param_limit:
            # Fallback: very small model (should never happen)
            width, num_blocks, bottleneck = 256, 2, 128
            model = ResMLPClassifier(
                input_dim=input_dim,
                num_classes=num_classes,
                width=width,
                num_blocks=num_blocks,
                bottleneck=bottleneck,
                dropout=0.05,
                mean=mean,
                std=std,
            ).to(device)

        x_train = x_train.to(device)
        y_train = y_train.to(device)
        x_val = x_val.to(device)
        y_val = y_val.to(device)

        n = x_train.shape[0]
        batch_size = 256 if n >= 1024 else 128
        epochs = 140
        warmup_epochs = 6
        base_lr = 3.0e-3
        min_lr = 2.5e-4
        weight_decay = 7.5e-3

        optimizer = torch.optim.AdamW(model.parameters(), lr=base_lr, weight_decay=weight_decay, betas=(0.9, 0.95))
        best_state = None
        best_val_acc = -1.0
        patience = 25
        bad_epochs = 0

        mixup_prob = 0.35
        mixup_alpha = 0.20
        label_smoothing = 0.03
        max_grad_norm = 1.0

        def set_epoch_lr(ep: int):
            if ep < warmup_epochs:
                lr = base_lr * float(ep + 1) / float(max(1, warmup_epochs))
            else:
                t = float(ep - warmup_epochs) / float(max(1, epochs - warmup_epochs))
                lr = min_lr + 0.5 * (base_lr - min_lr) * (1.0 + math.cos(math.pi * t))
            for pg in optimizer.param_groups:
                pg["lr"] = lr

        for ep in range(epochs):
            set_epoch_lr(ep)
            model.train()

            perm = torch.randperm(n, device=device)
            for i in range(0, n, batch_size):
                idx = perm[i : i + batch_size]
                xb = x_train.index_select(0, idx)
                yb = y_train.index_select(0, idx)

                do_mixup = (mixup_prob > 0.0) and (torch.rand((), device=device).item() < mixup_prob) and (xb.size(0) > 1)
                if do_mixup:
                    lam = torch.distributions.Beta(mixup_alpha, mixup_alpha).sample(()).to(device=device)
                    j = torch.randperm(xb.size(0), device=device)
                    xb = lam * xb + (1.0 - lam) * xb.index_select(0, j)
                    ya = yb
                    yb2 = yb.index_select(0, j)

                    logits = model(xb)
                    loss = lam * F.cross_entropy(logits, ya, label_smoothing=label_smoothing) + (1.0 - lam) * F.cross_entropy(
                        logits, yb2, label_smoothing=label_smoothing
                    )
                else:
                    logits = model(xb)
                    loss = F.cross_entropy(logits, yb, label_smoothing=label_smoothing)

                optimizer.zero_grad(set_to_none=True)
                loss.backward()
                if max_grad_norm is not None and max_grad_norm > 0:
                    torch.nn.utils.clip_grad_norm_(model.parameters(), max_grad_norm)
                optimizer.step()

            model.eval()
            with torch.inference_mode():
                logits_val = []
                for i in range(0, x_val.size(0), 512):
                    logits_val.append(model(x_val[i : i + 512]))
                logits_val = torch.cat(logits_val, dim=0)
                val_acc = _accuracy_from_logits(logits_val, y_val)

            if val_acc > best_val_acc + 1e-5:
                best_val_acc = val_acc
                best_state = {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}
                bad_epochs = 0
            else:
                bad_epochs += 1
                if bad_epochs >= patience:
                    break

        if best_state is not None:
            model.load_state_dict(best_state, strict=True)

        # Prototype refinement for cosine head in embedding space
        model.eval()
        with torch.inference_mode():
            feats = []
            for i in range(0, x_train.size(0), 512):
                feats.append(model.encode(x_train[i : i + 512]))
            feats = torch.cat(feats, dim=0)
            feats = F.normalize(feats, dim=1)

            prototypes = torch.zeros((num_classes, feats.size(1)), device=device, dtype=feats.dtype)
            counts = torch.zeros((num_classes,), device=device, dtype=torch.float32)
            prototypes.index_add_(0, y_train, feats)
            counts.index_add_(0, y_train, torch.ones_like(y_train, dtype=torch.float32))
            counts = counts.clamp_min(1.0).unsqueeze(1)
            prototypes = prototypes / counts
            prototypes = F.normalize(prototypes, dim=1)

            model.head.weight.data.copy_(prototypes)

        model.eval()
        return model.to(device)