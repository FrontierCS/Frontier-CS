import os
import math
import time
import random
from typing import Optional, Tuple, List, Dict

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F


def _set_seeds(seed: int = 0) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)


def _count_trainable_params(model: nn.Module) -> int:
    return sum(p.numel() for p in model.parameters() if p.requires_grad)


def _flatten_inputs(x: torch.Tensor, input_dim: int) -> torch.Tensor:
    if not torch.is_tensor(x):
        x = torch.as_tensor(x)
    if x.ndim > 2:
        x = x.reshape(x.shape[0], -1)
    if x.ndim == 1:
        x = x.unsqueeze(0)
    if x.shape[-1] != input_dim:
        x = x.reshape(x.shape[0], input_dim)
    return x


def _collect_from_loader(loader, input_dim: int) -> Tuple[torch.Tensor, torch.Tensor]:
    xs = []
    ys = []
    for batch in loader:
        if isinstance(batch, (list, tuple)) and len(batch) >= 2:
            x, y = batch[0], batch[1]
        else:
            raise ValueError("Expected loader to yield (inputs, targets).")
        x = _flatten_inputs(x, input_dim)
        if not torch.is_tensor(y):
            y = torch.as_tensor(y)
        y = y.long().view(-1)
        xs.append(x.detach().cpu())
        ys.append(y.detach().cpu())
    X = torch.cat(xs, dim=0).contiguous()
    y = torch.cat(ys, dim=0).contiguous()
    if X.dtype != torch.float32:
        X = X.float()
    return X, y


@torch.inference_mode()
def _accuracy(model: nn.Module, X: torch.Tensor, y: torch.Tensor, batch_size: int = 1024, device: torch.device = torch.device("cpu")) -> float:
    model.eval()
    n = X.shape[0]
    correct = 0
    for i in range(0, n, batch_size):
        xb = X[i:i + batch_size].to(device, non_blocking=False)
        yb = y[i:i + batch_size].to(device, non_blocking=False)
        logits = model(xb)
        pred = logits.argmax(dim=1)
        correct += (pred == yb).sum().item()
    return correct / max(1, n)


def _ce_smooth(logits: torch.Tensor, target: torch.Tensor, eps: float) -> torch.Tensor:
    log_probs = F.log_softmax(logits, dim=1)
    nll = -log_probs.gather(dim=1, index=target.unsqueeze(1)).squeeze(1)
    smooth = -log_probs.mean(dim=1)
    return ((1.0 - eps) * nll + eps * smooth).mean()


class _CentroidModel(nn.Module):
    def __init__(self, mean: torch.Tensor, std: torch.Tensor, prototypes: torch.Tensor):
        super().__init__()
        self.register_buffer("mean", mean.clone().detach())
        self.register_buffer("invstd", (1.0 / std).clone().detach())
        self.register_buffer("prototypes", prototypes.clone().detach())
        bias = -(prototypes * prototypes).sum(dim=1)
        self.register_buffer("bias", bias.clone().detach())

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = _flatten_inputs(x, self.mean.numel()).to(dtype=torch.float32)
        x = (x - self.mean) * self.invstd
        logits = 2.0 * (x @ self.prototypes.t()) + self.bias
        return logits


class _LDAModel(nn.Module):
    def __init__(self, mean: torch.Tensor, std: torch.Tensor, W: torch.Tensor, b: torch.Tensor):
        super().__init__()
        self.register_buffer("mean", mean.clone().detach())
        self.register_buffer("invstd", (1.0 / std).clone().detach())
        self.register_buffer("W", W.clone().detach())
        self.register_buffer("b", b.clone().detach())

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = _flatten_inputs(x, self.mean.numel()).to(dtype=torch.float32)
        x = (x - self.mean) * self.invstd
        return x @ self.W + self.b


