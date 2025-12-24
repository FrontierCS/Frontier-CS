import os
import math
import time
import torch
import torch.nn as nn


class _NormalizedLinear(nn.Module):
    def __init__(self, mean, std, weight, bias):
        super().__init__()
        self.register_buffer("mean", mean.detach().clone())
        self.register_buffer("inv_std", (1.0 / std.detach().clone()))
        self.register_buffer("weight", weight.detach().clone())
        self.register_buffer("bias", bias.detach().clone())

    def forward(self, x):
        x = (x - self.mean) * self.inv_std
        return x.matmul(self.weight) + self.bias


class _RFFModel(nn.Module):
    def __init__(self, mean, std, proj_w, proj_b, out_w, out_b, scale):
        super().__init__()
        self.register_buffer("mean", mean.detach().clone())
        self.register_buffer("inv_std", (1.0 / std.detach().clone()))
        self.register_buffer("proj_w", proj_w.detach().clone())
        self.register_buffer("proj_b", proj_b.detach().clone())
        self.register_buffer("out_w", out_w.detach().clone())
        self.register_buffer("out_b", out_b.detach().clone())
        self.register_buffer("scale", torch.tensor(float(scale), dtype=torch.float32))

    def forward(self, x):
        x = (x - self.mean) * self.inv_std
        z = x.matmul(self.proj_w) + self.proj_b
        z = torch.cos(z) * self.scale
        return z.matmul(self.out_w) + self.out_b


class _Ensemble(nn.Module):
    def __init__(self, models):
        super().__init__()
        self.models = nn.ModuleList(models)

    def forward(self, x):
        out = None
        for m in self.models:
            y = m(x)
            if out is None:
                out = y
            else:
                out = out + y
        return out / float(len(self.models))


def _collect_xy(loader, input_dim=None):
    xs = []
    ys = []
    for batch in loader:
        if isinstance(batch, (list, tuple)):
            x = batch[0]
            y = batch[1]
        else:
            x, y = batch
        if not torch.is_tensor(x):
            x = torch.as_tensor(x)
        if not torch.is_tensor(y):
            y = torch.as_tensor(y)
        x = x.detach().cpu()
        y = y.detach().cpu()
        if x.dtype != torch.float32:
            x = x.float()
        y = y.long()
        if x.dim() > 2:
            x = x.view(x.size(0), -1)
        if input_dim is not None and x.size(1) != input_dim:
            x = x.view(x.size(0), input_dim)
        xs.append(x)
        ys.append(y)
    if not xs:
        return torch.empty(0, input_dim or 0, dtype=torch.float32), torch.empty(0, dtype=torch.long)
    return torch.cat(xs, dim=0), torch.cat(ys, dim=0)


@torch.no_grad()
def _accuracy(model, x, y, batch_size=2048):
    model.eval()
    n = y.numel()
    correct = 0
    for i in range(0, n, batch_size):
        xb = x[i:i + batch_size]
        yb = y[i:i + batch_size]
        logits = model(xb)
        pred = logits.argmax(dim=1)
        correct += (pred == yb).sum().item()
    return correct / max(1, n)


def _make_onehot(y, num_classes, dtype=torch.float32):
    n = y.numel()
    oh = torch.zeros(n, num_classes, dtype=dtype)
    oh.scatter_(1, y.view(-1, 1), 1.0)
    return oh


def _fit_centroid(x, y, num_classes):
    n, d = x.shape
    mu = torch.zeros(num_classes, d, dtype=torch.float32)
    mu.index_add_(0, y, x)
    counts = torch.bincount(y, minlength=num_classes).clamp_min(1).float().unsqueeze(1)
    mu = mu / counts
    weight = mu.t().contiguous()
    bias = -0.5 * (mu * mu).sum(dim=1)
    return weight, bias


def _fit_ridge(x, y, num_classes, lam):
    n, d = x.shape
    xb = torch.cat([x, torch.ones(n, 1, dtype=torch.float32)], dim=1)  # (n, d+1)
    yoh = _make_onehot(y, num_classes, dtype=torch.float32)  # (n, c)
    xtx = xb.t().matmul(xb)  # (d+1, d+1)
    reg = torch.eye(d + 1, dtype=torch.float32) * float(lam)
    reg[-1, -1] = 0.0
    a = xtx + reg
    b = xb.t().matmul(yoh)  # (d+1, c)
    wb = torch.linalg.solve(a, b)  # (d+1, c)
    weight = wb[:-1, :].contiguous()
    bias = wb[-1, :].contiguous()
    return weight, bias


