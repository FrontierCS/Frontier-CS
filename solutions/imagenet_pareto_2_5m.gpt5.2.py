import os
import math
import copy
import time
from typing import Dict, Tuple, Optional, List

import torch
import torch.nn as nn
import torch.nn.functional as F


def _count_trainable_params(model: nn.Module) -> int:
    return sum(p.numel() for p in model.parameters() if p.requires_grad)


def _loader_to_tensors(loader, device: torch.device) -> Tuple[torch.Tensor, torch.Tensor]:
    xs = []
    ys = []
    for batch in loader:
        if isinstance(batch, (list, tuple)) and len(batch) >= 2:
            x, y = batch[0], batch[1]
        else:
            raise ValueError("Expected loader to yield (inputs, targets).")
        if not torch.is_tensor(x):
            x = torch.as_tensor(x)
        if not torch.is_tensor(y):
            y = torch.as_tensor(y)
        x = x.to(device=device, dtype=torch.float32, non_blocking=True)
        y = y.to(device=device, dtype=torch.long, non_blocking=True)
        if x.ndim > 2:
            x = x.view(x.shape[0], -1)
        xs.append(x)
        ys.append(y)
    if not xs:
        raise ValueError("Empty dataloader.")
    X = torch.cat(xs, dim=0)
    Y = torch.cat(ys, dim=0)
    return X, Y


class Standardize(nn.Module):
    def __init__(self, mean: torch.Tensor, std: torch.Tensor, eps: float = 1e-6):
        super().__init__()
        mean = mean.detach().clone().to(dtype=torch.float32)
        std = std.detach().clone().to(dtype=torch.float32)
        invstd = 1.0 / (std.clamp_min(eps))
        self.register_buffer("mean", mean)
        self.register_buffer("invstd", invstd)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        if x.ndim > 2:
            x = x.view(x.shape[0], -1)
        return (x.to(dtype=torch.float32) - self.mean) * self.invstd


class LDAClassifier(nn.Module):
    def __init__(self, standardize: Standardize, weight: torch.Tensor, bias: torch.Tensor):
        super().__init__()
        self.standardize = standardize
        self.register_buffer("weight", weight.detach().clone().to(dtype=torch.float32))
        self.register_buffer("bias", bias.detach().clone().to(dtype=torch.float32))

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self.standardize(x)
        return F.linear(x, self.weight, self.bias)


class ResidualBlock(nn.Module):
    def __init__(self, dim: int, dropout: float):
        super().__init__()
        self.ln = nn.LayerNorm(dim)
        self.fc1 = nn.Linear(dim, dim)
        self.fc2 = nn.Linear(dim, dim)
        self.dropout = float(dropout)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        h = self.ln(x)
        h = F.gelu(self.fc1(h))
        if self.dropout > 0:
            h = F.dropout(h, p=self.dropout, training=self.training)
        h = self.fc2(h)
        if self.dropout > 0:
            h = F.dropout(h, p=self.dropout, training=self.training)
        return x + h


class MLPClassifier(nn.Module):
    def __init__(self, standardize: Standardize, input_dim: int, num_classes: int, h1: int, h2: int, n_blocks: int, dropout: float):
        super().__init__()
        self.standardize = standardize
        self.fc_in = nn.Linear(input_dim, h1)
        self.fc_mid = nn.Linear(h1, h2)
        self.blocks = nn.ModuleList([ResidualBlock(h2, dropout=dropout) for _ in range(n_blocks)])
        self.ln_out = nn.LayerNorm(h2)
        self.head = nn.Linear(h2, num_classes)
        self.dropout = float(dropout)

        self._init_weights()

    def _init_weights(self):
        for m in self.modules():
            if isinstance(m, nn.Linear):
                nn.init.kaiming_normal_(m.weight, nonlinearity="relu")
                if m.bias is not None:
                    nn.init.zeros_(m.bias)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self.standardize(x)
        x = F.gelu(self.fc_in(x))
        if self.dropout > 0:
            x = F.dropout(x, p=self.dropout, training=self.training)
        x = F.gelu(self.fc_mid(x))
        if self.dropout > 0:
            x = F.dropout(x, p=self.dropout, training=self.training)
        for b in self.blocks:
            x = b(x)
        x = self.ln_out(x)
        return self.head(x)


class EnsembleAvg(nn.Module):
    def __init__(self, a: nn.Module, b: nn.Module, wa: float = 0.5, wb: float = 0.5):
        super().__init__()
        self.a = a
        self.b = b
        self.wa = float(wa)
        self.wb = float(wb)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.wa * self.a(x) + self.wb * self.b(x)


@torch.inference_mode()
def _accuracy(model: nn.Module, X: torch.Tensor, y: torch.Tensor, batch_size: int = 2048) -> float:
    model.eval()
    n = X.shape[0]
    correct = 0
    for i in range(0, n, batch_size):
        xb = X[i:i + batch_size]
        yb = y[i:i + batch_size]
        logits = model(xb)
        pred = logits.argmax(dim=1)
        correct += (pred == yb).sum().item()
    return correct / max(1, n)