class _WideDeepMLP(nn.Module):
    def __init__(self, input_dim: int, hidden_dim: int, num_classes: int, mean: torch.Tensor, std: torch.Tensor, dropout: float = 0.12):
        super().__init__()
        self.register_buffer("mean", mean.clone().detach())
        self.register_buffer("invstd", (1.0 / std).clone().detach())

        self.fc1 = nn.Linear(input_dim, hidden_dim, bias=True)
        self.ln1 = nn.LayerNorm(hidden_dim, elementwise_affine=True)
        self.fc2 = nn.Linear(hidden_dim, hidden_dim, bias=True)
        self.ln2 = nn.LayerNorm(hidden_dim, elementwise_affine=True)
        self.fc3 = nn.Linear(hidden_dim, num_classes, bias=True)

        self.skip = nn.Linear(input_dim, num_classes, bias=True)

        self.drop = nn.Dropout(p=dropout)
        self.act = nn.GELU()

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = _flatten_inputs(x, self.mean.numel()).to(dtype=torch.float32)
        x = (x - self.mean) * self.invstd

        h = self.fc1(x)
        h = self.ln1(h)
        h = self.act(h)
        h = self.drop(h)

        h = self.fc2(h)
        h = self.ln2(h)
        h = self.act(h)
        h = self.drop(h)

        return self.fc3(h) + self.skip(x)


def _max_hidden_for_widedeep(input_dim: int, num_classes: int, param_limit: int) -> int:
    # Total params (trainable) for WideDeepMLP:
    # Deep part:
    # fc1: in*h + h
    # ln1: 2h
    # fc2: h*h + h
    # ln2: 2h
    # fc3: h*c + c
    # Skip:
    # skip: in*c + c
    # Total = h^2 + (in + c + 6)*h + (in*c + 2c)
    in_d = input_dim
    c = num_classes
    const = in_d * c + 2 * c
    coef = in_d + c + 6
    # Find max h by simple scan near quadratic root.
    # Start with an upper bound.
    h = int(max(8, math.sqrt(max(1, param_limit - const))))
    h = max(h, 8)
    # Increase until exceed, then step back.
    while True:
        total = h * h + coef * h + const
        if total > param_limit:
            break
        h += 1
        if h > 4096:
            break
    h -= 1
    if h < 8:
        h = 8
    # Safety: adjust down if needed.
    while h > 8 and (h * h + coef * h + const) > param_limit:
        h -= 1
    return h


def _fit_centroids(X_train: torch.Tensor, y_train: torch.Tensor, num_classes: int, mean: torch.Tensor, std: torch.Tensor) -> torch.Tensor:
    Xs = ((X_train - mean) / std).to(dtype=torch.float64)
    D = Xs.shape[1]
    C = num_classes
    sums = torch.zeros(C, D, dtype=torch.float64)
    counts = torch.bincount(y_train, minlength=C).to(dtype=torch.float64).clamp_min(1.0)
    sums.index_add_(0, y_train, Xs)
    protos = sums / counts.unsqueeze(1)
    return protos.to(dtype=torch.float32)


def _fit_lda(
    X_train: torch.Tensor,
    y_train: torch.Tensor,
    num_classes: int,
    mean: torch.Tensor,
    std: torch.Tensor,
    alpha: float,
    jitter: float = 1e-4,
) -> Optional[Tuple[torch.Tensor, torch.Tensor]]:
    Xs = ((X_train - mean) / std).to(dtype=torch.float64)
    N, D = Xs.shape
    C = num_classes

    sums = torch.zeros(C, D, dtype=torch.float64)
    counts = torch.bincount(y_train, minlength=C).to(dtype=torch.float64).clamp_min(1.0)
    sums.index_add_(0, y_train, Xs)
    mu = sums / counts.unsqueeze(1)  # (C, D)

    centered = Xs - mu[y_train]  # within-class centered
    S = centered.t().matmul(centered)
    denom = max(1.0, float(N - C))
    Sigma = S / denom

    tr = torch.trace(Sigma)
    avg_var = (tr / D) if D > 0 else torch.tensor(1.0, dtype=torch.float64)
    I = torch.eye(D, dtype=torch.float64)
    Sigma_sh = (1.0 - alpha) * Sigma + alpha * avg_var * I
    Sigma_sh = Sigma_sh + jitter * avg_var * I

    try:
        L = torch.linalg.cholesky(Sigma_sh)
    except Exception:
        try:
            Sigma_sh2 = Sigma_sh + (10.0 * jitter) * avg_var * I
            L = torch.linalg.cholesky(Sigma_sh2)
        except Exception:
            return None

    mu_T = mu.t().contiguous()  # (D, C)
    W = torch.cholesky_solve(mu_T, L)  # (D, C) = Sigma^-1 * mu^T
    # bias: -0.5 * mu_c^T Sigma^-1 mu_c
    quad = (mu_T * W).sum(dim=0)  # (C,)
    b = -0.5 * quad

    return W.to(dtype=torch.float32), b.to(dtype=torch.float32)


