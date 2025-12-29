import os
import math
import random
from typing import Dict, Optional, Tuple, List

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F


def _set_threads():
    try:
        n = os.cpu_count() or 8
    except Exception:
        n = 8
    torch.set_num_threads(min(8, n))


def _seed_all(seed: int = 0):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)


def _count_trainable_params(model: nn.Module) -> int:
    return sum(p.numel() for p in model.parameters() if p.requires_grad)


def _collect_xy(loader) -> Tuple[torch.Tensor, torch.Tensor]:
    xs = []
    ys = []
    for batch in loader:
        if isinstance(batch, (tuple, list)) and len(batch) >= 2:
            x, y = batch[0], batch[1]
        else:
            raise ValueError("Dataloader batch must be (inputs, targets).")
        if not torch.is_tensor(x):
            x = torch.as_tensor(x)
        if not torch.is_tensor(y):
            y = torch.as_tensor(y)
        xs.append(x.detach().to("cpu"))
        ys.append(y.detach().to("cpu"))
    X = torch.cat(xs, dim=0).contiguous().float()
    y = torch.cat(ys, dim=0).contiguous().long()
    return X, y


@torch.no_grad()
def _accuracy_from_logits(logits: torch.Tensor, y: torch.Tensor) -> float:
    preds = logits.argmax(dim=1)
    return (preds == y).float().mean().item()


@torch.no_grad()
def _batched_logits(model: nn.Module, X: torch.Tensor, batch_size: int = 1024) -> torch.Tensor:
    model.eval()
    outs = []
    for i in range(0, X.shape[0], batch_size):
        outs.append(model(X[i:i + batch_size]))
    return torch.cat(outs, dim=0)


def _safe_cholesky(A: torch.Tensor, base_jitter: float = 1e-6, max_tries: int = 8) -> torch.Tensor:
    jitter = base_jitter
    for _ in range(max_tries):
        try:
            return torch.linalg.cholesky(A)
        except Exception:
            A = A + jitter * torch.eye(A.shape[0], dtype=A.dtype, device=A.device)
            jitter *= 10.0
    return torch.linalg.cholesky(A)


def _fit_shrinkage_lda(
    X: torch.Tensor,
    y: torch.Tensor,
    num_classes: int,
    reg: float,
) -> Tuple[torch.Tensor, torch.Tensor]:
    Xd = X.double()
    N, d = Xd.shape
    C = num_classes

    counts = torch.bincount(y, minlength=C).double()
    counts_clamped = counts.clamp_min(1.0)

    mu = torch.zeros((C, d), dtype=torch.float64)
    mu.index_add_(0, y, Xd)
    mu = mu / counts_clamped.unsqueeze(1)

    Xc = Xd - mu[y]
    denom = max(1, N - C)
    cov = (Xc.T @ Xc) / float(denom)
    cov = cov + float(reg) * torch.eye(d, dtype=torch.float64)

    L = _safe_cholesky(cov, base_jitter=max(1e-10, float(reg) * 1e-3))
    inv_muT = torch.cholesky_solve(mu.T.contiguous(), L)  # d x C
    quad = (mu * inv_muT.T).sum(dim=1)  # C
    prior = (counts / counts.sum().clamp_min(1.0)).clamp_min(1e-12).log()
    bias = (-0.5 * quad + prior).float()
    weight = inv_muT.T.float()  # C x d
    return weight, bias


def _fit_ridge_ls_classifier(
    X: torch.Tensor,
    y: torch.Tensor,
    num_classes: int,
    alpha: float,
) -> Tuple[torch.Tensor, torch.Tensor]:
    Xd = X.double()
    N, d = Xd.shape
    C = num_classes

    Xaug = torch.cat([Xd, torch.ones((N, 1), dtype=torch.float64)], dim=1)  # N x (d+1)
    D = d + 1

    Y = F.one_hot(y, num_classes=C).double()  # N x C

    A = Xaug.T @ Xaug
    A = A + float(alpha) * torch.eye(D, dtype=torch.float64)
    B = Xaug.T @ Y  # (d+1) x C

    W = torch.linalg.solve(A, B)  # (d+1) x C
    weight = W[:-1, :].T.contiguous().float()  # C x d
    bias = W[-1, :].contiguous().float()  # C
    return weight, bias


