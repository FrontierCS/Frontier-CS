import os
import math
import time
import random
from typing import Optional, Tuple, List, Dict

import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import TensorDataset, DataLoader


def _set_torch_threads(max_threads: int = 8) -> None:
    try:
        n = os.cpu_count() or max_threads
        n = max(1, min(int(n), int(max_threads)))
        torch.set_num_threads(n)
        torch.set_num_interop_threads(max(1, min(2, n)))
    except Exception:
        pass


def _seed_all(seed: int = 42) -> None:
    random.seed(seed)
    torch.manual_seed(seed)


def _count_trainable_params(model: nn.Module) -> int:
    return sum(p.numel() for p in model.parameters() if p.requires_grad)


@torch.no_grad()
def _accuracy(model: nn.Module, loader: DataLoader, device: torch.device) -> float:
    model.eval()
    correct = 0
    total = 0
    for xb, yb in loader:
        xb = xb.to(device=device, dtype=torch.float32, non_blocking=False)
        yb = yb.to(device=device, dtype=torch.long, non_blocking=False)
        logits = model(xb)
        pred = logits.argmax(dim=1)
        correct += (pred == yb).sum().item()
        total += yb.numel()
    return correct / max(1, total)


def _ce_label_smooth(logits: torch.Tensor, targets: torch.Tensor, smoothing: float) -> torch.Tensor:
    if smoothing <= 0.0:
        return F.cross_entropy(logits, targets)
    log_probs = F.log_softmax(logits, dim=1)
    nll = -log_probs.gather(1, targets.unsqueeze(1)).squeeze(1)
    smooth = -log_probs.mean(dim=1)
    loss = (1.0 - smoothing) * nll + smoothing * smooth
    return loss.mean()


class _Standardize(nn.Module):
    def __init__(self, mean: torch.Tensor, std: torch.Tensor):
        super().__init__()
        self.register_buffer("mean", mean.detach().clone().to(dtype=torch.float32))
        self.register_buffer("std", std.detach().clone().to(dtype=torch.float32))

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = x.to(dtype=torch.float32)
        return (x - self.mean) / self.std


class _LDACore(nn.Module):
    def __init__(self, W: torch.Tensor, b: torch.Tensor):
        super().__init__()
        self.register_buffer("W", W.detach().clone().to(dtype=torch.float32))  # (D, K)
        self.register_buffer("b", b.detach().clone().to(dtype=torch.float32))  # (K,)

    def forward(self, x_std: torch.Tensor) -> torch.Tensor:
        return x_std.matmul(self.W) + self.b


class _ResidualMLPCore(nn.Module):
    def __init__(self, input_dim: int, num_classes: int, hidden: int, dropout: float):
        super().__init__()
        self.ln0 = nn.LayerNorm(input_dim)
        self.fc1 = nn.Linear(input_dim, hidden, bias=True)

        self.ln1 = nn.LayerNorm(hidden)
        self.fc2 = nn.Linear(hidden, hidden, bias=True)

        self.ln2 = nn.LayerNorm(hidden)
        self.fc3 = nn.Linear(hidden, hidden, bias=True)

        self.ln3 = nn.LayerNorm(hidden)
        self.fc4 = nn.Linear(hidden, num_classes, bias=True)

        self.act = nn.GELU()
        self.drop = nn.Dropout(dropout)

        self.alpha2 = nn.Parameter(torch.tensor(0.10, dtype=torch.float32))
        self.alpha3 = nn.Parameter(torch.tensor(0.10, dtype=torch.float32))
        self.logit_scale = nn.Parameter(torch.tensor(1.0, dtype=torch.float32))

        self._init()

    def _init(self) -> None:
        for m in self.modules():
            if isinstance(m, nn.Linear):
                nn.init.trunc_normal_(m.weight, std=0.02)
                if m.bias is not None:
                    nn.init.zeros_(m.bias)

    def forward(self, x_std: torch.Tensor) -> torch.Tensor:
        x = self.ln0(x_std)
        h = self.act(self.fc1(x))
        h = self.drop(h)

        r2 = self.act(self.fc2(self.ln1(h)))
        h = h + self.alpha2 * self.drop(r2)

        r3 = self.act(self.fc3(self.ln2(h)))
        h = h + self.alpha3 * self.drop(r3)

        h = self.ln3(h)
        logits = self.fc4(h) * self.logit_scale
        return logits


