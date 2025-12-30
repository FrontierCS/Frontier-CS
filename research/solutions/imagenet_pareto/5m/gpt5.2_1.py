import os
import math
import copy
import time
from typing import Optional, Tuple, List, Dict

import torch
import torch.nn as nn
import torch.nn.functional as F


def _set_torch_threads():
    try:
        n = os.cpu_count() or 8
        torch.set_num_threads(min(8, n))
        torch.set_num_interop_threads(min(2, n))
    except Exception:
        pass


def _count_trainable_params(model: nn.Module) -> int:
    return sum(p.numel() for p in model.parameters() if p.requires_grad)


@torch.no_grad()
def _collect_xy(loader) -> Tuple[torch.Tensor, torch.Tensor]:
    xs = []
    ys = []
    for xb, yb in loader:
        if isinstance(xb, (list, tuple)):
            xb = xb[0]
        xs.append(xb.detach().cpu())
        ys.append(yb.detach().cpu())
    x = torch.cat(xs, dim=0)
    y = torch.cat(ys, dim=0).long()
    return x, y


@torch.no_grad()
def _accuracy(model: nn.Module, loader, device: str = "cpu") -> float:
    model.eval()
    correct = 0
    total = 0
    for xb, yb in loader:
        xb = xb.to(device)
        yb = yb.to(device)
        logits = model(xb)
        pred = logits.argmax(dim=1)
        correct += (pred == yb).sum().item()
        total += yb.numel()
    return (correct / total) if total > 0 else 0.0


class _Normalize(nn.Module):
    def __init__(self, mean: torch.Tensor, inv_std: torch.Tensor):
        super().__init__()
        self.register_buffer("mean", mean.clone().detach())
        self.register_buffer("inv_std", inv_std.clone().detach())

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return (x - self.mean) * self.inv_std


class _LDAClassifier(nn.Module):
    def __init__(self, mean: torch.Tensor, inv_std: torch.Tensor, W: torch.Tensor, b: torch.Tensor):
        super().__init__()
        self.norm = _Normalize(mean, inv_std)
        self.register_buffer("W", W.clone().detach())
        self.register_buffer("b", b.clone().detach())

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self.norm(x)
        return x.matmul(self.W) + self.b


class _BottleneckResidualBlock(nn.Module):
    def __init__(self, width: int, bottleneck: int, dropout: float):
        super().__init__()
        self.ln = nn.LayerNorm(width)
        self.fc1 = nn.Linear(width, bottleneck)
        self.fc2 = nn.Linear(bottleneck, width)
        self.dropout = nn.Dropout(dropout)
        self.act = nn.GELU()

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        h = self.ln(x)
        h = self.fc1(h)
        h = self.act(h)
        h = self.dropout(h)
        h = self.fc2(h)
        h = self.dropout(h)
        return x + h


class _ResidualBottleneckMLP(nn.Module):
    def __init__(
        self,
        input_dim: int,
        num_classes: int,
        mean: torch.Tensor,
        inv_std: torch.Tensor,
        width: int = 1728,
        bottleneck: int = 384,
        blocks: int = 3,
        dropout: float = 0.10,
    ):
        super().__init__()
        self.norm = _Normalize(mean, inv_std)
        self.in_ln = nn.LayerNorm(input_dim)
        self.stem = nn.Linear(input_dim, width)
        self.stem_act = nn.GELU()
        self.stem_ln = nn.LayerNorm(width)
        self.blocks = nn.ModuleList([_BottleneckResidualBlock(width, bottleneck, dropout) for _ in range(blocks)])
        self.final_ln = nn.LayerNorm(width)
        self.head = nn.Linear(width, num_classes)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self.norm(x)
        x = self.in_ln(x)
        x = self.stem(x)
        x = self.stem_act(x)
        x = self.stem_ln(x)
        for blk in self.blocks:
            x = blk(x)
        x = self.final_ln(x)
        return self.head(x)


def _compute_standardization(x: torch.Tensor, eps: float = 1e-6) -> Tuple[torch.Tensor, torch.Tensor]:
    mean = x.mean(dim=0)
    var = x.var(dim=0, unbiased=False)
    inv_std = torch.rsqrt(var + eps)
    return mean, inv_std