def _fit_lda_weights(X: torch.Tensor, y: torch.Tensor, num_classes: int, shrink: float, reg_scale: float = 1e-4) -> Tuple[torch.Tensor, torch.Tensor]:
    device = X.device
    N, D = X.shape

    counts = torch.zeros(num_classes, device=device, dtype=torch.float64)
    sums = torch.zeros(num_classes, D, device=device, dtype=torch.float64)
    X64 = X.to(dtype=torch.float64)
    y64 = y.to(dtype=torch.long)

    counts.index_add_(0, y64, torch.ones_like(y64, dtype=torch.float64))
    sums.index_add_(0, y64, X64)

    counts_clamped = counts.clamp_min(1.0)
    mu = sums / counts_clamped.unsqueeze(1)  # (K, D)

    mu_y = mu[y64]  # (N, D)
    centered = X64 - mu_y
    denom = float(max(1, N - num_classes))
    S = (centered.t().matmul(centered)) / denom  # (D, D), within-class cov estimate

    S = 0.5 * (S + S.t())

    evals, evecs = torch.linalg.eigh(S)  # evals ascending
    evals = evals.clamp_min(0.0)

    alpha = (evals.mean()).item()
    reg = reg_scale * (alpha if alpha > 0 else 1.0)

    lam = float(shrink)
    inv_diag = 1.0 / (((1.0 - lam) * evals) + (lam * alpha) + reg)  # (D,)

    M = mu.t()  # (D, K)
    tmp = evecs.t().matmul(M)  # (D, K)
    tmp = tmp * inv_diag.unsqueeze(1)
    WdK = evecs.matmul(tmp)  # (D, K) = inv_cov @ mu^T

    W = WdK.t().contiguous()  # (K, D)
    b = -0.5 * (mu * W).sum(dim=1)  # (K,)

    return W.to(dtype=torch.float32), b.to(dtype=torch.float32)


def _choose_mlp_config(input_dim: int, num_classes: int, param_limit: int) -> Tuple[int, int, int]:
    best = None

    h1_candidates = []
    for h in [640, 768, 896, 1024, 1152, 1280, 1408]:
        if h >= 256:
            h1_candidates.append(h)

    h2_candidates = []
    for h in [320, 384, 448, 512, 576, 640, 704, 768]:
        if h >= 256:
            h2_candidates.append(h)

    block_candidates = [1, 2, 3, 4]

    def estimate_params(d: int, k: int, h1: int, h2: int, nb: int) -> int:
        P = 0
        P += d * h1 + h1
        P += h1 * h2 + h2
        # blocks: LayerNorm (2*h2) + fc1 (h2*h2+h2) + fc2 (h2*h2+h2)
        P += nb * (2 * h2 + (h2 * h2 + h2) + (h2 * h2 + h2))
        P += 2 * h2  # ln_out
        P += h2 * k + k
        return int(P)

    target = int(param_limit * 0.995)

    for h1 in h1_candidates:
        for h2 in h2_candidates:
            if h2 > h1:
                continue
            for nb in block_candidates:
                est = estimate_params(input_dim, num_classes, h1, h2, nb)
                if est <= target:
                    if best is None:
                        best = (est, h1, h2, nb)
                    else:
                        if est > best[0]:
                            best = (est, h1, h2, nb)

    if best is None:
        return 512, 256, 1
    return best[1], best[2], best[3]


def _train_mlp(
    model: nn.Module,
    X_train: torch.Tensor,
    y_train: torch.Tensor,
    X_val: torch.Tensor,
    y_val: torch.Tensor,
    epochs: int = 250,
    batch_size: int = 256,
    base_lr: float = 3e-3,
    min_lr_ratio: float = 0.05,
    weight_decay: float = 0.02,
    label_smoothing: float = 0.05,
    patience: int = 40,
    grad_clip: float = 1.0,
) -> Tuple[nn.Module, float]:
    device = X_train.device
    N = X_train.shape[0]
    bs = int(min(max(16, batch_size), N))

    opt = torch.optim.AdamW(model.parameters(), lr=base_lr, weight_decay=weight_decay, betas=(0.9, 0.99), eps=1e-8)
    steps_per_epoch = int(math.ceil(N / bs))
    total_steps = max(1, steps_per_epoch * epochs)
    warmup_steps = max(1, int(0.08 * total_steps))
    min_lr = base_lr * float(min_lr_ratio)

    best_state = None
    best_acc = -1.0
    best_epoch = -1

    model.train()
    step = 0

    for epoch in range(epochs):
        perm = torch.randperm(N, device=device)
        model.train()

        for si in range(0, N, bs):
            idx = perm[si:si + bs]
            xb = X_train[idx]
            yb = y_train[idx]

            if step < warmup_steps:
                lr = base_lr * float(step + 1) / float(warmup_steps)
            else:
                t = float(step - warmup_steps) / float(max(1, total_steps - warmup_steps))
                lr = min_lr + 0.5 * (base_lr - min_lr) * (1.0 + math.cos(math.pi * t))
            for pg in opt.param_groups:
                pg["lr"] = lr

            opt.zero_grad(set_to_none=True)
            logits = model(xb)
            loss = F.cross_entropy(logits, yb, label_smoothing=label_smoothing)
            loss.backward()
            if grad_clip is not None and grad_clip > 0:
                nn.utils.clip_grad_norm_(model.parameters(), max_norm=grad_clip)
            opt.step()
            step += 1

        val_acc = _accuracy(model, X_val, y_val, batch_size=2048)
        if val_acc > best_acc + 1e-6:
            best_acc = val_acc
            best_epoch = epoch
            best_state = copy.deepcopy(model.state_dict())

        if (epoch - best_epoch) >= patience:
            break

    if best_state is not None:
        model.load_state_dict(best_state)
    model.eval()
    return model, float(best_acc)


