import math
import random
from typing import List, Tuple, Optional, Dict

import torch
import torch.nn as nn
import torch.nn.functional as F


def _flatten_inputs(x: torch.Tensor) -> torch.Tensor:
    if x.dim() > 2:
        return x.view(x.size(0), -1)
    return x


@torch.no_grad()
def _collect_loader(loader, input_dim: int, device: str = "cpu") -> Tuple[torch.Tensor, torch.Tensor]:
    xs = []
    ys = []
    for xb, yb in loader:
        xb = _flatten_inputs(xb).to(device=device, dtype=torch.float32)
        if xb.size(1) != input_dim:
            xb = xb[:, :input_dim].contiguous()
        yb = yb.to(device=device, dtype=torch.long)
        xs.append(xb.cpu())
        ys.append(yb.cpu())
    x = torch.cat(xs, dim=0)
    y = torch.cat(ys, dim=0)
    return x, y


def _standardize_fit(x: torch.Tensor, eps: float = 1e-6) -> Tuple[torch.Tensor, torch.Tensor]:
    mean = x.mean(dim=0)
    var = x.var(dim=0, unbiased=False)
    inv_std = torch.rsqrt(var + eps)
    return mean, inv_std


def _standardize_apply(x: torch.Tensor, mean: torch.Tensor, inv_std: torch.Tensor) -> torch.Tensor:
    return (x - mean) * inv_std


def _class_means(x: torch.Tensor, y: torch.Tensor, num_classes: int) -> Tuple[torch.Tensor, torch.Tensor]:
    d = x.size(1)
    sums = torch.zeros(num_classes, d, dtype=x.dtype, device=x.device)
    sums.index_add_(0, y, x)
    counts = torch.bincount(y, minlength=num_classes).to(dtype=x.dtype, device=x.device).clamp_min(1.0)
    means = sums / counts.unsqueeze(1)
    return means, counts


def _accuracy_from_logits(logits: torch.Tensor, y: torch.Tensor) -> float:
    pred = logits.argmax(dim=1)
    return (pred == y).to(torch.float32).mean().item()


class FixedLinearModel(nn.Module):
    def __init__(self, mean: torch.Tensor, inv_std: torch.Tensor, weight: torch.Tensor, bias: torch.Tensor):
        super().__init__()
        self.register_buffer("mean", mean.clone().detach().to(torch.float32))
        self.register_buffer("inv_std", inv_std.clone().detach().to(torch.float32))
        self.register_buffer("weight", weight.clone().detach().to(torch.float32))
        self.register_buffer("bias", bias.clone().detach().to(torch.float32))

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = _flatten_inputs(x).to(dtype=torch.float32)
        x = (x - self.mean) * self.inv_std
        return F.linear(x, self.weight, self.bias)


class RandomFeatureLinearModel(nn.Module):
    def __init__(
        self,
        mean: torch.Tensor,
        inv_std: torch.Tensor,
        rf_weight: torch.Tensor,
        rf_bias: torch.Tensor,
        act: str,
        out_weight: torch.Tensor,
        out_bias: torch.Tensor,
        l2_normalize_features: bool = False,
        logit_scale: float = 1.0,
    ):
        super().__init__()
        self.register_buffer("mean", mean.clone().detach().to(torch.float32))
        self.register_buffer("inv_std", inv_std.clone().detach().to(torch.float32))
        self.register_buffer("rf_weight", rf_weight.clone().detach().to(torch.float32))  # (m, d)
        self.register_buffer("rf_bias", rf_bias.clone().detach().to(torch.float32))      # (m,)
        self.register_buffer("out_weight", out_weight.clone().detach().to(torch.float32))  # (C, m)
        self.register_buffer("out_bias", out_bias.clone().detach().to(torch.float32))      # (C,)
        self.act = act
        self.l2_normalize_features = l2_normalize_features
        self.register_buffer("logit_scale", torch.tensor(float(logit_scale), dtype=torch.float32))

    def _activate(self, z: torch.Tensor) -> torch.Tensor:
        if self.act == "relu":
            return F.relu(z)
        if self.act == "gelu":
            return F.gelu(z)
        if self.act == "tanh":
            return torch.tanh(z)
        if self.act == "cos":
            return torch.cos(z)
        return z

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = _flatten_inputs(x).to(dtype=torch.float32)
        x = (x - self.mean) * self.inv_std
        z = F.linear(x, self.rf_weight, self.rf_bias)
        z = self._activate(z)
        if self.l2_normalize_features:
            z = z / (z.norm(dim=1, keepdim=True) + 1e-6)
        logits = F.linear(z, self.out_weight, self.out_bias)
        return logits * self.logit_scale


