import os
import math
import copy
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F


class _Standardize(nn.Module):
    def __init__(self, mean: torch.Tensor, std: torch.Tensor):
        super().__init__()
        mean = mean.detach().to(dtype=torch.float32).view(1, -1)
        std = std.detach().to(dtype=torch.float32).view(1, -1)
        std = torch.clamp(std, min=1e-6)
        self.register_buffer("mean", mean)
        self.register_buffer("inv_std", 1.0 / std)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        if not torch.is_tensor(x):
            x = torch.as_tensor(x)
        x = x.to(dtype=torch.float32)
        return (x - self.mean) * self.inv_std


class _LDAModel(nn.Module):
    def __init__(self, mean: torch.Tensor, std: torch.Tensor, weight: torch.Tensor, bias: torch.Tensor):
        super().__init__()
        self.std_layer = _Standardize(mean, std)
        self.register_buffer("weight", weight.detach().to(dtype=torch.float32))  # (C, D)
        self.register_buffer("bias", bias.detach().to(dtype=torch.float32))      # (C,)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self.std_layer(x)
        return x.matmul(self.weight.t()) + self.bias


class _FFNBlock(nn.Module):
    def __init__(self, dim: int, mlp_dim: int, dropout: float):
        super().__init__()
        self.ln = nn.LayerNorm(dim)
        self.fc1 = nn.Linear(dim, mlp_dim, bias=True)
        self.fc2 = nn.Linear(mlp_dim, dim, bias=True)
        self.drop = nn.Dropout(dropout)
        self.act = nn.GELU()

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        h = self.ln(x)
        h = self.fc1(h)
        h = self.act(h)
        h = self.drop(h)
        h = self.fc2(h)
        h = self.drop(h)
        return x + h


class _ResFFNClassifier(nn.Module):
    def __init__(self, input_dim: int, num_classes: int, mean: torch.Tensor, std: torch.Tensor, n_blocks: int, mlp_dim: int, dropout: float):
        super().__init__()
        self.std_layer = _Standardize(mean, std)
        self.blocks = nn.ModuleList([_FFNBlock(input_dim, mlp_dim, dropout) for _ in range(n_blocks)])
        self.ln_out = nn.LayerNorm(input_dim)
        self.head = nn.Linear(input_dim, num_classes, bias=True)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self.std_layer(x)
        for b in self.blocks:
            x = b(x)
        x = self.ln_out(x)
        return self.head(x)


def _count_trainable_params(model: nn.Module) -> int:
    return sum(p.numel() for p in model.parameters() if p.requires_grad)


@torch.inference_mode()
def _accuracy(model: nn.Module, X: torch.Tensor, y: torch.Tensor, batch_size: int = 512) -> float:
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


def _collect_from_loader(loader):
    xs, ys = [], []
    for xb, yb in loader:
        if not torch.is_tensor(xb):
            xb = torch.as_tensor(xb)
        if not torch.is_tensor(yb):
            yb = torch.as_tensor(yb)
        xs.append(xb.detach().cpu())
        ys.append(yb.detach().cpu())
    X = torch.cat(xs, dim=0).to(dtype=torch.float32)
    y = torch.cat(ys, dim=0).to(dtype=torch.long)
    return X, y


def _soft_cross_entropy(logits: torch.Tensor, target_probs: torch.Tensor) -> torch.Tensor:
    logp = F.log_softmax(logits, dim=1)
    return -(target_probs * logp).sum(dim=1).mean()


def _one_hot(y: torch.Tensor, num_classes: int) -> torch.Tensor:
    return F.one_hot(y, num_classes=num_classes).to(dtype=torch.float32)