class FixedLinear(nn.Module):
    def __init__(self, weight: torch.Tensor, bias: torch.Tensor):
        super().__init__()
        self.register_buffer("weight", weight.contiguous())
        self.register_buffer("bias", bias.contiguous())

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return x.matmul(self.weight.t()) + self.bias


class Standardize(nn.Module):
    def __init__(self, mean: torch.Tensor, std: torch.Tensor):
        super().__init__()
        self.register_buffer("mean", mean.contiguous())
        self.register_buffer("std", std.contiguous())

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return (x - self.mean) / self.std


class KNNClassifier(nn.Module):
    def __init__(self, Xtrain: torch.Tensor, ytrain: torch.Tensor, num_classes: int, k: int = 1):
        super().__init__()
        self.register_buffer("Xtrain", Xtrain.contiguous())
        self.register_buffer("ytrain", ytrain.contiguous())
        self.num_classes = int(num_classes)
        self.k = int(k)
        self.register_buffer("train_norm2", (self.Xtrain * self.Xtrain).sum(dim=1, keepdim=False).contiguous())

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = x.contiguous()
        x_norm2 = (x * x).sum(dim=1, keepdim=True)  # B x 1
        dists = x_norm2 + self.train_norm2.unsqueeze(0) - 2.0 * x.matmul(self.Xtrain.t())
        if self.k <= 1:
            idx = dists.argmin(dim=1)
            pred = self.ytrain[idx]
            logits = torch.full((x.shape[0], self.num_classes), -1e3, device=x.device, dtype=x.dtype)
            logits.scatter_(1, pred.view(-1, 1), 1e3)
            return logits
        else:
            vals, idx = torch.topk(dists, k=self.k, dim=1, largest=False)
            neigh = self.ytrain[idx]  # B x k
            w = 1.0 / (vals.clamp_min(1e-6))
            logits = torch.zeros((x.shape[0], self.num_classes), device=x.device, dtype=x.dtype)
            logits.scatter_add_(1, neigh, w)
            return logits


class ResMLP(nn.Module):
    def __init__(self, input_dim: int, num_classes: int, width: int, nblocks: int = 2, dropout: float = 0.05):
        super().__init__()
        self.stem = nn.Linear(input_dim, width, bias=True)
        self.dropout0 = nn.Dropout(dropout)
        self.blocks = nn.ModuleList()
        for _ in range(nblocks):
            self.blocks.append(nn.LayerNorm(width))
            self.blocks.append(nn.Linear(width, width, bias=True))
            self.blocks.append(nn.Dropout(dropout))
        self.ln_final = nn.LayerNorm(width)
        self.head = nn.Linear(width, num_classes, bias=True)

        self._init_weights()

    def _init_weights(self):
        nn.init.kaiming_uniform_(self.stem.weight, a=math.sqrt(5))
        if self.stem.bias is not None:
            fan_in, _ = nn.init._calculate_fan_in_and_fan_out(self.stem.weight)
            bound = 1 / math.sqrt(fan_in)
            nn.init.uniform_(self.stem.bias, -bound, bound)

        for i in range(0, len(self.blocks), 3):
            lin = self.blocks[i + 1]
            nn.init.kaiming_uniform_(lin.weight, a=math.sqrt(5))
            lin.weight.data.mul_(0.5)
            if lin.bias is not None:
                nn.init.zeros_(lin.bias)

        nn.init.zeros_(self.head.bias)
        nn.init.kaiming_uniform_(self.head.weight, a=math.sqrt(5))

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self.stem(x)
        x = self.dropout0(F.gelu(x))
        for i in range(0, len(self.blocks), 3):
            ln = self.blocks[i]
            lin = self.blocks[i + 1]
            drop = self.blocks[i + 2]
            h = lin(ln(x))
            h = drop(F.gelu(h))
            x = x + h
        x = F.gelu(self.ln_final(x))
        return self.head(x)


