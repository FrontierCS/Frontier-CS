import math
import copy
from typing import Tuple, Optional, Dict

import torch
import torch.nn as nn
import torch.nn.functional as F


def _count_trainable_params(model: nn.Module) -> int:
    return sum(p.numel() for p in model.parameters() if p.requires_grad)


def _loader_to_tensors(loader) -> Tuple[torch.Tensor, torch.Tensor]:
    xs = []
    ys = []
    for batch in loader:
        if isinstance(batch, (list, tuple)) and len(batch) >= 2:
            x, y = batch[0], batch[1]
        else:
            raise ValueError("DataLoader batch must be a tuple/list (inputs, targets).")
        xs.append(x.detach().cpu())
        ys.append(y.detach().cpu())
    x = torch.cat(xs, dim=0)
    y = torch.cat(ys, dim=0).long()
    if x.dtype != torch.float32:
        x = x.float()
    return x, y


def _make_soft_targets(y: torch.Tensor, num_classes: int, smoothing: float) -> torch.Tensor:
    bs = y.shape[0]
    off = smoothing / float(num_classes)
    on = 1.0 - smoothing + off
    t = torch.full((bs, num_classes), off, dtype=torch.float32, device=y.device)
    t.scatter_(1, y.view(-1, 1), on)
    return t