def _build_lda_from_data(
    x_train: torch.Tensor,
    y_train: torch.Tensor,
    input_dim: int,
    num_classes: int,
    alphas: List[float],
    x_val: Optional[torch.Tensor] = None,
    y_val: Optional[torch.Tensor] = None,
) -> Tuple[nn.Module, float]:
    mean, inv_std = _compute_standardization(x_train)
    xtr = (x_train - mean) * inv_std
    xtr64 = xtr.double()

    means = torch.zeros((num_classes, input_dim), dtype=torch.float64)
    counts = torch.zeros((num_classes,), dtype=torch.float64)
    for c in range(num_classes):
        mask = (y_train == c)
        if mask.any():
            xc = xtr64[mask]
            means[c] = xc.mean(dim=0)
            counts[c] = mask.sum().item()
        else:
            means[c] = 0.0
            counts[c] = 1.0

    n = xtr64.shape[0]
    xm = xtr64.mean(dim=0, keepdim=True)
    xc = xtr64 - xm
    cov = (xc.t().matmul(xc)) / max(1, (n - 1))
    cov = (cov + cov.t()) * 0.5

    evals, evecs = torch.linalg.eigh(cov)
    evals = torch.clamp(evals, min=1e-12)
    m = evals.mean()

    if x_val is not None and y_val is not None:
        xva = ((x_val - mean) * inv_std).double()
        yva = y_val.long()
    else:
        xva = None
        yva = None

    best_acc = -1.0
    best_W = None
    best_b = None
    best_alpha = None

    Qt_meansT = evecs.t().matmul(means.t())  # (d, C)
    for alpha in alphas:
        lam = (1.0 - alpha) * evals + alpha * m
        inv_lam = 1.0 / torch.clamp(lam, min=1e-12)
        tmp = inv_lam.unsqueeze(1) * Qt_meansT
        W64 = evecs.matmul(tmp)  # (d, C)
        quad = torch.sum(means.t() * W64, dim=0)  # (C,)
        b64 = (-0.5 * quad)

        if xva is None:
            acc = 0.0
        else:
            logits = xva.matmul(W64) + b64
            pred = logits.argmax(dim=1)
            acc = (pred == yva).double().mean().item()

        if acc > best_acc:
            best_acc = acc
            best_W = W64
            best_b = b64
            best_alpha = alpha

    if best_W is None:
        alpha = 0.1
        lam = (1.0 - alpha) * evals + alpha * m
        inv_lam = 1.0 / torch.clamp(lam, min=1e-12)
        tmp = inv_lam.unsqueeze(1) * Qt_meansT
        best_W = evecs.matmul(tmp)
        quad = torch.sum(means.t() * best_W, dim=0)
        best_b = (-0.5 * quad)
        best_acc = -1.0
        best_alpha = alpha

    model = _LDAClassifier(mean.float(), inv_std.float(), best_W.float(), best_b.float())
    return model, float(best_acc)