class _PreprocessAndCore(nn.Module):
    def __init__(self, pre: _Standardize, core: nn.Module):
        super().__init__()
        self.pre = pre
        self.core = core

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self.pre(x)
        return self.core(x)


class _Ensemble(nn.Module):
    def __init__(self, pre: _Standardize, mlp_core: Optional[nn.Module], lda_core: Optional[nn.Module],
                 alpha_mlp: float, alpha_lda: float):
        super().__init__()
        self.pre = pre
        self.mlp_core = mlp_core
        self.lda_core = lda_core
        self.register_buffer("alpha_mlp", torch.tensor(float(alpha_mlp), dtype=torch.float32))
        self.register_buffer("alpha_lda", torch.tensor(float(alpha_lda), dtype=torch.float32))

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self.pre(x)
        out = None
        if self.mlp_core is not None and float(self.alpha_mlp.item()) != 0.0:
            out = self.mlp_core(x) * self.alpha_mlp
        if self.lda_core is not None and float(self.alpha_lda.item()) != 0.0:
            o2 = self.lda_core(x) * self.alpha_lda
            out = o2 if out is None else (out + o2)
        if out is None:
            if self.lda_core is not None:
                return self.lda_core(x)
            if self.mlp_core is not None:
                return self.mlp_core(x)
            raise RuntimeError("Empty ensemble.")
        return out


def _collect_tensors(loader) -> Tuple[torch.Tensor, torch.Tensor]:
    xs = []
    ys = []
    for xb, yb in loader:
        xs.append(xb.detach().cpu())
        ys.append(yb.detach().cpu())
    X = torch.cat(xs, dim=0)
    y = torch.cat(ys, dim=0)
    return X, y


def _fit_lda_from_standardized(Xs: torch.Tensor, y: torch.Tensor, num_classes: int, shrink: float) -> Optional[Tuple[torch.Tensor, torch.Tensor]]:
    Xs = Xs.to(dtype=torch.float32)
    y = y.to(dtype=torch.long)
    N, D = Xs.shape
    K = int(num_classes)

    counts = torch.bincount(y, minlength=K).to(dtype=torch.float32).clamp_min_(1.0).unsqueeze(1)  # (K,1)
    mus = torch.zeros((K, D), dtype=torch.float32)
    mus.index_add_(0, y, Xs)
    mus = mus / counts

    Z = Xs - mus[y]
    denom = float(max(1, N - K))
    Sigma = (Z.t().matmul(Z)) / denom
    tr = Sigma.diag().mean()
    Sigma = (1.0 - float(shrink)) * Sigma + float(shrink) * (tr * torch.eye(D, dtype=torch.float32))

    eye = torch.eye(D, dtype=torch.float32)
    for jitter in (0.0, 1e-6, 1e-5, 1e-4, 1e-3):
        try:
            Sig = Sigma if jitter == 0.0 else (Sigma + (float(jitter) * tr) * eye)
            inv = torch.linalg.inv(Sig)
            W = inv.matmul(mus.t())  # (D,K)
            quad = (mus * (inv.matmul(mus.t()).t())).sum(dim=1)  # (K,)
            b = -0.5 * quad
            return W, b
        except Exception:
            continue
    return None


