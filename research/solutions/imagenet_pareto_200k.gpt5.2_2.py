import os
import math
from typing import List, Optional, Tuple, Dict

import torch
import torch.nn as nn


def _count_trainable_params(model: nn.Module) -> int:
    return sum(p.numel() for p in model.parameters() if p.requires_grad)


def _extract_xy(batch):
    if isinstance(batch, (list, tuple)) and len(batch) == 2:
        return batch[0], batch[1]
    if isinstance(batch, dict):
        for kx in ("x", "inputs", "input", "features", "data"):
            if kx in batch:
                x = batch[kx]
                break
        else:
            raise ValueError("Cannot find inputs in batch dict")
        for ky in ("y", "targets", "target", "label", "labels"):
            if ky in batch:
                y = batch[ky]
                break
        else:
            raise ValueError("Cannot find targets in batch dict")
        return x, y
    raise ValueError("Unsupported batch format")


def _load_loader_to_tensors(loader, device: torch.device) -> Tuple[torch.Tensor, torch.Tensor]:
    xs = []
    ys = []
    for batch in loader:
        x, y = _extract_xy(batch)
        if not torch.is_tensor(x):
            x = torch.as_tensor(x)
        if not torch.is_tensor(y):
            y = torch.as_tensor(y)
        x = x.detach().to(device=device, dtype=torch.float32, non_blocking=True)
        y = y.detach().to(device=device, dtype=torch.long, non_blocking=True)
        if x.dim() > 2:
            x = x.view(x.shape[0], -1)
        xs.append(x)
        ys.append(y)
    X = torch.cat(xs, dim=0).contiguous()
    Y = torch.cat(ys, dim=0).contiguous()
    return X, Y


@torch.inference_mode()
def _batched_logits(model: nn.Module, X: torch.Tensor, batch_size: int = 1024) -> torch.Tensor:
    model.eval()
    n = X.shape[0]
    outs = []
    for i in range(0, n, batch_size):
        outs.append(model(X[i:i + batch_size]))
    return torch.cat(outs, dim=0)


@torch.inference_mode()
def _accuracy_from_logits(logits: torch.Tensor, y: torch.Tensor) -> float:
    return (logits.argmax(dim=1) == y).float().mean().item()


@torch.inference_mode()
def _accuracy(model: nn.Module, X: torch.Tensor, y: torch.Tensor, batch_size: int = 1024) -> float:
    logits = _batched_logits(model, X, batch_size=batch_size)
    return _accuracy_from_logits(logits, y)


class _InputNorm(nn.Module):
    def __init__(self, mean: torch.Tensor, std: torch.Tensor, eps: float = 1e-6):
        super().__init__()
        self.register_buffer("mean", mean.detach().clone().to(dtype=torch.float32))
        self.register_buffer("std", std.detach().clone().to(dtype=torch.float32))
        self.eps = float(eps)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        if x.dtype != torch.float32:
            x = x.float()
        return (x - self.mean) / (self.std + self.eps)


class _ResMLP(nn.Module):
    def __init__(
        self,
        input_dim: int,
        num_classes: int,
        hidden_dim: int,
        mean: torch.Tensor,
        std: torch.Tensor,
        input_dropout: float = 0.10,
        hidden_dropout: float = 0.15,
    ):
        super().__init__()
        self.norm = _InputNorm(mean, std)
        self.in_drop = nn.Dropout(p=float(input_dropout))
        self.fc1 = nn.Linear(input_dim, hidden_dim, bias=True)
        self.ln1 = nn.LayerNorm(hidden_dim, elementwise_affine=True)
        self.fc_res = nn.Linear(hidden_dim, hidden_dim, bias=True)
        self.ln_res = nn.LayerNorm(hidden_dim, elementwise_affine=True)
        self.h_drop = nn.Dropout(p=float(hidden_dropout))
        self.act = nn.GELU()
        self.out = nn.Linear(hidden_dim, num_classes, bias=True)

        for m in self.modules():
            if isinstance(m, nn.Linear):
                nn.init.kaiming_uniform_(m.weight, a=math.sqrt(5))
                if m.bias is not None:
                    fan_in, _ = nn.init._calculate_fan_in_and_fan_out(m.weight)
                    bound = 1 / math.sqrt(fan_in) if fan_in > 0 else 0
                    nn.init.uniform_(m.bias, -bound, bound)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self.norm(x)
        x = self.in_drop(x)
        x = self.act(self.ln1(self.fc1(x)))
        r = self.act(self.ln_res(self.fc_res(x)))
        r = self.h_drop(r)
        x = self.act(x + r)
        return self.out(x)