class WeightedEnsemble(nn.Module):
    def __init__(self, models: List[nn.Module], weights: List[float]):
        super().__init__()
        self.models = nn.ModuleList(models)
        w = torch.tensor(weights, dtype=torch.float32)
        self.register_buffer("weights", w)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        out = None
        for i, m in enumerate(self.models):
            y = m(x) * self.weights[i]
            out = y if out is None else (out + y)
        return out


def _fit_lda_full(
    x: torch.Tensor,
    y: torch.Tensor,
    num_classes: int,
    shrink_rel: float,
) -> Tuple[torch.Tensor, torch.Tensor]:
    x64 = x.to(torch.float64)
    y64 = y.to(torch.long)

    means, counts = _class_means(x64, y64, num_classes)  # (C, d)
    x_centered = x64 - means[y64]
    n = x64.size(0)
    cov = (x_centered.t() @ x_centered) / max(1, (n - 1))
    scale = cov.diag().mean().clamp_min(1e-12)
    alpha = float(shrink_rel) * float(scale.item())
    cov_reg = cov + torch.eye(cov.size(0), dtype=torch.float64, device=cov.device) * alpha

    chol = torch.linalg.cholesky(cov_reg)
    inv_cov_mu = torch.cholesky_solve(means.t(), chol)  # (d, C)
    w = inv_cov_mu.t().to(torch.float32)  # (C, d)
    b = (-0.5 * (means * inv_cov_mu.t()).sum(dim=1)).to(torch.float32)  # (C,)
    return w, b


def _fit_diag_shared(
    x: torch.Tensor,
    y: torch.Tensor,
    num_classes: int,
    shrink_rel: float,
) -> Tuple[torch.Tensor, torch.Tensor]:
    x64 = x.to(torch.float64)
    y64 = y.to(torch.long)
    means, _ = _class_means(x64, y64, num_classes)
    x_centered = x64 - means[y64]
    var = (x_centered * x_centered).mean(dim=0).clamp_min(1e-12)
    scale = var.mean().clamp_min(1e-12)
    alpha = float(shrink_rel) * float(scale.item())
    denom = (var + alpha).to(torch.float32)  # (d,)
    means32 = means.to(torch.float32)
    w = means32 / denom.unsqueeze(0)
    b = (-0.5 * (means32 * means32 / denom.unsqueeze(0)).sum(dim=1))
    return w, b


def _fit_centroid(
    x: torch.Tensor,
    y: torch.Tensor,
    num_classes: int,
) -> Tuple[torch.Tensor, torch.Tensor]:
    means, _ = _class_means(x, y, num_classes)
    w = means.to(torch.float32)
    b = (-0.5 * (w * w).sum(dim=1))
    return w, b


def _make_random_matrix(m: int, d: int, seed: int, kind: str, gamma: float = 1.0) -> Tuple[torch.Tensor, torch.Tensor]:
    g = torch.Generator(device="cpu")
    g.manual_seed(seed)
    if kind == "cos":
        w = torch.randn(m, d, generator=g, dtype=torch.float32) * (gamma / math.sqrt(d))
        b = torch.rand(m, generator=g, dtype=torch.float32) * (2.0 * math.pi)
        return w, b
    w = torch.randn(m, d, generator=g, dtype=torch.float32) * (gamma / math.sqrt(d))
    b = torch.randn(m, generator=g, dtype=torch.float32) * 0.1
    return w, b


def _rf_transform(
    x: torch.Tensor,
    rf_w: torch.Tensor,
    rf_b: torch.Tensor,
    act: str,
    l2_normalize_features: bool = False,
) -> torch.Tensor:
    z = F.linear(x, rf_w, rf_b)
    if act == "relu":
        z = F.relu(z)
    elif act == "gelu":
        z = F.gelu(z)
    elif act == "tanh":
        z = torch.tanh(z)
    elif act == "cos":
        z = torch.cos(z)
    if l2_normalize_features:
        z = z / (z.norm(dim=1, keepdim=True) + 1e-6)
    return z