def _build_param_groups(model: nn.Module, weight_decay: float) -> List[Dict]:
    decay = []
    no_decay = []
    for name, p in model.named_parameters():
        if not p.requires_grad:
            continue
        if p.ndim >= 2 and ("ln" not in name.lower()) and (not name.lower().endswith("bias")):
            decay.append(p)
        else:
            no_decay.append(p)
    groups = []
    if decay:
        groups.append({"params": decay, "weight_decay": weight_decay})
    if no_decay:
        groups.append({"params": no_decay, "weight_decay": 0.0})
    return groups


class Solution:
    def solve(self, train_loader, val_loader, metadata: dict = None) -> torch.nn.Module:
        if metadata is None:
            metadata = {}
        device = torch.device(metadata.get("device", "cpu"))
        input_dim = int(metadata.get("input_dim", 384))
        num_classes = int(metadata.get("num_classes", 128))
        param_limit = int(metadata.get("param_limit", 200_000))

        try:
            n_threads = int(os.environ.get("OMP_NUM_THREADS", "0") or 0)
        except Exception:
            n_threads = 0
        if n_threads <= 0:
            n_threads = min(8, os.cpu_count() or 8)
        try:
            torch.set_num_threads(n_threads)
        except Exception:
            pass

        _set_seeds(0)

        X_train, y_train = _collect_from_loader(train_loader, input_dim)
        X_val, y_val = _collect_from_loader(val_loader, input_dim)

        mean = X_train.mean(dim=0, dtype=torch.float64).to(dtype=torch.float32)
        std = X_train.std(dim=0, unbiased=False, dtype=torch.float64).clamp_min(1e-6).to(dtype=torch.float32)

        best_model: nn.Module = None
        best_val_acc = -1.0

        # Analytic baseline: centroid classifier
        protos = _fit_centroids(X_train, y_train, num_classes, mean, std)
        centroid_model = _CentroidModel(mean, std, protos).to(device)
        centroid_val = _accuracy(centroid_model, X_val, y_val, batch_size=1024, device=device)
        best_model, best_val_acc = centroid_model, centroid_val

        # Analytic: LDA with shrinkage selection
        alphas = [0.0, 0.03, 0.06, 0.1, 0.2, 0.35]
        for a in alphas:
            fitted = _fit_lda(X_train, y_train, num_classes, mean, std, alpha=a, jitter=1e-4)
            if fitted is None:
                continue
            W, b = fitted
            lda_model = _LDAModel(mean, std, W, b).to(device)
            lda_val = _accuracy(lda_model, X_val, y_val, batch_size=1024, device=device)
            if lda_val > best_val_acc + 1e-6:
                best_model, best_val_acc = lda_model, lda_val

        # If analytic is already very good, return it.
        if best_val_acc >= 0.92:
            best_model.eval()
            return best_model

        # Trainable model: Wide+Deep MLP (kept under parameter budget)
        hidden_dim = _max_hidden_for_widedeep(input_dim, num_classes, param_limit)
        mlp = _WideDeepMLP(input_dim, hidden_dim, num_classes, mean, std, dropout=0.12).to(device)

        # Ensure budget
        while _count_trainable_params(mlp) > param_limit and hidden_dim > 8:
            hidden_dim -= 1
            mlp = _WideDeepMLP(input_dim, hidden_dim, num_classes, mean, std, dropout=0.12).to(device)

        # If something went wrong, fall back to best analytic.
        if _count_trainable_params(mlp) > param_limit:
            best_model.eval()
            return best_model

        train_ds = torch.utils.data.TensorDataset(X_train, y_train)
        train_bs = 256 if X_train.shape[0] >= 256 else max(32, 2 ** int(math.floor(math.log2(max(32, X_train.shape[0])))))
        train_dl = torch.utils.data.DataLoader(train_ds, batch_size=train_bs, shuffle=True, drop_last=False, num_workers=0)

        weight_decay = 1.0e-2
        lr_max = 4.0e-3
        param_groups = _build_param_groups(mlp, weight_decay=weight_decay)
        optimizer = torch.optim.AdamW(param_groups, lr=lr_max, betas=(0.9, 0.95), eps=1e-8)

        epochs = 160
        steps_per_epoch = max(1, math.ceil(len(train_ds) / train_bs))
        total_steps = epochs * steps_per_epoch
        warmup_steps = max(10, int(0.08 * total_steps))

        def lr_at_step(step: int) -> float:
            if step < warmup_steps:
                return lr_max * (step + 1) / warmup_steps
            t = (step - warmup_steps) / max(1, (total_steps - warmup_steps))
            return lr_max * 0.5 * (1.0 + math.cos(math.pi * t))

        eps_ls = 0.06
        mixup_alpha = 0.20
        mixup_until = int(0.75 * epochs)

        best_mlp_state = None
        best_mlp_val = -1.0
        patience = 25
        bad_epochs = 0
        global_step = 0
        t0 = time.time()

        for epoch in range(epochs):
            mlp.train()
            use_mix = epoch < mixup_until and mixup_alpha > 0.0

            for xb, yb in train_dl:
                xb = xb.to(device, non_blocking=False)
                yb = yb.to(device, non_blocking=False)

                for pg in optimizer.param_groups:
                    pg["lr"] = lr_at_step(global_step)

                if use_mix and xb.shape[0] >= 2:
                    lam = np.random.beta(mixup_alpha, mixup_alpha)
                    perm = torch.randperm(xb.shape[0], device=device)
                    xb2 = xb[perm]
                    y2 = yb[perm]
                    xmix = xb.mul(lam).add_(xb2, alpha=(1.0 - lam))
                    logits = mlp(xmix)
                    loss = lam * _ce_smooth(logits, yb, eps_ls) + (1.0 - lam) * _ce_smooth(logits, y2, eps_ls)
                else:
                    logits = mlp(xb)
                    loss = _ce_smooth(logits, yb, eps_ls)

                optimizer.zero_grad(set_to_none=True)
                loss.backward()
                torch.nn.utils.clip_grad_norm_(mlp.parameters(), 1.0)
                optimizer.step()

                global_step += 1

            val_acc = _accuracy(mlp, X_val, y_val, batch_size=1024, device=device)

            if val_acc > best_mlp_val + 1e-6:
                best_mlp_val = val_acc
                best_mlp_state = {k: v.detach().cpu().clone() for k, v in mlp.state_dict().items()}
                bad_epochs = 0
            else:
                bad_epochs += 1

            if bad_epochs >= patience:
                break

            if time.time() - t0 > 45.0 and best_mlp_val >= best_val_acc + 1e-3:
                # Quick exit if we already beat analytic and time is passing (usually not needed).
                break

        if best_mlp_state is not None:
            mlp.load_state_dict(best_mlp_state, strict=True)

        mlp_val = _accuracy(mlp, X_val, y_val, batch_size=1024, device=device)

        if mlp_val > best_val_acc + 1e-6:
            mlp.eval()
            return mlp

        best_model.eval()
        return best_model