class _LDAModel(nn.Module):
    def __init__(self, mean: torch.Tensor, std: torch.Tensor, W: torch.Tensor, b: torch.Tensor):
        super().__init__()
        self.norm = _InputNorm(mean, std)
        self.register_buffer("W", W.detach().clone().to(dtype=torch.float32))
        self.register_buffer("b", b.detach().clone().to(dtype=torch.float32))

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self.norm(x)
        return x @ self.W.t() + self.b


class _CosinePrototypeModel(nn.Module):
    def __init__(self, mean: torch.Tensor, std: torch.Tensor, proto: torch.Tensor, scale: float = 12.0, eps: float = 1e-8):
        super().__init__()
        self.norm = _InputNorm(mean, std)
        p = proto.detach().clone().to(dtype=torch.float32)
        p = p / (p.norm(dim=1, keepdim=True) + eps)
        self.register_buffer("proto", p)
        self.register_buffer("scale", torch.tensor(float(scale), dtype=torch.float32))
        self.eps = float(eps)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self.norm(x)
        x = x / (x.norm(dim=1, keepdim=True) + self.eps)
        return (x @ self.proto.t()) * self.scale


class _DiagGaussianNBModel(nn.Module):
    def __init__(self, mean: torch.Tensor, std: torch.Tensor, mu: torch.Tensor, inv_var: torch.Tensor, bias: torch.Tensor):
        super().__init__()
        self.norm = _InputNorm(mean, std)
        self.register_buffer("mu_over_var", (mu * inv_var).detach().clone().to(dtype=torch.float32))
        self.register_buffer("inv_var", inv_var.detach().clone().to(dtype=torch.float32))
        self.register_buffer("bias", bias.detach().clone().to(dtype=torch.float32))

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self.norm(x)
        x2 = x * x
        term1 = x @ self.mu_over_var.t()
        term2 = x2 @ self.inv_var.t()
        return term1 - 0.5 * term2 + self.bias


class _LogitEnsemble(nn.Module):
    def __init__(self, models: List[nn.Module], weights: Optional[List[float]] = None):
        super().__init__()
        self.models = nn.ModuleList(models)
        if weights is None:
            weights = [1.0 / len(models)] * len(models)
        s = float(sum(weights))
        weights = [float(w) / s for w in weights]
        self.register_buffer("weights", torch.tensor(weights, dtype=torch.float32))

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        out = None
        for i, m in enumerate(self.models):
            w = self.weights[i]
            logits = m(x)
            out = logits.mul(w) if out is None else out.add(logits.mul(w))
        return out


def _compute_mean_std(X: torch.Tensor, eps: float = 1e-6) -> Tuple[torch.Tensor, torch.Tensor]:
    X64 = X.double()
    mean = X64.mean(dim=0)
    var = (X64 - mean).pow(2).mean(dim=0)
    std = var.sqrt().clamp_min(eps)
    return mean.float(), std.float()


def _compute_class_means(Xn: torch.Tensor, y: torch.Tensor, num_classes: int) -> torch.Tensor:
    d = Xn.shape[1]
    mu = torch.zeros((num_classes, d), dtype=Xn.dtype, device=Xn.device)
    counts = torch.zeros((num_classes,), dtype=torch.long, device=Xn.device)
    counts.scatter_add_(0, y, torch.ones_like(y, dtype=torch.long))
    mu.index_add_(0, y, Xn)
    mu = mu / counts.clamp_min(1).to(dtype=Xn.dtype).unsqueeze(1)
    return mu