class EnsembleModel(nn.Module):
    def __init__(
        self,
        mean: torch.Tensor,
        std: torch.Tensor,
        mlp: Optional[nn.Module],
        fixed_components: List[Tuple[float, nn.Module]],
    ):
        super().__init__()
        self.pre = Standardize(mean, std)
        self.mlp = mlp
        self.fixed = nn.ModuleList([m for _, m in fixed_components])
        weights = torch.tensor([w for w, _ in fixed_components], dtype=torch.float32)
        self.register_buffer("fixed_weights", weights)
        self.register_buffer("use_mlp", torch.tensor(1 if mlp is not None else 0, dtype=torch.uint8))

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self.pre(x)
        out = None
        if self.mlp is not None:
            out = self.mlp(x)
        if len(self.fixed) > 0:
            for i, m in enumerate(self.fixed):
                comp = m(x)
                w = self.fixed_weights[i].to(dtype=comp.dtype, device=comp.device)
                if out is None:
                    out = comp * w
                else:
                    out = out + comp * w
        if out is None:
            out = torch.zeros((x.shape[0], 1), device=x.device, dtype=x.dtype)
        return out


def _train_mlp(
    Xtr: torch.Tensor,
    ytr: torch.Tensor,
    Xval: torch.Tensor,
    yval: torch.Tensor,
    input_dim: int,
    num_classes: int,
    param_limit: int,
    max_epochs: int = 60,
) -> Tuple[Optional[ResMLP], float]:
    device = torch.device("cpu")
    Xtr = Xtr.to(device)
    ytr = ytr.to(device)
    Xval = Xval.to(device)
    yval = yval.to(device)

    def build_with_width(width: int) -> ResMLP:
        return ResMLP(input_dim=input_dim, num_classes=num_classes, width=width, nblocks=2, dropout=0.05)

    lo, hi = 64, 4096
    best_w = lo
    while lo <= hi:
        mid = (lo + hi) // 2
        m = build_with_width(mid)
        pc = _count_trainable_params(m)
        if pc <= param_limit:
            best_w = mid
            lo = mid + 1
        else:
            hi = mid - 1

    width = best_w
    model = build_with_width(width).to(device)
    if _count_trainable_params(model) > param_limit:
        return None, 0.0

    optimizer = torch.optim.AdamW(model.parameters(), lr=3e-3, weight_decay=2e-2)
    max_grad_norm = 1.0

    N = Xtr.shape[0]
    bs = 256 if N >= 256 else N
    label_smooth = 0.02
    mixup_alpha = 0.2
    mixup_prob = 0.5
    input_noise = 0.01

    beta_dist = torch.distributions.Beta(mixup_alpha, mixup_alpha)

    def soft_targets(y: torch.Tensor) -> torch.Tensor:
        oh = F.one_hot(y, num_classes=num_classes).float()
        if label_smooth > 0:
            oh = oh * (1.0 - label_smooth) + (label_smooth / float(num_classes))
        return oh

    best_state = None
    best_acc = -1.0
    patience = 20
    bad = 0
    warmup = 5

    for epoch in range(1, max_epochs + 1):
        model.train()
        if epoch <= warmup:
            lr = 3e-3 * (epoch / float(warmup))
        else:
            t = (epoch - warmup) / float(max(1, max_epochs - warmup))
            lr = 3e-3 * (0.1 + 0.9 * 0.5 * (1.0 + math.cos(math.pi * t)))
        for pg in optimizer.param_groups:
            pg["lr"] = lr

        perm = torch.randperm(N, device=device)
        for i in range(0, N, bs):
            idx = perm[i:i + bs]
            xb = Xtr[idx]
            yb = ytr[idx]

            if input_noise > 0:
                xb = xb + input_noise * torch.randn_like(xb)

            if mixup_alpha > 0 and (torch.rand((), device=device).item() < mixup_prob):
                lam = float(beta_dist.sample(()).item())
                idx2 = idx[torch.randperm(idx.shape[0], device=device)]
                xb2 = Xtr[idx2]
                yb2 = ytr[idx2]
                xb = lam * xb + (1.0 - lam) * xb2
                tb = lam * soft_targets(yb) + (1.0 - lam) * soft_targets(yb2)
            else:
                tb = soft_targets(yb)

            optimizer.zero_grad(set_to_none=True)
            logits = model(xb)
            logp = F.log_softmax(logits, dim=1)
            loss = -(tb * logp).sum(dim=1).mean()
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), max_grad_norm)
            optimizer.step()

        with torch.no_grad():
            model.eval()
            v_logits = model(Xval)
            v_acc = _accuracy_from_logits(v_logits, yval)

        if v_acc > best_acc + 1e-6:
            best_acc = v_acc
            best_state = {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}
            bad = 0
        else:
            bad += 1

        if best_acc >= 0.999:
            break
        if bad >= patience:
            break

    if best_state is not None:
        model.load_state_dict(best_state, strict=True)

    model.eval()
    return model, float(best_acc)