class Solution:
    def solve(self, train_loader, val_loader, metadata: dict = None) -> torch.nn.Module:
        if metadata is None:
            metadata = {}
        input_dim = int(metadata.get("input_dim", 384))
        num_classes = int(metadata.get("num_classes", 128))
        param_limit = int(metadata.get("param_limit", 2_500_000))
        device_str = str(metadata.get("device", "cpu"))
        device = torch.device(device_str)

        try:
            n_threads = min(8, (os.cpu_count() or 8))
            torch.set_num_threads(n_threads)
        except Exception:
            pass

        torch.manual_seed(0)

        X_train_raw, y_train = _loader_to_tensors(train_loader, device=device)
        X_val_raw, y_val = _loader_to_tensors(val_loader, device=device)

        if X_train_raw.shape[1] != input_dim:
            X_train_raw = X_train_raw.view(X_train_raw.shape[0], -1)
        if X_val_raw.shape[1] != input_dim:
            X_val_raw = X_val_raw.view(X_val_raw.shape[0], -1)

        mean = X_train_raw.mean(dim=0)
        std = X_train_raw.std(dim=0, unbiased=False).clamp_min(1e-3)
        standardize = Standardize(mean=mean, std=std)

        X_train = standardize(X_train_raw)
        X_val = standardize(X_val_raw)

        best_lda_model = None
        best_lda_acc = -1.0
        for shrink in (0.0, 0.05, 0.1, 0.2, 0.35):
            W, b = _fit_lda_weights(X_train, y_train, num_classes=num_classes, shrink=shrink, reg_scale=1e-4)
            lda_model = LDAClassifier(standardize=standardize, weight=W, bias=b).to(device)
            acc = _accuracy(lda_model, X_val_raw, y_val, batch_size=2048)
            if acc > best_lda_acc:
                best_lda_acc = acc
                best_lda_model = lda_model

        h1, h2, n_blocks = _choose_mlp_config(input_dim=input_dim, num_classes=num_classes, param_limit=param_limit)
        dropout = 0.12 if n_blocks >= 3 else 0.10
        mlp_model = MLPClassifier(standardize=standardize, input_dim=input_dim, num_classes=num_classes, h1=h1, h2=h2, n_blocks=n_blocks, dropout=dropout).to(device)

        if _count_trainable_params(mlp_model) > param_limit:
            fallback = MLPClassifier(standardize=standardize, input_dim=input_dim, num_classes=num_classes, h1=1024, h2=512, n_blocks=2, dropout=0.10).to(device)
            if _count_trainable_params(fallback) <= param_limit:
                mlp_model = fallback
            else:
                mlp_model = MLPClassifier(standardize=standardize, input_dim=input_dim, num_classes=num_classes, h1=768, h2=384, n_blocks=2, dropout=0.10).to(device)

        base_lr = 3e-3
        wd = 0.02
        ls = 0.06
        epochs = 260
        batch_size = 256

        mlp_model, best_mlp_acc = _train_mlp(
            mlp_model,
            X_train=X_train_raw,
            y_train=y_train,
            X_val=X_val_raw,
            y_val=y_val,
            epochs=epochs,
            batch_size=batch_size,
            base_lr=base_lr,
            min_lr_ratio=0.05,
            weight_decay=wd,
            label_smoothing=ls,
            patience=45,
            grad_clip=1.0,
        )

        candidates: List[Tuple[float, nn.Module]] = []
        if best_lda_model is not None:
            candidates.append((best_lda_acc, best_lda_model))
        candidates.append((best_mlp_acc, mlp_model))

        if best_lda_model is not None:
            ensemble = EnsembleAvg(best_lda_model, mlp_model, wa=0.45, wb=0.55).to(device)
            ens_acc = _accuracy(ensemble, X_val_raw, y_val, batch_size=2048)
            candidates.append((ens_acc, ensemble))

        candidates.sort(key=lambda x: x[0], reverse=True)
        best_model = candidates[0][1].to(device)
        best_model.eval()

        if _count_trainable_params(best_model) > param_limit:
            if best_lda_model is not None:
                best_model = best_lda_model
                best_model.eval()
            else:
                small = MLPClassifier(standardize=standardize, input_dim=input_dim, num_classes=num_classes, h1=768, h2=384, n_blocks=2, dropout=0.1).to(device)
                if _count_trainable_params(small) <= param_limit:
                    small.eval()
                    best_model = small

        return best_model