def _try_cholesky(A: torch.Tensor, base_jitter: float = 1e-6, max_tries: int = 6) -> torch.Tensor:
    jitter = base_jitter
    I = torch.eye(A.shape[0], dtype=A.dtype, device=A.device)
    for _ in range(max_tries):
        try:
            return torch.linalg.cholesky(A + jitter * I)
        except RuntimeError:
            jitter *= 10.0
    return torch.linalg.cholesky(A + jitter * I)


def _build_lda(
    train_X: torch.Tensor,
    train_y: torch.Tensor,
    val_X: torch.Tensor,
    val_y: torch.Tensor,
    mean: torch.Tensor,
    std: torch.Tensor,
    num_classes: int,
) -> Tuple[nn.Module, float]:
    device = train_X.device
    Xn = ((train_X - mean) / (std + 1e-6)).double()
    yn = train_y
    mu = _compute_class_means(Xn, yn, num_classes)
    Xc = Xn - mu[yn]
    cov = (Xc.t() @ Xc) / max(1, Xc.shape[0])
    d = cov.shape[0]
    I = torch.eye(d, dtype=cov.dtype, device=device)

    Xv = ((val_X - mean) / (std + 1e-6)).double()
    best_acc = -1.0
    best_W = None
    best_b = None

    lambdas = [1e-4, 3e-4, 1e-3, 3e-3, 1e-2, 3e-2, 1e-1, 2e-1, 5e-1, 1.0]
    for lam in lambdas:
        cov_reg = cov + float(lam) * I
        L = _try_cholesky(cov_reg, base_jitter=1e-7, max_tries=6)
        inv_cov_mu_T = torch.cholesky_solve(mu.t().contiguous(), L)  # D x C
        W = inv_cov_mu_T.t().contiguous()  # C x D
        b = (-0.5 * (mu * W).sum(dim=1)).contiguous()

        logits = (Xv @ W.t()) + b
        acc = _accuracy_from_logits(logits.float(), val_y)
        if acc > best_acc:
            best_acc = acc
            best_W = W.float()
            best_b = b.float()

    model = _LDAModel(mean, std, best_W, best_b)
    return model, float(best_acc)


def _build_cosine_proto(
    train_X: torch.Tensor,
    train_y: torch.Tensor,
    val_X: torch.Tensor,
    val_y: torch.Tensor,
    mean: torch.Tensor,
    std: torch.Tensor,
    num_classes: int,
) -> Tuple[nn.Module, float]:
    Xn = ((train_X - mean) / (std + 1e-6)).float()
    mu = _compute_class_means(Xn, train_y, num_classes).float()

    best_acc = -1.0
    best_scale = 12.0
    for s in (6.0, 8.0, 10.0, 12.0, 14.0, 16.0, 20.0):
        model = _CosinePrototypeModel(mean, std, mu, scale=s)
        acc = _accuracy(model, val_X, val_y, batch_size=1024)
        if acc > best_acc:
            best_acc = acc
            best_scale = s
    model = _CosinePrototypeModel(mean, std, mu, scale=best_scale)
    return model, float(best_acc)