class Solution:
    def solve(self, train_loader, val_loader, metadata: dict = None) -> torch.nn.Module:
        _set_threads()
        _seed_all(0)

        if metadata is None:
            metadata = {}

        device_str = metadata.get("device", "cpu")
        device = torch.device(device_str)

        Xtr_raw, ytr = _collect_xy(train_loader)
        Xval_raw, yval = _collect_xy(val_loader)

        input_dim = int(metadata.get("input_dim", Xtr_raw.shape[1]))
        num_classes = int(metadata.get("num_classes", int(ytr.max().item()) + 1))
        param_limit = int(metadata.get("param_limit", 2_500_000))

        Xtr_raw = Xtr_raw[:, :input_dim].contiguous()
        Xval_raw = Xval_raw[:, :input_dim].contiguous()

        mean = Xtr_raw.mean(dim=0)
        std = Xtr_raw.std(dim=0, unbiased=False).clamp_min(1e-5)

        Xtr = ((Xtr_raw - mean) / std).contiguous()
        Xval = ((Xval_raw - mean) / std).contiguous()

        # Candidate 1: kNN
        knn_candidates = []
        for k in (1, 3, 5):
            knn_model = EnsembleModel(mean, std, mlp=None, fixed_components=[(1.0, KNNClassifier(Xtr, ytr, num_classes=num_classes, k=k))]).to("cpu")
            with torch.no_grad():
                v_logits = _batched_logits(knn_model, Xval_raw, batch_size=512)
                v_acc = _accuracy_from_logits(v_logits, yval)
            knn_candidates.append((v_acc, k, knn_model))

        knn_candidates.sort(key=lambda t: t[0], reverse=True)
        best_knn_acc, best_knn_k, best_knn_model = knn_candidates[0]

        # Candidate 2: LDA grid
        lda_regs = [1e-4, 3e-4, 1e-3, 3e-3, 1e-2, 3e-2, 1e-1, 3e-1, 1.0, 3.0]
        best_lda = None
        best_lda_acc = -1.0
        best_lda_logits_val = None
        for reg in lda_regs:
            try:
                w, b = _fit_shrinkage_lda(Xtr, ytr, num_classes=num_classes, reg=reg)
            except Exception:
                continue
            lda = FixedLinear(w, b)
            with torch.no_grad():
                logits = lda(Xval)
                acc = _accuracy_from_logits(logits, yval)
            if acc > best_lda_acc + 1e-12:
                best_lda_acc = acc
                best_lda = lda
                best_lda_logits_val = logits.detach().cpu()

        # Candidate 3: Ridge LS grid
        ridge_alphas = [1e-4, 3e-4, 1e-3, 3e-3, 1e-2, 3e-2, 1e-1, 3e-1, 1.0, 3.0, 10.0]
        best_ridge = None
        best_ridge_acc = -1.0
        best_ridge_logits_val = None
        for alpha in ridge_alphas:
            try:
                w, b = _fit_ridge_ls_classifier(Xtr, ytr, num_classes=num_classes, alpha=alpha)
            except Exception:
                continue
            ridge = FixedLinear(w, b)
            with torch.no_grad():
                logits = ridge(Xval)
                acc = _accuracy_from_logits(logits, yval)
            if acc > best_ridge_acc + 1e-12:
                best_ridge_acc = acc
                best_ridge = ridge
                best_ridge_logits_val = logits.detach().cpu()

        best_linear_acc = max(best_lda_acc, best_ridge_acc, best_knn_acc)

        # Candidate 4: MLP (train if potentially useful)
        train_mlp_flag = True
        if best_linear_acc >= 0.995:
            train_mlp_flag = False

        mlp_model = None
        mlp_val_acc = 0.0
        mlp_logits_val = None
        if train_mlp_flag:
            mlp_model, mlp_val_acc = _train_mlp(
                Xtr=Xtr,
                ytr=ytr,
                Xval=Xval,
                yval=yval,
                input_dim=input_dim,
                num_classes=num_classes,
                param_limit=param_limit,
                max_epochs=60,
            )
            if mlp_model is not None:
                with torch.no_grad():
                    mlp_logits_val = mlp_model(Xval).detach().cpu()
            else:
                mlp_val_acc = 0.0

        # Select best/ensemble based on val
        best_choice = ("knn", None, best_knn_acc)
        if best_lda_acc > best_choice[2] + 1e-12:
            best_choice = ("lda", None, best_lda_acc)
        if best_ridge_acc > best_choice[2] + 1e-12:
            best_choice = ("ridge", None, best_ridge_acc)
        if mlp_model is not None and mlp_val_acc > best_choice[2] + 1e-12:
            best_choice = ("mlp", None, mlp_val_acc)

        # Try simple ensembles if MLP exists and fixed logits exist
        if mlp_model is not None and mlp_logits_val is not None:
            betas = [0.0, 0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0, 4.0]
            if best_lda is not None and best_lda_logits_val is not None:
                for beta in betas:
                    comb = mlp_logits_val + float(beta) * best_lda_logits_val
                    acc = _accuracy_from_logits(comb, yval)
                    if acc > best_choice[2] + 1e-12:
                        best_choice = ("mlp+lda", beta, acc)
            if best_ridge is not None and best_ridge_logits_val is not None:
                for beta in betas:
                    comb = mlp_logits_val + float(beta) * best_ridge_logits_val
                    acc = _accuracy_from_logits(comb, yval)
                    if acc > best_choice[2] + 1e-12:
                        best_choice = ("mlp+ridge", beta, acc)

        # Also try LDA+Ridge ensemble
        if best_lda is not None and best_ridge is not None and best_lda_logits_val is not None and best_ridge_logits_val is not None:
            gammas = [0.0, 0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0]
            for g in gammas:
                comb = best_lda_logits_val + float(g) * best_ridge_logits_val
                acc = _accuracy_from_logits(comb, yval)
                if acc > best_choice[2] + 1e-12:
                    best_choice = ("lda+ridge", g, acc)

        # Build final model
        kind, scale, _ = best_choice

        fixed_components: List[Tuple[float, nn.Module]] = []
        final_mlp = None

        if kind == "knn":
            final_model = best_knn_model
        elif kind == "lda":
            fixed_components = [(1.0, best_lda)]
            final_model = EnsembleModel(mean, std, mlp=None, fixed_components=fixed_components)
        elif kind == "ridge":
            fixed_components = [(1.0, best_ridge)]
            final_model = EnsembleModel(mean, std, mlp=None, fixed_components=fixed_components)
        elif kind == "mlp":
            final_mlp = mlp_model
            final_model = EnsembleModel(mean, std, mlp=final_mlp, fixed_components=[])
        elif kind == "mlp+lda":
            beta = float(scale)
            final_mlp = mlp_model
            fixed_components = [(beta, best_lda)]
            final_model = EnsembleModel(mean, std, mlp=final_mlp, fixed_components=fixed_components)
        elif kind == "mlp+ridge":
            beta = float(scale)
            final_mlp = mlp_model
            fixed_components = [(beta, best_ridge)]
            final_model = EnsembleModel(mean, std, mlp=final_mlp, fixed_components=fixed_components)
        elif kind == "lda+ridge":
            gamma = float(scale)
            fixed_components = [(1.0, best_lda), (gamma, best_ridge)]
            final_model = EnsembleModel(mean, std, mlp=None, fixed_components=fixed_components)
        else:
            final_model = best_knn_model

        final_model = final_model.to(device)
        final_model.eval()

        if _count_trainable_params(final_model) > param_limit:
            # Safety fallback: choose best fixed model only (0 trainable params)
            if best_knn_acc >= max(best_lda_acc, best_ridge_acc):
                final_model = best_knn_model.to(device).eval()
            elif best_lda_acc >= best_ridge_acc and best_lda is not None:
                final_model = EnsembleModel(mean, std, mlp=None, fixed_components=[(1.0, best_lda)]).to(device).eval()
            elif best_ridge is not None:
                final_model = EnsembleModel(mean, std, mlp=None, fixed_components=[(1.0, best_ridge)]).to(device).eval()
            else:
                final_model = best_knn_model.to(device).eval()

        return final_model