def _fit_lda(x, y, num_classes, alpha):
    n, d = x.shape
    mu = torch.zeros(num_classes, d, dtype=torch.float32)
    mu.index_add_(0, y, x)
    counts = torch.bincount(y, minlength=num_classes).clamp_min(1).float().unsqueeze(1)
    mu = mu / counts
    centered = x - mu[y]
    denom = float(max(1, n - num_classes))
    sigma = centered.t().matmul(centered) / denom
    sigma2 = float(torch.trace(sigma).item() / d) if d > 0 else 1.0
    a = sigma + (float(alpha) * sigma2 + 1e-6 * sigma2) * torch.eye(d, dtype=torch.float32)
    inv_mu = torch.linalg.solve(a, mu.t())  # (d, c)
    quad = (mu * inv_mu.t()).sum(dim=1)  # (c,)
    bias = (-0.5 * quad).contiguous()
    weight = inv_mu.contiguous()
    return weight, bias


def _compute_norm_stats(x, eps=1e-5):
    mean = x.mean(dim=0)
    var = (x - mean).pow(2).mean(dim=0)
    std = torch.sqrt(var + eps)
    return mean, std


def _fit_rff_ridge(x, y, num_classes, proj_w, proj_b, lam):
    n = x.size(0)
    z = torch.cos(x.matmul(proj_w) + proj_b) * math.sqrt(2.0 / float(proj_w.size(1)))  # (n, m)
    zb = torch.cat([z, torch.ones(n, 1, dtype=torch.float32)], dim=1)  # (n, m+1)
    yoh = _make_onehot(y, num_classes, dtype=torch.float32)  # (n, c)
    m1 = zb.size(1)
    ztz = zb.t().matmul(zb)  # (m+1, m+1)
    reg = torch.eye(m1, dtype=torch.float32) * float(lam)
    reg[-1, -1] = 0.0
    a = ztz + reg
    b = zb.t().matmul(yoh)  # (m+1, c)
    wb = torch.linalg.solve(a, b)  # (m+1, c)
    out_w = wb[:-1, :].contiguous()
    out_b = wb[-1, :].contiguous()
    return out_w, out_b