def _fit_lda(X_train: torch.Tensor, y_train: torch.Tensor, X_val: torch.Tensor, y_val: torch.Tensor, input_dim: int, num_classes: int, alpha_list):
    # Standardize from train only
    Xtr64 = X_train.to(dtype=torch.float64)
    mean = Xtr64.mean(dim=0)
    std = Xtr64.std(dim=0, unbiased=False)
    std = torch.clamp(std, min=1e-6)

    Xtr = ((Xtr64 - mean) / std).to(dtype=torch.float64)
    Xva = (((X_val.to(dtype=torch.float64) - mean) / std)).to(dtype=torch.float64)

    counts = torch.bincount(y_train, minlength=num_classes).to(dtype=torch.float64)
    priors = counts / counts.sum().clamp_min(1.0)
    log_priors = torch.log(priors.clamp_min(1e-12))

    means = torch.zeros((num_classes, input_dim), dtype=torch.float64)
    for c in range(num_classes):
        idx = (y_train == c).nonzero(as_tuple=False).view(-1)
        if idx.numel() > 0:
            means[c] = Xtr.index_select(0, idx).mean(dim=0)

    # Pooled covariance
    Xc = Xtr - means.index_select(0, y_train)
    denom = max(1, X_train.shape[0] - num_classes)
    cov = (Xc.t().matmul(Xc)) / float(denom)

    tr_cov = torch.trace(cov).clamp_min(1e-12)
    avg_var = tr_cov / float(input_dim)
    eye = torch.eye(input_dim, dtype=torch.float64)

    best_acc = -1.0
    best_alpha = None
    best_weight = None
    best_bias = None

    for alpha in alpha_list:
        cov_reg = (1.0 - alpha) * cov + alpha * avg_var * eye
        # extra jitter for safety
        cov_reg = cov_reg + (1e-6 * avg_var) * eye
        try:
            L = torch.linalg.cholesky(cov_reg)
        except Exception:
            cov_reg = cov_reg + (1e-3 * avg_var) * eye
            L = torch.linalg.cholesky(cov_reg)

        W = torch.cholesky_solve(means.t(), L)  # (D, C)
        quad = 0.5 * (means * W.t()).sum(dim=1)  # (C,)
        b = -quad + log_priors
        weight = W.t().to(dtype=torch.float32)  # (C, D)
        bias = b.to(dtype=torch.float32)        # (C,)

        lda_model = _LDAModel(mean.to(dtype=torch.float32), std.to(dtype=torch.float32), weight, bias)
        acc = _accuracy(lda_model, X_val, y_val, batch_size=512)
        if acc > best_acc:
            best_acc = acc
            best_alpha = alpha
            best_weight = weight
            best_bias = bias

    # Return best model trained on train only (for selection)
    best_model = _LDAModel(mean.to(dtype=torch.float32), std.to(dtype=torch.float32), best_weight, best_bias)
    return best_model, best_acc, best_alpha