@torch.no_grad()
def _tune_ensemble_weights(mlp_model: Optional[nn.Module], lda_model: Optional[nn.Module], val_loader: DataLoader,
                          device: torch.device) -> Tuple[float, float, float]:
    mlp_logits_list = []
    lda_logits_list = []
    y_list = []
    for xb, yb in val_loader:
        xb = xb.to(device=device, dtype=torch.float32)
        yb = yb.to(device=device, dtype=torch.long)
        y_list.append(yb)
        if mlp_model is not None:
            mlp_logits_list.append(mlp_model(xb))
        if lda_model is not None:
            lda_logits_list.append(lda_model(xb))
    y = torch.cat(y_list, dim=0)
    mlp_logits = torch.cat(mlp_logits_list, dim=0) if mlp_model is not None else None
    lda_logits = torch.cat(lda_logits_list, dim=0) if lda_model is not None else None

    best_acc = -1.0
    best_am = 0.0 if mlp_model is None else 1.0
    best_al = 0.0 if lda_model is None else 1.0

    if mlp_logits is None and lda_logits is None:
        return 0.0, 0.0, 0.0

    mlp_scales = [0.0] if mlp_logits is None else [0.5, 1.0, 1.5]
    lda_scales = [0.0] if lda_logits is None else [0.0, 0.25, 0.5, 0.75, 1.0, 1.25, 1.5, 2.0]

    for am in mlp_scales:
        for al in lda_scales:
            if (mlp_logits is None and al == 0.0) or (lda_logits is None and am == 0.0) or (mlp_logits is not None and lda_logits is not None and am == 0.0 and al == 0.0):
                continue
            logits = None
            if mlp_logits is not None and am != 0.0:
                logits = mlp_logits * float(am)
            if lda_logits is not None and al != 0.0:
                logits2 = lda_logits * float(al)
                logits = logits2 if logits is None else (logits + logits2)
            pred = logits.argmax(dim=1)
            acc = (pred == y).float().mean().item()
            if acc > best_acc:
                best_acc = acc
                best_am, best_al = float(am), float(al)

    return best_am, best_al, best_acc