def _train_mlp(
    model: nn.Module,
    train_loader,
    val_loader,
    device: str,
    max_epochs: int = 40,
    patience: int = 8,
    lr: float = 2e-3,
    weight_decay: float = 2e-2,
    label_smoothing: float = 0.08,
    mixup_alpha: float = 0.2,
    grad_clip: float = 1.0,
) -> Tuple[nn.Module, float]:
    model.to(device)
    opt = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=weight_decay)
    total_steps = max(1, max_epochs * max(1, len(train_loader)))
    sched = torch.optim.lr_scheduler.OneCycleLR(
        opt,
        max_lr=lr,
        total_steps=total_steps,
        pct_start=0.2,
        div_factor=10.0,
        final_div_factor=50.0,
        anneal_strategy="cos",
    )

    beta_dist = torch.distributions.Beta(mixup_alpha, mixup_alpha) if mixup_alpha and mixup_alpha > 0 else None

    best_state = None
    best_val = -1.0
    bad = 0

    step = 0
    for epoch in range(max_epochs):
        model.train()
        for xb, yb in train_loader:
            xb = xb.to(device)
            yb = yb.to(device)

            if beta_dist is not None and xb.size(0) >= 2:
                lam = float(beta_dist.sample().clamp(0.0, 1.0).item())
                perm = torch.randperm(xb.size(0), device=device)
                xb2 = xb[perm]
                yb2 = yb[perm]
                xmix = lam * xb + (1.0 - lam) * xb2
                logits = model(xmix)
                loss1 = F.cross_entropy(logits, yb, label_smoothing=label_smoothing)
                loss2 = F.cross_entropy(logits, yb2, label_smoothing=label_smoothing)
                loss = lam * loss1 + (1.0 - lam) * loss2
            else:
                logits = model(xb)
                loss = F.cross_entropy(logits, yb, label_smoothing=label_smoothing)

            opt.zero_grad(set_to_none=True)
            loss.backward()
            if grad_clip is not None and grad_clip > 0:
                torch.nn.utils.clip_grad_norm_(model.parameters(), grad_clip)
            opt.step()
            sched.step()
            step += 1

        val_acc = _accuracy(model, val_loader, device=device)
        if val_acc > best_val + 1e-6:
            best_val = val_acc
            best_state = copy.deepcopy(model.state_dict())
            bad = 0
        else:
            bad += 1
            if bad >= patience:
                break

    if best_state is not None:
        model.load_state_dict(best_state)
    model.eval()
    return model, float(best_val)


class Solution:
    def solve(self, train_loader, val_loader, metadata: dict = None) -> torch.nn.Module:
        _set_torch_threads()
        if metadata is None:
            metadata = {}
        device = str(metadata.get("device", "cpu"))
        input_dim = int(metadata.get("input_dim", 384))
        num_classes = int(metadata.get("num_classes", 128))
        param_limit = int(metadata.get("param_limit", 5_000_000))

        torch.manual_seed(0)

        x_train, y_train = _collect_xy(train_loader)
        x_val, y_val = _collect_xy(val_loader)

        alphas = [0.0, 0.02, 0.05, 0.1, 0.2, 0.4]
        lda_model, lda_val_acc = _build_lda_from_data(
            x_train=x_train,
            y_train=y_train,
            input_dim=input_dim,
            num_classes=num_classes,
            alphas=alphas,
            x_val=x_val,
            y_val=y_val,
        )
        lda_model.to(device)

        mean, inv_std = _compute_standardization(x_train)

        width, bottleneck, blocks, dropout = 1728, 384, 3, 0.10
        mlp_model = _ResidualBottleneckMLP(
            input_dim=input_dim,
            num_classes=num_classes,
            mean=mean.float(),
            inv_std=inv_std.float(),
            width=width,
            bottleneck=bottleneck,
            blocks=blocks,
            dropout=dropout,
        )
        while _count_trainable_params(mlp_model) > param_limit and width > 256:
            width = max(256, width - 64)
            bottleneck = min(bottleneck, max(64, width // 4))
            blocks = min(blocks, 4)
            mlp_model = _ResidualBottleneckMLP(
                input_dim=input_dim,
                num_classes=num_classes,
                mean=mean.float(),
                inv_std=inv_std.float(),
                width=width,
                bottleneck=bottleneck,
                blocks=blocks,
                dropout=dropout,
            )

        mlp_params = _count_trainable_params(mlp_model)
        if mlp_params > param_limit:
            return lda_model

        max_epochs = 20 if lda_val_acc >= 0.97 else 45
        patience = 6 if lda_val_acc >= 0.97 else 10

        mlp_model, mlp_val_acc = _train_mlp(
            model=mlp_model,
            train_loader=train_loader,
            val_loader=val_loader,
            device=device,
            max_epochs=max_epochs,
            patience=patience,
            lr=2.2e-3,
            weight_decay=2e-2,
            label_smoothing=0.08,
            mixup_alpha=0.2 if lda_val_acc < 0.985 else 0.1,
            grad_clip=1.0,
        )

        if mlp_val_acc >= lda_val_acc:
            mlp_model.to(device)
            return mlp_model
        else:
            lda_model.to(device)
            return lda_model