def _compute_blocks_and_mlpdim(input_dim: int, num_classes: int, param_limit: int):
    dim = int(input_dim)
    # choose mlp_dim around dim/4 but not too small
    mlp_dim = max(32, int(round(dim * 0.25)))
    # params for one block: LN(2d) + fc1(d*mlp+mlp) + fc2(mlp*d + d)
    block_params = (2 * dim) + (dim * mlp_dim + mlp_dim) + (mlp_dim * dim + dim)
    # head: ln_out (2d) + linear (d*C + C)
    head_params = (2 * dim) + (dim * num_classes + num_classes)
    rem = param_limit - head_params
    if rem < block_params:
        n_blocks = 1
        # make sure at least a tiny block fits; reduce mlp_dim if necessary
        while True:
            block_params = (2 * dim) + (dim * mlp_dim + mlp_dim) + (mlp_dim * dim + dim)
            if head_params + block_params <= param_limit or mlp_dim <= 8:
                break
            mlp_dim = max(8, mlp_dim // 2)
    else:
        n_blocks = int(rem // block_params)
        n_blocks = max(1, min(n_blocks, 12))
        # try to use as much budget as possible by increasing blocks if possible (already floor)
    return n_blocks, mlp_dim


def _train_resffn_phase(
    X_train: torch.Tensor,
    y_train: torch.Tensor,
    X_val: torch.Tensor,
    y_val: torch.Tensor,
    input_dim: int,
    num_classes: int,
    param_limit: int,
    mean: torch.Tensor,
    std: torch.Tensor,
    n_blocks: int,
    mlp_dim: int,
    dropout: float,
    epochs: int,
    batch_size: int,
    lr_max: float,
    weight_decay: float,
    label_smoothing: float,
    mixup_alpha: float,
    mixup_prob: float,
    noise_std: float,
    ema_decay: float,
    eval_every: int,
    patience: int,
    seed: int
):
    g = torch.Generator(device="cpu")
    g.manual_seed(seed)

    model = _ResFFNClassifier(input_dim, num_classes, mean, std, n_blocks=n_blocks, mlp_dim=mlp_dim, dropout=dropout)
    if _count_trainable_params(model) > param_limit:
        # Try reducing blocks and/or mlp_dim
        while n_blocks > 1 and _count_trainable_params(model) > param_limit:
            n_blocks -= 1
            model = _ResFFNClassifier(input_dim, num_classes, mean, std, n_blocks=n_blocks, mlp_dim=mlp_dim, dropout=dropout)
        while _count_trainable_params(model) > param_limit and mlp_dim > 8:
            mlp_dim = max(8, mlp_dim // 2)
            model = _ResFFNClassifier(input_dim, num_classes, mean, std, n_blocks=n_blocks, mlp_dim=mlp_dim, dropout=dropout)
    assert _count_trainable_params(model) <= param_limit

    ema_model = copy.deepcopy(model)
    for p in ema_model.parameters():
        p.requires_grad_(False)

    opt = torch.optim.AdamW(model.parameters(), lr=lr_max, weight_decay=weight_decay)

    n = X_train.shape[0]
    bs = max(32, int(batch_size))
    bs = min(bs, n)

    best_val = -1.0
    best_epoch = 0
    best_state = None

    no_improve = 0

    def set_lr(ep: int):
        warmup = max(3, min(10, epochs // 10))
        if ep < warmup:
            lr = lr_max * float(ep + 1) / float(warmup)
        else:
            t = float(ep - warmup) / float(max(1, epochs - warmup))
            lr = lr_max * 0.5 * (1.0 + math.cos(math.pi * t))
        for pg in opt.param_groups:
            pg["lr"] = lr

    for ep in range(epochs):
        model.train()
        set_lr(ep)

        perm = torch.randperm(n, generator=g)
        for i in range(0, n, bs):
            idx = perm[i:i + bs]
            xb = X_train.index_select(0, idx)
            yb = y_train.index_select(0, idx)

            if noise_std > 0:
                xb = xb + noise_std * torch.randn_like(xb, generator=g)

            if mixup_alpha > 0 and (torch.rand((), generator=g).item() < mixup_prob) and xb.shape[0] > 1:
                lam = np.random.beta(mixup_alpha, mixup_alpha)
                lam = float(lam)
                p2 = torch.randperm(xb.shape[0], generator=g)
                xb2 = xb.index_select(0, p2)
                yb2 = yb.index_select(0, p2)

                t1 = _one_hot(yb, num_classes)
                t2 = _one_hot(yb2, num_classes)
                if label_smoothing > 0:
                    t1 = t1 * (1.0 - label_smoothing) + (label_smoothing / float(num_classes))
                    t2 = t2 * (1.0 - label_smoothing) + (label_smoothing / float(num_classes))
                tb = lam * t1 + (1.0 - lam) * t2
                xb = lam * xb + (1.0 - lam) * xb2
            else:
                tb = _one_hot(yb, num_classes)
                if label_smoothing > 0:
                    tb = tb * (1.0 - label_smoothing) + (label_smoothing / float(num_classes))

            opt.zero_grad(set_to_none=True)
            logits = model(xb)
            loss = _soft_cross_entropy(logits, tb)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            opt.step()

            with torch.no_grad():
                for p, pe in zip(model.parameters(), ema_model.parameters()):
                    pe.mul_(ema_decay).add_(p, alpha=(1.0 - ema_decay))

        if (ep + 1) % eval_every == 0:
            val_acc = _accuracy(ema_model, X_val, y_val, batch_size=512)
            if val_acc > best_val + 1e-6:
                best_val = val_acc
                best_epoch = ep + 1
                best_state = copy.deepcopy(ema_model.state_dict())
                no_improve = 0
            else:
                no_improve += 1

            if no_improve >= patience:
                break

    if best_state is None:
        best_val = _accuracy(ema_model, X_val, y_val, batch_size=512)
        best_epoch = max(1, epochs // 2)
        best_state = copy.deepcopy(ema_model.state_dict())

    ema_model.load_state_dict(best_state, strict=True)
    return ema_model, best_val, best_epoch, n_blocks, mlp_dim


def _train_resffn_fixed_epochs(
    X: torch.Tensor,
    y: torch.Tensor,
    input_dim: int,
    num_classes: int,
    param_limit: int,
    mean: torch.Tensor,
    std: torch.Tensor,
    n_blocks: int,
    mlp_dim: int,
    dropout: float,
    epochs: int,
    batch_size: int,
    lr_max: float,
    weight_decay: float,
    label_smoothing: float,
    mixup_alpha: float,
    mixup_prob: float,
    noise_std: float,
    ema_decay: float,
    seed: int
):
    g = torch.Generator(device="cpu")
    g.manual_seed(seed)

    model = _ResFFNClassifier(input_dim, num_classes, mean, std, n_blocks=n_blocks, mlp_dim=mlp_dim, dropout=dropout)
    if _count_trainable_params(model) > param_limit:
        while n_blocks > 1 and _count_trainable_params(model) > param_limit:
            n_blocks -= 1
            model = _ResFFNClassifier(input_dim, num_classes, mean, std, n_blocks=n_blocks, mlp_dim=mlp_dim, dropout=dropout)
        while _count_trainable_params(model) > param_limit and mlp_dim > 8:
            mlp_dim = max(8, mlp_dim // 2)
            model = _ResFFNClassifier(input_dim, num_classes, mean, std, n_blocks=n_blocks, mlp_dim=mlp_dim, dropout=dropout)
    assert _count_trainable_params(model) <= param_limit

    ema_model = copy.deepcopy(model)
    for p in ema_model.parameters():
        p.requires_grad_(False)

    opt = torch.optim.AdamW(model.parameters(), lr=lr_max, weight_decay=weight_decay)

    n = X.shape[0]
    bs = max(32, int(batch_size))
    bs = min(bs, n)

    def set_lr(ep: int):
        warmup = max(3, min(10, epochs // 10))
        if ep < warmup:
            lr = lr_max * float(ep + 1) / float(warmup)
        else:
            t = float(ep - warmup) / float(max(1, epochs - warmup))
            lr = lr_max * 0.5 * (1.0 + math.cos(math.pi * t))
        for pg in opt.param_groups:
            pg["lr"] = lr

    for ep in range(epochs):
        model.train()
        set_lr(ep)

        perm = torch.randperm(n, generator=g)
        for i in range(0, n, bs):
            idx = perm[i:i + bs]
            xb = X.index_select(0, idx)
            yb = y.index_select(0, idx)

            if noise_std > 0:
                xb = xb + noise_std * torch.randn_like(xb, generator=g)

            if mixup_alpha > 0 and (torch.rand((), generator=g).item() < mixup_prob) and xb.shape[0] > 1:
                lam = np.random.beta(mixup_alpha, mixup_alpha)
                lam = float(lam)
                p2 = torch.randperm(xb.shape[0], generator=g)
                xb2 = xb.index_select(0, p2)
                yb2 = yb.index_select(0, p2)

                t1 = _one_hot(yb, num_classes)
                t2 = _one_hot(yb2, num_classes)
                if label_smoothing > 0:
                    t1 = t1 * (1.0 - label_smoothing) + (label_smoothing / float(num_classes))
                    t2 = t2 * (1.0 - label_smoothing) + (label_smoothing / float(num_classes))
                tb = lam * t1 + (1.0 - lam) * t2
                xb = lam * xb + (1.0 - lam) * xb2
            else:
                tb = _one_hot(yb, num_classes)
                if label_smoothing > 0:
                    tb = tb * (1.0 - label_smoothing) + (label_smoothing / float(num_classes))

            opt.zero_grad(set_to_none=True)
            logits = model(xb)
            loss = _soft_cross_entropy(logits, tb)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            opt.step()

            with torch.no_grad():
                for p, pe in zip(model.parameters(), ema_model.parameters()):
                    pe.mul_(ema_decay).add_(p, alpha=(1.0 - ema_decay))

    ema_model.eval()
    return ema_model


class Solution:
    def solve(self, train_loader, val_loader, metadata: dict = None) -> torch.nn.Module:
        if metadata is None:
            metadata = {}
        input_dim = int(metadata.get("input_dim", 384))
        num_classes = int(metadata.get("num_classes", 128))
        param_limit = int(metadata.get("param_limit", 500_000))
        device = torch.device(metadata.get("device", "cpu"))

        try:
            torch.set_num_threads(min(8, os.cpu_count() or 8))
        except Exception:
            pass

        torch.manual_seed(0)
        np.random.seed(0)

        X_train, y_train = _collect_from_loader(train_loader)
        X_val, y_val = _collect_from_loader(val_loader)

        X_train = X_train[:, :input_dim].contiguous()
        X_val = X_val[:, :input_dim].contiguous()

        # Standardization stats for neural model (train only, to avoid leakage in phase 1)
        mean_train = X_train.mean(dim=0)
        std_train = X_train.std(dim=0, unbiased=False).clamp_min(1e-6)

        # 1) LDA candidate tuned on val
        alpha_list = [0.0, 0.01, 0.05, 0.1, 0.2, 0.35, 0.5]
        lda_model_sel, lda_val_acc, best_alpha = _fit_lda(X_train, y_train, X_val, y_val, input_dim, num_classes, alpha_list)

        # 2) ResFFN candidate: phase 1 train on train, validate on val
        n_blocks, mlp_dim = _compute_blocks_and_mlpdim(input_dim, num_classes, param_limit)

        # Hyperparams
        dropout = 0.10
        epochs_phase1 = 250
        batch_size = 128
        lr_max = 3e-3
        weight_decay = 1.0e-2
        label_smoothing = 0.05
        mixup_alpha = 0.20
        mixup_prob = 0.70
        noise_std = 0.02
        ema_decay = 0.995
        eval_every = 1
        patience = 35

        res_model_sel, res_val_acc, best_epoch, n_blocks_used, mlp_dim_used = _train_resffn_phase(
            X_train=X_train,
            y_train=y_train,
            X_val=X_val,
            y_val=y_val,
            input_dim=input_dim,
            num_classes=num_classes,
            param_limit=param_limit,
            mean=mean_train,
            std=std_train,
            n_blocks=n_blocks,
            mlp_dim=mlp_dim,
            dropout=dropout,
            epochs=epochs_phase1,
            batch_size=batch_size,
            lr_max=lr_max,
            weight_decay=weight_decay,
            label_smoothing=label_smoothing,
            mixup_alpha=mixup_alpha,
            mixup_prob=mixup_prob,
            noise_std=noise_std,
            ema_decay=ema_decay,
            eval_every=eval_every,
            patience=patience,
            seed=1
        )

        # Select winner based on val accuracy (phase 1)
        use_resffn = (res_val_acc >= lda_val_acc)

        # Phase 2: fit final model on train+val for best_epoch epochs (or LDA with best alpha)
        X_full = torch.cat([X_train, X_val], dim=0)
        y_full = torch.cat([y_train, y_val], dim=0)

        mean_full = X_full.mean(dim=0)
        std_full = X_full.std(dim=0, unbiased=False).clamp_min(1e-6)

        if use_resffn:
            final_epochs = max(10, int(best_epoch))
            final_model = _train_resffn_fixed_epochs(
                X=X_full,
                y=y_full,
                input_dim=input_dim,
                num_classes=num_classes,
                param_limit=param_limit,
                mean=mean_full,
                std=std_full,
                n_blocks=n_blocks_used,
                mlp_dim=mlp_dim_used,
                dropout=dropout,
                epochs=final_epochs,
                batch_size=batch_size,
                lr_max=lr_max,
                weight_decay=weight_decay,
                label_smoothing=label_smoothing,
                mixup_alpha=mixup_alpha,
                mixup_prob=mixup_prob,
                noise_std=noise_std,
                ema_decay=ema_decay,
                seed=2
            )
        else:
            # Fit LDA on full data using chosen alpha and full-data standardization
            X64 = X_full.to(dtype=torch.float64)
            mean = X64.mean(dim=0)
            std = X64.std(dim=0, unbiased=False).clamp_min(1e-6)
            Xs = ((X64 - mean) / std).to(dtype=torch.float64)

            counts = torch.bincount(y_full, minlength=num_classes).to(dtype=torch.float64)
            priors = counts / counts.sum().clamp_min(1.0)
            log_priors = torch.log(priors.clamp_min(1e-12))

            means = torch.zeros((num_classes, input_dim), dtype=torch.float64)
            for c in range(num_classes):
                idx = (y_full == c).nonzero(as_tuple=False).view(-1)
                if idx.numel() > 0:
                    means[c] = Xs.index_select(0, idx).mean(dim=0)

            Xc = Xs - means.index_select(0, y_full)
            denom = max(1, X_full.shape[0] - num_classes)
            cov = (Xc.t().matmul(Xc)) / float(denom)

            tr_cov = torch.trace(cov).clamp_min(1e-12)
            avg_var = tr_cov / float(input_dim)
            eye = torch.eye(input_dim, dtype=torch.float64)

            alpha = float(best_alpha) if best_alpha is not None else 0.1
            cov_reg = (1.0 - alpha) * cov + alpha * avg_var * eye
            cov_reg = cov_reg + (1e-6 * avg_var) * eye
            try:
                L = torch.linalg.cholesky(cov_reg)
            except Exception:
                cov_reg = cov_reg + (1e-3 * avg_var) * eye
                L = torch.linalg.cholesky(cov_reg)

            W = torch.cholesky_solve(means.t(), L)  # (D, C)
            quad = 0.5 * (means * W.t()).sum(dim=1)  # (C,)
            b = -quad + log_priors

            final_model = _LDAModel(mean.to(dtype=torch.float32), std.to(dtype=torch.float32), W.t().to(dtype=torch.float32), b.to(dtype=torch.float32))

        # Safety: ensure within param limit
        trainable = _count_trainable_params(final_model)
        if trainable > param_limit:
            # fallback to LDA (small)
            final_model = lda_model_sel
        final_model.to(device)
        final_model.eval()
        return final_model