class Solution:
    def solve(self, train_loader, val_loader, metadata: dict = None) -> torch.nn.Module:
        try:
            torch.set_num_threads(min(8, os.cpu_count() or 8))
        except Exception:
            pass

        if metadata is None:
            metadata = {}
        input_dim = int(metadata.get("input_dim", 384))
        num_classes = int(metadata.get("num_classes", 128))
        param_limit = int(metadata.get("param_limit", 5_000_000))
        device = str(metadata.get("device", "cpu"))

        torch.manual_seed(0)

        x_tr, y_tr = _collect_xy(train_loader, input_dim=input_dim)
        x_va, y_va = _collect_xy(val_loader, input_dim=input_dim)

        if x_tr.numel() == 0:
            model = nn.Linear(input_dim, num_classes)
            return model.to(device)

        mean, std = _compute_norm_stats(x_tr)
        xtrn = (x_tr - mean) / std
        xvan = (x_va - mean) / std if x_va.numel() else x_va

        candidates = []

        # Centroid
        w, b = _fit_centroid(xtrn, y_tr, num_classes)
        model_centroid = _NormalizedLinear(mean, std, w, b)
        acc_centroid = _accuracy(model_centroid, x_va, y_va) if x_va.numel() else 0.0
        candidates.append(("centroid", None, model_centroid, acc_centroid))

        # Ridge regression grid
        ridge_lams = [1e-6, 1e-5, 1e-4, 1e-3, 1e-2, 5e-2, 1e-1, 5e-1, 1.0, 5.0]
        for lam in ridge_lams:
            w, b = _fit_ridge(xtrn, y_tr, num_classes, lam)
            m = _NormalizedLinear(mean, std, w, b)
            acc = _accuracy(m, x_va, y_va) if x_va.numel() else 0.0
            candidates.append(("ridge", lam, m, acc))

        # LDA shrinkage grid
        lda_alphas = [0.0, 1e-5, 1e-4, 3e-4, 1e-3, 3e-3, 1e-2, 3e-2, 1e-1, 3e-1, 1.0]
        for a in lda_alphas:
            w, b = _fit_lda(xtrn, y_tr, num_classes, a)
            m = _NormalizedLinear(mean, std, w, b)
            acc = _accuracy(m, x_va, y_va) if x_va.numel() else 0.0
            candidates.append(("lda", a, m, acc))

        candidates.sort(key=lambda t: t[3], reverse=True)
        best_name, best_h, best_model, best_acc = candidates[0]

        # If linear doesn't look strong, try a small RFF ridge head
        if x_va.numel() and best_acc < 0.92:
            rff_specs = [
                (256, 1.0, [1e-3, 1e-2, 1e-1, 5e-1]),
                (384, 1.0, [1e-3, 1e-2, 1e-1, 5e-1]),
            ]
            for mfeat, gamma, lam_list in rff_specs:
                g = float(gamma)
                gen = torch.Generator(device="cpu")
                gen.manual_seed(12345 + mfeat)
                proj_w = torch.randn(input_dim, mfeat, generator=gen, dtype=torch.float32) * math.sqrt(2.0 * g)
                proj_b = torch.rand(mfeat, generator=gen, dtype=torch.float32) * (2.0 * math.pi)

                for lam in lam_list:
                    out_w, out_b = _fit_rff_ridge(xtrn, y_tr, num_classes, proj_w, proj_b, lam)
                    rff_model = _RFFModel(mean, std, proj_w, proj_b, out_w, out_b, scale=math.sqrt(2.0 / float(mfeat)))
                    acc = _accuracy(rff_model, x_va, y_va)
                    candidates.append(("rff", (mfeat, g, lam), rff_model, acc))

            candidates.sort(key=lambda t: t[3], reverse=True)
            best_name, best_h, best_model, best_acc = candidates[0]

        # Try simple ensemble of top-2
        if x_va.numel() and len(candidates) >= 2:
            top = candidates[:4]
            best_ens = None
            best_ens_acc = best_acc
            for i in range(min(3, len(top))):
                for j in range(i + 1, min(4, len(top))):
                    m1 = top[i][2]
                    m2 = top[j][2]
                    ens = _Ensemble([m1, m2])
                    acc = _accuracy(ens, x_va, y_va)
                    if acc > best_ens_acc + 1e-6:
                        best_ens_acc = acc
                        best_ens = (("ens", (top[i][0], top[i][1], top[j][0], top[j][1]), ens, acc))
            if best_ens is not None:
                best_name, best_h, best_model, best_acc = best_ens

        # Refit on train+val with chosen method (and chosen hypers); then return
        x_all = x_tr
        y_all = y_tr
        if x_va.numel():
            x_all = torch.cat([x_tr, x_va], dim=0)
            y_all = torch.cat([y_tr, y_va], dim=0)

        mean2, std2 = _compute_norm_stats(x_all)
        xalln = (x_all - mean2) / std2

        def refit_one(name, h):
            if name == "centroid":
                w, b = _fit_centroid(xalln, y_all, num_classes)
                return _NormalizedLinear(mean2, std2, w, b)
            if name == "ridge":
                w, b = _fit_ridge(xalln, y_all, num_classes, float(h))
                return _NormalizedLinear(mean2, std2, w, b)
            if name == "lda":
                w, b = _fit_lda(xalln, y_all, num_classes, float(h))
                return _NormalizedLinear(mean2, std2, w, b)
            if name == "rff":
                mfeat, gamma, lam = h
                gen = torch.Generator(device="cpu")
                gen.manual_seed(12345 + int(mfeat))
                proj_w = torch.randn(input_dim, int(mfeat), generator=gen, dtype=torch.float32) * math.sqrt(2.0 * float(gamma))
                proj_b = torch.rand(int(mfeat), generator=gen, dtype=torch.float32) * (2.0 * math.pi)
                out_w, out_b = _fit_rff_ridge(xalln, y_all, num_classes, proj_w, proj_b, float(lam))
                return _RFFModel(mean2, std2, proj_w, proj_b, out_w, out_b, scale=math.sqrt(2.0 / float(mfeat)))
            raise ValueError("unknown model")

        if best_name == "ens":
            n1, h1, n2, h2 = best_h
            m1 = refit_one(n1, h1)
            m2 = refit_one(n2, h2)
            final_model = _Ensemble([m1, m2])
        else:
            final_model = refit_one(best_name, best_h)

        final_model = final_model.to(device)
        final_model.eval()

        trainable_params = sum(p.numel() for p in final_model.parameters() if p.requires_grad)
        if trainable_params > param_limit:
            final_model = nn.Linear(input_dim, num_classes).to(device)
            final_model.eval()

        return final_model