class Solution:
    def solve(self, train_loader, val_loader, metadata: dict = None) -> torch.nn.Module:
        _set_torch_threads(8)
        _seed_all(42)

        if metadata is None:
            metadata = {}
        input_dim = int(metadata.get("input_dim", 384))
        num_classes = int(metadata.get("num_classes", 128))
        param_limit = int(metadata.get("param_limit", 5_000_000))
        device = torch.device(metadata.get("device", "cpu"))

        Xtr, ytr = _collect_tensors(train_loader)
        Xva, yva = _collect_tensors(val_loader)

        if Xtr.ndim != 2 or Xtr.shape[1] != input_dim:
            Xtr = Xtr.view(Xtr.shape[0], -1)
        if Xva.ndim != 2 or Xva.shape[1] != input_dim:
            Xva = Xva.view(Xva.shape[0], -1)

        Xtr = Xtr.to(dtype=torch.float32)
        Xva = Xva.to(dtype=torch.float32)
        ytr = ytr.to(dtype=torch.long)
        yva = yva.to(dtype=torch.long)

        mean = Xtr.mean(dim=0)
        std = Xtr.std(dim=0, unbiased=False).clamp_min_(1e-6)

        pre = _Standardize(mean, std)

        Xtr_std = (Xtr - mean) / std
        Xva_std = (Xva - mean) / std

        lda_best = None
        lda_best_acc = -1.0
        lda_best_shrink = None
        for shrink in (0.0, 0.02, 0.05, 0.10, 0.20, 0.30, 0.40):
            fitted = _fit_lda_from_standardized(Xtr_std, ytr, num_classes, shrink)
            if fitted is None:
                continue
            W, b = fitted
            lda_core = _LDACore(W, b)
            lda_model = _PreprocessAndCore(pre, lda_core).to(device)
            val_ds_tmp = TensorDataset(Xva, yva)
            val_loader_tmp = DataLoader(val_ds_tmp, batch_size=min(512, len(val_ds_tmp)), shuffle=False, num_workers=0)
            acc = _accuracy(lda_model, val_loader_tmp, device)
            if acc > lda_best_acc:
                lda_best_acc = acc
                lda_best = lda_model
                lda_best_shrink = shrink

        train_ds = TensorDataset(Xtr, ytr)
        val_ds = TensorDataset(Xva, yva)
        batch_size = int(min(256, len(train_ds)))
        if batch_size <= 0:
            batch_size = 32
        train_loader2 = DataLoader(train_ds, batch_size=batch_size, shuffle=True, num_workers=0)
        val_loader2 = DataLoader(val_ds, batch_size=min(512, len(val_ds)), shuffle=False, num_workers=0)

        hidden = 1456
        dropout = 0.10
        mlp_core = None
        while hidden >= 512:
            core = _ResidualMLPCore(input_dim=input_dim, num_classes=num_classes, hidden=hidden, dropout=dropout)
            tmp = _PreprocessAndCore(pre, core)
            if _count_trainable_params(tmp) <= param_limit:
                mlp_core = core
                break
            hidden -= 8

        mlp_model = None
        best_mlp_val_acc = -1.0
        if mlp_core is not None:
            mlp_model = _PreprocessAndCore(pre, mlp_core).to(device)
            if _count_trainable_params(mlp_model) > param_limit:
                mlp_model = None

        if mlp_model is not None:
            max_epochs = 250
            base_lr = 2.0e-3
            weight_decay = 1.0e-2
            label_smoothing = 0.10
            mixup_alpha = 0.20
            input_noise = 0.01
            grad_clip = 1.0
            patience = 40
            min_epochs = 30

            opt = torch.optim.AdamW(mlp_model.parameters(), lr=base_lr, weight_decay=weight_decay, betas=(0.9, 0.99))
            total_steps = max_epochs * max(1, len(train_loader2))
            warmup_steps = max(1, int(0.10 * total_steps))

            def lr_at(step: int) -> float:
                if step < warmup_steps:
                    return base_lr * (step + 1) / warmup_steps
                t = (step - warmup_steps) / max(1, (total_steps - warmup_steps))
                return base_lr * (0.5 * (1.0 + math.cos(math.pi * t)))

            best_state = None
            best_epoch = -1
            step = 0

            for epoch in range(max_epochs):
                mlp_model.train()
                for xb, yb in train_loader2:
                    xb = xb.to(device=device, dtype=torch.float32)
                    yb = yb.to(device=device, dtype=torch.long)
                    if input_noise > 0.0:
                        xb = xb + input_noise * torch.randn_like(xb)

                    if mixup_alpha > 0.0:
                        lam = float(torch.distributions.Beta(mixup_alpha, mixup_alpha).sample().item())
                        perm = torch.randperm(xb.shape[0], device=device)
                        xb2 = xb[perm]
                        yb2 = yb[perm]
                        xb_mix = xb * lam + xb2 * (1.0 - lam)
                        logits = mlp_model(xb_mix)
                        loss = lam * _ce_label_smooth(logits, yb, label_smoothing) + (1.0 - lam) * _ce_label_smooth(logits, yb2, label_smoothing)
                    else:
                        logits = mlp_model(xb)
                        loss = _ce_label_smooth(logits, yb, label_smoothing)

                    opt.zero_grad(set_to_none=True)
                    loss.backward()
                    if grad_clip is not None and grad_clip > 0:
                        torch.nn.utils.clip_grad_norm_(mlp_model.parameters(), grad_clip)
                    lr = lr_at(step)
                    for pg in opt.param_groups:
                        pg["lr"] = lr
                    opt.step()
                    step += 1

                if epoch % 2 == 0 or epoch == max_epochs - 1:
                    acc = _accuracy(mlp_model, val_loader2, device)
                    if acc > best_mlp_val_acc + 1e-5:
                        best_mlp_val_acc = acc
                        best_epoch = epoch
                        best_state = {k: v.detach().cpu().clone() for k, v in mlp_model.state_dict().items()}

                if epoch >= min_epochs and best_epoch >= 0 and (epoch - best_epoch) >= patience:
                    break

            if best_state is not None:
                mlp_model.load_state_dict(best_state, strict=True)

        if lda_best is None and mlp_model is None:
            fallback = nn.Linear(input_dim, num_classes, bias=True).to(device)
            fallback.eval()
            return fallback

        am, al, best_ens = _tune_ensemble_weights(mlp_model, lda_best, val_loader2, device)

        if mlp_model is None:
            model = lda_best
        elif lda_best is None:
            model = mlp_model
        else:
            pre2 = _Standardize(mean, std).to(device)
            mlp_core2 = mlp_model.core if isinstance(mlp_model, _PreprocessAndCore) else None
            lda_core2 = lda_best.core if isinstance(lda_best, _PreprocessAndCore) else None
            model = _Ensemble(pre2, mlp_core2, lda_core2, alpha_mlp=am, alpha_lda=al).to(device)

        if _count_trainable_params(model) > param_limit:
            if lda_best is not None:
                lda_best.eval()
                return lda_best
            model.eval()
            return model

        model.eval()
        return model