def _build_diag_gnb(
    train_X: torch.Tensor,
    train_y: torch.Tensor,
    val_X: torch.Tensor,
    val_y: torch.Tensor,
    mean: torch.Tensor,
    std: torch.Tensor,
    num_classes: int,
) -> Tuple[nn.Module, float]:
    device = train_X.device
    Xn = ((train_X - mean) / (std + 1e-6)).double()
    y = train_y
    mu = _compute_class_means(Xn, y, num_classes)  # C x D

    C, D = mu.shape
    counts = torch.zeros((C,), dtype=torch.long, device=device)
    counts.scatter_add_(0, y, torch.ones_like(y, dtype=torch.long))
    centered = Xn - mu[y]
    var = torch.zeros((C, D), dtype=Xn.dtype, device=device)
    var.index_add_(0, y, centered * centered)
    var = var / counts.clamp_min(1).to(dtype=Xn.dtype).unsqueeze(1)

    Xv = ((val_X - mean) / (std + 1e-6)).double()

    best_acc = -1.0
    best_alpha = 1e-2
    for alpha in (1e-4, 3e-4, 1e-3, 3e-3, 1e-2, 3e-2, 1e-1, 2e-1, 5e-1, 1.0):
        v = (var + float(alpha)).clamp_min(1e-8)
        inv_var = (1.0 / v).contiguous()
        bias = (-0.5 * (torch.log(v) + (mu * mu) * inv_var).sum(dim=1)).contiguous()
        logits = (Xv @ (mu * inv_var).t()) - 0.5 * ((Xv * Xv) @ inv_var.t()) + bias
        acc = _accuracy_from_logits(logits.float(), val_y)
        if acc > best_acc:
            best_acc = acc
            best_alpha = float(alpha)

    v = (var + best_alpha).clamp_min(1e-8)
    inv_var = (1.0 / v).contiguous().float()
    mu_f = mu.float()
    bias = (-0.5 * (torch.log(v).float() + (mu_f * mu_f) * inv_var).sum(dim=1)).contiguous()
    model = _DiagGaussianNBModel(mean, std, mu_f, inv_var, bias)
    return model, float(best_acc)