def _fit_rf_centroid(
    z: torch.Tensor,
    y: torch.Tensor,
    num_classes: int,
) -> Tuple[torch.Tensor, torch.Tensor]:
    means, _ = _class_means(z, y, num_classes)
    w = means.to(torch.float32)
    b = (-0.5 * (w * w).sum(dim=1))
    return w, b


def _fit_rf_diag_shared(
    z: torch.Tensor,
    y: torch.Tensor,
    num_classes: int,
    shrink_rel: float,
) -> Tuple[torch.Tensor, torch.Tensor]:
    z64 = z.to(torch.float64)
    y64 = y.to(torch.long)
    means, _ = _class_means(z64, y64, num_classes)
    z_centered = z64 - means[y64]
    var = (z_centered * z_centered).mean(dim=0).clamp_min(1e-12)
    scale = var.mean().clamp_min(1e-12)
    alpha = float(shrink_rel) * float(scale.item())
    denom = (var + alpha).to(torch.float32)
    means32 = means.to(torch.float32)
    w = means32 / denom.unsqueeze(0)
    b = (-0.5 * (means32 * means32 / denom.unsqueeze(0)).sum(dim=1))
    return w, b


class Solution:
    def solve(self, train_loader, val_loader, metadata: dict = None) -> torch.nn.Module:
        if metadata is None:
            metadata = {}
        input_dim = int(metadata.get("input_dim", 384))
        num_classes = int(metadata.get("num_classes", 128))
        device = str(metadata.get("device", "cpu"))

        torch.set_num_threads(max(1, int(torch.get_num_threads())))
        torch.manual_seed(0)
        random.seed(0)

        x_train, y_train = _collect_loader(train_loader, input_dim=input_dim, device=device)
        x_val, y_val = _collect_loader(val_loader, input_dim=input_dim, device=device)

        mean_std, inv_std_std = _standardize_fit(x_train)
        mean_raw = torch.zeros_like(mean_std)
        inv_std_raw = torch.ones_like(inv_std_std)

        candidates: List[Tuple[str, nn.Module, float, torch.Tensor]] = []

        def eval_and_add(name: str, model: nn.Module):
            model.eval()
            with torch.no_grad():
                logits = model(x_val)
                acc = _accuracy_from_logits(logits, y_val)
            candidates.append((name, model, acc, logits))

        # Input-space candidates (raw)
        for shrink in [0.0, 1e-4, 3e-4, 1e-3, 3e-3, 1e-2, 3e-2, 1e-1, 3e-1, 1.0]:
            try:
                w, b = _fit_lda_full(x_train, y_train, num_classes=num_classes, shrink_rel=shrink)
                m = FixedLinearModel(mean_raw, inv_std_raw, w, b)
                eval_and_add(f"lda_raw_{shrink:g}", m)
            except Exception:
                pass

        for shrink in [0.0, 1e-4, 1e-3, 1e-2, 1e-1, 1.0]:
            try:
                w, b = _fit_diag_shared(x_train, y_train, num_classes=num_classes, shrink_rel=shrink)
                m = FixedLinearModel(mean_raw, inv_std_raw, w, b)
                eval_and_add(f"diag_raw_{shrink:g}", m)
            except Exception:
                pass

        try:
            w, b = _fit_centroid(x_train, y_train, num_classes=num_classes)
            m = FixedLinearModel(mean_raw, inv_std_raw, w, b)
            eval_and_add("centroid_raw", m)
        except Exception:
            pass

        # Input-space candidates (standardized)
        x_train_s = _standardize_apply(x_train, mean_std, inv_std_std)
        for shrink in [0.0, 1e-4, 3e-4, 1e-3, 3e-3, 1e-2, 3e-2, 1e-1, 3e-1, 1.0]:
            try:
                w, b = _fit_lda_full(x_train_s, y_train, num_classes=num_classes, shrink_rel=shrink)
                m = FixedLinearModel(mean_std, inv_std_std, w, b)
                eval_and_add(f"lda_std_{shrink:g}", m)
            except Exception:
                pass

        for shrink in [0.0, 1e-4, 1e-3, 1e-2, 1e-1, 1.0]:
            try:
                w, b = _fit_diag_shared(x_train_s, y_train, num_classes=num_classes, shrink_rel=shrink)
                m = FixedLinearModel(mean_std, inv_std_std, w, b)
                eval_and_add(f"diag_std_{shrink:g}", m)
            except Exception:
                pass

        try:
            w, b = _fit_centroid(x_train_s, y_train, num_classes=num_classes)
            m = FixedLinearModel(mean_std, inv_std_std, w, b)
            eval_and_add("centroid_std", m)
        except Exception:
            pass

        # Random feature candidates (standardized input in-model)
        rf_specs = [
            ("relu", 1024, 11, 1.0, False),
            ("relu", 2048, 12, 1.0, False),
            ("gelu", 2048, 13, 1.0, False),
            ("cos", 2048, 14, 1.0, False),
        ]

        for act, mdim, seed, gamma, l2norm in rf_specs:
            try:
                rf_w, rf_b = _make_random_matrix(mdim, input_dim, seed=seed, kind=act, gamma=gamma)
                z_train = _rf_transform(x_train_s, rf_w, rf_b, act=act, l2_normalize_features=l2norm)
                w_cent, b_cent = _fit_rf_centroid(z_train, y_train, num_classes=num_classes)
                model_cent = RandomFeatureLinearModel(
                    mean=mean_std,
                    inv_std=inv_std_std,
                    rf_weight=rf_w,
                    rf_bias=rf_b,
                    act=act,
                    out_weight=w_cent,
                    out_bias=b_cent,
                    l2_normalize_features=l2norm,
                    logit_scale=1.0,
                )
                eval_and_add(f"rf_cent_{act}_{mdim}", model_cent)

                for shrink in [0.0, 1e-4, 1e-3, 1e-2, 1e-1]:
                    w_d, b_d = _fit_rf_diag_shared(z_train, y_train, num_classes=num_classes, shrink_rel=shrink)
                    model_d = RandomFeatureLinearModel(
                        mean=mean_std,
                        inv_std=inv_std_std,
                        rf_weight=rf_w,
                        rf_bias=rf_b,
                        act=act,
                        out_weight=w_d,
                        out_bias=b_d,
                        l2_normalize_features=l2norm,
                        logit_scale=1.0,
                    )
                    eval_and_add(f"rf_diag_{act}_{mdim}_{shrink:g}", model_d)
            except Exception:
                pass

        # Ensemble among best few
        if not candidates:
            # As a last resort, return a simple centroid classifier in standardized space
            w, b = _fit_centroid(x_train_s, y_train, num_classes=num_classes)
            model = FixedLinearModel(mean_std, inv_std_std, w, b).to(device)
            model.eval()
            return model

        candidates.sort(key=lambda t: t[2], reverse=True)
        best_name, best_model, best_acc, best_logits = candidates[0]

        top_k = min(5, len(candidates))
        top = candidates[:top_k]

        best_ens_model = None
        best_ens_acc = best_acc

        # Prepare per-model scaling based on val logits std to stabilize logit magnitudes
        scales = []
        for _, _, _, lg in top:
            s = float(lg.std().item())
            scales.append(1.0 / (s + 1e-6))

        # Pair ensembles
        for i in range(top_k):
            for j in range(i + 1, top_k):
                li = top[i][3]
                lj = top[j][3]
                wi = scales[i]
                wj = scales[j]
                logits_sum = li * wi + lj * wj
                acc = _accuracy_from_logits(logits_sum, y_val)
                if acc > best_ens_acc:
                    best_ens_acc = acc
                    best_ens_model = WeightedEnsemble([top[i][1], top[j][1]], [wi, wj])

        # Triple ensembles
        for i in range(top_k):
            for j in range(i + 1, top_k):
                for k in range(j + 1, top_k):
                    li = top[i][3]
                    lj = top[j][3]
                    lk = top[k][3]
                    wi = scales[i]
                    wj = scales[j]
                    wk = scales[k]
                    logits_sum = li * wi + lj * wj + lk * wk
                    acc = _accuracy_from_logits(logits_sum, y_val)
                    if acc > best_ens_acc:
                        best_ens_acc = acc
                        best_ens_model = WeightedEnsemble([top[i][1], top[j][1], top[k][1]], [wi, wj, wk])

        final_model = best_model if best_ens_model is None else best_ens_model
        final_model = final_model.to(device)
        final_model.eval()
        return final_model