def _soft_cross_entropy(logits: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
    logp = F.log_softmax(logits, dim=1)
    return -(targets * logp).sum(dim=1).mean()


class _ResidualFFN(nn.Module):
    def __init__(self, d: int, h: int, dropout: float):
        super().__init__()
        self.ln = nn.LayerNorm(d)
        self.fc1 = nn.Linear(d, h)
        self.fc2 = nn.Linear(h, d)
        self.drop = nn.Dropout(dropout)
        self.alpha = nn.Parameter(torch.zeros(1))

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        y = self.ln(x)
        y = self.fc1(y)
        y = F.gelu(y)
        y = self.drop(y)
        y = self.fc2(y)
        y = self.drop(y)
        return x + self.alpha * y


class _ResMLPClassifier(nn.Module):
    def __init__(
        self,
        input_dim: int,
        num_classes: int,
        d: int,
        h: int,
        n_blocks: int,
        dropout: float,
        mean: torch.Tensor,
        std: torch.Tensor,
        input_noise: float = 0.0,
    ):
        super().__init__()
        self.input_dim = input_dim
        self.num_classes = num_classes
        self.d = d
        self.h = h
        self.n_blocks = n_blocks
        self.dropout_p = dropout
        self.input_noise = float(input_noise)

        self.register_buffer("x_mean", mean.view(1, -1).clone())
        self.register_buffer("x_std", std.view(1, -1).clone())

        self.in_ln = nn.LayerNorm(input_dim)
        self.in_proj = nn.Linear(input_dim, d)
        self.in_drop = nn.Dropout(dropout)

        self.blocks = nn.ModuleList([_ResidualFFN(d, h, dropout) for _ in range(n_blocks)])
        self.out_ln = nn.LayerNorm(d)
        self.head = nn.Linear(d, num_classes)

    def _normalize(self, x: torch.Tensor) -> torch.Tensor:
        return (x - self.x_mean) / self.x_std

    def forward_features(self, x: torch.Tensor) -> torch.Tensor:
        x = self._normalize(x)
        if self.training and self.input_noise > 0:
            x = x + self.input_noise * torch.randn_like(x)
        x = self.in_ln(x)
        x = self.in_proj(x)
        x = F.gelu(x)
        x = self.in_drop(x)
        for blk in self.blocks:
            x = blk(x)
        x = self.out_ln(x)
        return x

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        feats = self.forward_features(x)
        return self.head(feats)


def _param_estimate(
    input_dim: int,
    num_classes: int,
    d: int,
    h: int,
    n_blocks: int,
    include_input_ln: bool = True,
    include_in_drop: bool = False,
    include_out_ln: bool = True,
    include_block_alpha: bool = True,
) -> int:
    total = 0
    if include_input_ln:
        total += 2 * input_dim
    total += (input_dim * d + d)  # in_proj
    if include_in_drop:
        total += 0
    for _ in range(n_blocks):
        total += 2 * d  # block ln
        total += d * h + h  # fc1
        total += h * d + d  # fc2
        if include_block_alpha:
            total += 1
    if include_out_ln:
        total += 2 * d
    total += d * num_classes + num_classes  # head
    return total


def _choose_arch(input_dim: int, num_classes: int, param_limit: int) -> Tuple[int, int, int, float]:
    best = None  # (score, params, d, h, n, dropout)
    dropouts = [0.10, 0.08, 0.12]
    ratios = [4, 5, 3]
    for dropout in dropouts:
        for n_blocks in (4, 3, 2, 1):
            for d in range(1024, 255, -32):
                for r in ratios:
                    h = max(64, d // r)
                    if h >= d:
                        continue
                    p = _param_estimate(input_dim, num_classes, d, h, n_blocks)
                    if p > param_limit:
                        continue
                    # Prefer using most params, then more blocks, then larger d
                    score = (p, n_blocks, d, h)
                    if best is None or score > best[0]:
                        best = (score, p, d, h, n_blocks, dropout)
    if best is None:
        d = 256
        h = 64
        n_blocks = 1
        dropout = 0.10
        return d, h, n_blocks, dropout
    _, _, d, h, n_blocks, dropout = best
    return d, h, n_blocks, dropout


def _accuracy(model: nn.Module, x: torch.Tensor, y: torch.Tensor, batch_size: int = 512) -> float:
    model.eval()
    correct = 0
    total = y.numel()
    with torch.inference_mode():
        for i in range(0, x.shape[0], batch_size):
            xb = x[i : i + batch_size]
            yb = y[i : i + batch_size]
            logits = model(xb)
            pred = logits.argmax(dim=1)
            correct += (pred == yb).sum().item()
    return float(correct) / float(total) if total > 0 else 0.0


def _ridge_refit_head(
    model: _ResMLPClassifier,
    train_x: torch.Tensor,
    train_y: torch.Tensor,
    val_x: Optional[torch.Tensor],
    val_y: Optional[torch.Tensor],
    lam: float = 1e-2,
) -> None:
    model.eval()
    d = model.d
    c = model.num_classes

    with torch.inference_mode():
        feats = model.forward_features(train_x).float()
    feats = feats.contiguous()

    ones = torch.ones((feats.shape[0], 1), dtype=feats.dtype, device=feats.device)
    Faug = torch.cat([feats, ones], dim=1).double()  # (N, d+1)

    Y = torch.zeros((train_y.shape[0], c), dtype=torch.float64, device=Faug.device)
    Y.scatter_(1, train_y.view(-1, 1).to(torch.int64), 1.0)

    FtF = Faug.T @ Faug
    FtY = Faug.T @ Y
    FtF = FtF + lam * torch.eye(d + 1, dtype=torch.float64, device=Faug.device)

    try:
        Waug = torch.linalg.solve(FtF, FtY)  # (d+1, c)
    except RuntimeError:
        return

    old_w = model.head.weight.detach().clone()
    old_b = model.head.bias.detach().clone()

    new_w = Waug[:d, :].T.contiguous().float()
    new_b = Waug[d, :].contiguous().float()

    with torch.no_grad():
        model.head.weight.copy_(new_w)
        model.head.bias.copy_(new_b)

    if val_x is not None and val_y is not None:
        before = None
        after = _accuracy(model, val_x, val_y, batch_size=512)
        # If val got worse, revert
        with torch.no_grad():
            model.head.weight.copy_(old_w)
            model.head.bias.copy_(old_b)
        before = _accuracy(model, val_x, val_y, batch_size=512)
        if after >= before:
            with torch.no_grad():
                model.head.weight.copy_(new_w)
                model.head.bias.copy_(new_b)


class Solution:
    def solve(self, train_loader, val_loader, metadata: dict = None) -> torch.nn.Module:
        if metadata is None:
            metadata = {}
        input_dim = int(metadata.get("input_dim", 384))
        num_classes = int(metadata.get("num_classes", 128))
        param_limit = int(metadata.get("param_limit", 1_000_000))
        device = metadata.get("device", "cpu")
        if device is None:
            device = "cpu"
        device = str(device)

        train_x, train_y = _loader_to_tensors(train_loader)
        if val_loader is not None:
            val_x, val_y = _loader_to_tensors(val_loader)
        else:
            val_x, val_y = None, None

        mean = train_x.mean(dim=0)
        std = train_x.std(dim=0, unbiased=False).clamp_min(1e-6)

        d, h, n_blocks, dropout = _choose_arch(input_dim, num_classes, param_limit)

        model = _ResMLPClassifier(
            input_dim=input_dim,
            num_classes=num_classes,
            d=d,
            h=h,
            n_blocks=n_blocks,
            dropout=dropout,
            mean=mean,
            std=std,
            input_noise=0.02,
        ).to("cpu")

        # Hard safety: ensure under param limit, otherwise shrink d until it is.
        while _count_trainable_params(model) > param_limit and d > 128:
            d -= 32
            h = max(64, d // 4)
            model = _ResMLPClassifier(
                input_dim=input_dim,
                num_classes=num_classes,
                d=d,
                h=h,
                n_blocks=n_blocks,
                dropout=dropout,
                mean=mean,
                std=std,
                input_noise=0.02,
            ).to("cpu")

        # Training hyperparams
        n = train_x.shape[0]
        batch_size = 256 if n >= 512 else 128
        max_epochs = 220
        min_epochs = 30
        patience = 35

        base_lr = 3e-3
        min_lr = 3e-5
        warmup_epochs = 6
        weight_decay = 1.5e-4
        smoothing = 0.06
        mixup_alpha = 0.20

        optimizer = torch.optim.AdamW(model.parameters(), lr=base_lr, weight_decay=weight_decay)

        best_state = copy.deepcopy(model.state_dict())
        best_val = -1.0
        best_epoch = -1
        no_improve = 0

        beta_dist = torch.distributions.Beta(mixup_alpha, mixup_alpha)

        train_x = train_x.to("cpu")
        train_y = train_y.to("cpu")
        if val_x is not None:
            val_x = val_x.to("cpu")
            val_y = val_y.to("cpu")

        for epoch in range(max_epochs):
            model.train()

            if epoch < warmup_epochs:
                lr = base_lr * float(epoch + 1) / float(warmup_epochs)
            else:
                prog = float(epoch - warmup_epochs) / float(max(1, max_epochs - warmup_epochs))
                lr = min_lr + 0.5 * (base_lr - min_lr) * (1.0 + math.cos(math.pi * prog))
            for pg in optimizer.param_groups:
                pg["lr"] = lr

            idx = torch.randperm(n)
            mixup_p = 0.55 if epoch < int(0.65 * max_epochs) else 0.15
            for start in range(0, n, batch_size):
                bidx = idx[start : start + batch_size]
                xb = train_x[bidx]
                yb = train_y[bidx]

                do_mixup = (mixup_alpha > 0) and (torch.rand(()) < mixup_p) and (yb.numel() > 1)
                if do_mixup:
                    perm = torch.randperm(xb.shape[0])
                    lam = float(beta_dist.sample().item())
                    xb2 = xb[perm]
                    yb2 = yb[perm]
                    xb = xb.mul(lam).add_(xb2, alpha=(1.0 - lam))
                    t1 = _make_soft_targets(yb, num_classes, smoothing)
                    t2 = _make_soft_targets(yb2, num_classes, smoothing)
                    targets = t1.mul(lam).add_(t2, alpha=(1.0 - lam))
                else:
                    targets = _make_soft_targets(yb, num_classes, smoothing)

                logits = model(xb)
                loss = _soft_cross_entropy(logits, targets)

                optimizer.zero_grad(set_to_none=True)
                loss.backward()
                torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
                optimizer.step()

            # Validation / tracking
            if val_x is not None:
                val_acc = _accuracy(model, val_x, val_y, batch_size=512)
            else:
                val_acc = _accuracy(model, train_x, train_y, batch_size=512)

            if val_acc > best_val + 1e-4:
                best_val = val_acc
                best_epoch = epoch
                best_state = copy.deepcopy(model.state_dict())
                no_improve = 0
            else:
                no_improve += 1

            if epoch + 1 >= min_epochs and no_improve >= patience:
                break

        model.load_state_dict(best_state)

        # Ridge refit head for potentially better generalization
        _ridge_refit_head(model, train_x, train_y, val_x, val_y, lam=1e-2)

        model.to(device)
        return model