def _hidden_dim_max(input_dim: int, num_classes: int, param_limit: int) -> int:
    b = input_dim + num_classes + 6
    c = num_classes - param_limit
    disc = b * b - 4 * c
    if disc < 0:
        return 32
    s = int(math.isqrt(int(disc)))
    h = max(32, int((-b + s) // 2))
    def cnt(H):
        return H * H + H * b + num_classes
    while h > 32 and cnt(h) > param_limit:
        h -= 1
    return h


def _train_mlp(
    train_X: torch.Tensor,
    train_y: torch.Tensor,
    val_X: torch.Tensor,
    val_y: torch.Tensor,
    mean: torch.Tensor,
    std: torch.Tensor,
    input_dim: int,
    num_classes: int,
    param_limit: int,
) -> Tuple[nn.Module, float]:
    device = train_X.device
    hidden = _hidden_dim_max(input_dim, num_classes, param_limit)
    model = _ResMLP(
        input_dim=input_dim,
        num_classes=num_classes,
        hidden_dim=hidden,
        mean=mean,
        std=std,
        input_dropout=0.10,
        hidden_dropout=0.15,
    ).to(device)

    if _count_trainable_params(model) > param_limit:
        # Fallback: shrink hidden until it fits.
        while hidden > 32 and _count_trainable_params(model) > param_limit:
            hidden -= 1
            model = _ResMLP(input_dim, num_classes, hidden, mean, std).to(device)

    n = train_X.shape[0]
    batch_size = 512 if n >= 1024 else 256
    max_epochs = 140
    warmup_epochs = 6
    patience = 18
    min_epochs = 30

    optimizer = torch.optim.AdamW(model.parameters(), lr=2.5e-3, weight_decay=1e-2)
    criterion = nn.CrossEntropyLoss(label_smoothing=0.08)

    best_acc = -1.0
    best_state = None
    bad = 0

    for epoch in range(max_epochs):
        if epoch < warmup_epochs:
            lr = 2.5e-3 * float(epoch + 1) / float(warmup_epochs)
        else:
            t = float(epoch - warmup_epochs) / float(max(1, max_epochs - warmup_epochs - 1))
            lr = 3.0e-4 + 0.5 * (2.5e-3 - 3.0e-4) * (1.0 + math.cos(math.pi * t))
        for pg in optimizer.param_groups:
            pg["lr"] = lr

        model.train()
        perm = torch.randperm(n, device=device)
        for i in range(0, n, batch_size):
            idx = perm[i:i + batch_size]
            xb = train_X[idx]
            yb = train_y[idx]
            logits = model(xb)
            loss = criterion(logits, yb)
            optimizer.zero_grad(set_to_none=True)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()

        model.eval()
        with torch.inference_mode():
            vacc = _accuracy(model, val_X, val_y, batch_size=1024)

        if vacc > best_acc + 1e-4:
            best_acc = vacc
            best_state = {k: v.detach().clone() for k, v in model.state_dict().items()}
            bad = 0
        else:
            bad += 1

        if epoch >= min_epochs and bad >= patience:
            break

    if best_state is not None:
        model.load_state_dict(best_state, strict=True)
    model.eval()
    return model, float(best_acc)


class Solution:
    def solve(self, train_loader, val_loader, metadata: dict = None) -> torch.nn.Module:
        if metadata is None:
            metadata = {}
        device_str = metadata.get("device", "cpu")
        device = torch.device(device_str)

        try:
            cpu_threads = int(min(8, os.cpu_count() or 1))
            torch.set_num_threads(cpu_threads)
        except Exception:
            pass

        train_X, train_y = _load_loader_to_tensors(train_loader, device=device)
        val_X, val_y = _load_loader_to_tensors(val_loader, device=device)

        input_dim = int(metadata.get("input_dim", train_X.shape[1]))
        num_classes = int(metadata.get("num_classes", int(train_y.max().item()) + 1))
        param_limit = int(metadata.get("param_limit", 200_000))

        if train_X.shape[1] != input_dim:
            train_X = train_X.view(train_X.shape[0], -1)
            val_X = val_X.view(val_X.shape[0], -1)
            input_dim = train_X.shape[1]

        mean, std = _compute_mean_std(train_X, eps=1e-6)

        candidates: List[Tuple[float, nn.Module]] = []

        # Non-iterative classifiers
        try:
            lda_model, lda_acc = _build_lda(train_X, train_y, val_X, val_y, mean, std, num_classes)
            candidates.append((lda_acc, lda_model))
        except Exception:
            pass

        try:
            cos_model, cos_acc = _build_cosine_proto(train_X, train_y, val_X, val_y, mean, std, num_classes)
            candidates.append((cos_acc, cos_model))
        except Exception:
            pass

        try:
            gnb_model, gnb_acc = _build_diag_gnb(train_X, train_y, val_X, val_y, mean, std, num_classes)
            candidates.append((gnb_acc, gnb_model))
        except Exception:
            pass

        # Train MLP
        mlp_model, mlp_acc = _train_mlp(train_X, train_y, val_X, val_y, mean, std, input_dim, num_classes, param_limit)
        candidates.append((mlp_acc, mlp_model))

        # Ensembling (doesn't add trainable params if auxiliary models are parameter-free)
        aux_models = [m for a, m in candidates if not any(p.requires_grad for p in m.parameters())]
        for aux in aux_models:
            try:
                ens = _LogitEnsemble([mlp_model, aux], weights=[0.6, 0.4]).to(device)
                acc = _accuracy(ens, val_X, val_y, batch_size=1024)
                candidates.append((acc, ens))
            except Exception:
                pass

        if len(aux_models) >= 2:
            try:
                ens = _LogitEnsemble([mlp_model, aux_models[0], aux_models[1]], weights=[0.55, 0.25, 0.20]).to(device)
                acc = _accuracy(ens, val_X, val_y, batch_size=1024)
                candidates.append((acc, ens))
            except Exception:
                pass

        candidates.sort(key=lambda t: t[0], reverse=True)
        best_model = candidates[0][1]
        best_model.eval()

        if _count_trainable_params(best_model) > param_limit:
            # Hard fallback to a parameter-free model if somehow exceeded
            fallback = None
            for acc, m in candidates:
                if _count_trainable_params(m) <= param_limit:
                    fallback = m
                    break
            if fallback is not None:
                best_model = fallback
                best_model.eval()

        return best_model
