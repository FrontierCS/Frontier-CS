import os
import math
import random
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F


def _set_seeds(seed: int = 0):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)


def _collect_xy(loader):
    xs = []
    ys = []
    for batch in loader:
        if isinstance(batch, (list, tuple)) and len(batch) >= 2:
            x, y = batch[0], batch[1]
        else:
            raise ValueError("Dataloader batch must be (inputs, targets).")
        if not torch.is_tensor(x):
            x = torch.as_tensor(x)
        if not torch.is_tensor(y):
            y = torch.as_tensor(y)
        x = x.detach().to(dtype=torch.float32).view(x.shape[0], -1).cpu()
        y = y.detach().to(dtype=torch.long).view(-1).cpu()
        xs.append(x)
        ys.append(y)
    return torch.cat(xs, dim=0), torch.cat(ys, dim=0)


def _mean_invstd(X: torch.Tensor, eps: float = 1e-6):
    mean = X.mean(dim=0)
    var = X.var(dim=0, unbiased=False)
    inv_std = torch.rsqrt(var + eps)
    return mean, inv_std


def _acc_from_logits(logits: torch.Tensor, y: torch.Tensor) -> float:
    return (logits.argmax(dim=1) == y).float().mean().item()


def _confusion_free_bincount(y: torch.Tensor, minlength: int):
    if y.numel() == 0:
        return torch.zeros(minlength, dtype=torch.long, device=y.device)
    return torch.bincount(y, minlength=minlength)


def _fit_nearest_mean_from_norm(Xn: torch.Tensor, y: torch.Tensor, num_classes: int):
    d = Xn.shape[1]
    sums = torch.zeros((num_classes, d), dtype=Xn.dtype, device=Xn.device)
    sums.index_add_(0, y, Xn)
    counts = _confusion_free_bincount(y, num_classes).to(dtype=Xn.dtype, device=Xn.device).clamp_min(1.0)
    mu = sums / counts.unsqueeze(1)
    W = (2.0 * mu).t().contiguous()  # d x C
    b = -(mu * mu).sum(dim=1).contiguous()  # C
    return W, b


def _fit_lda_from_norm(Xn: torch.Tensor, y: torch.Tensor, num_classes: int, alpha: float):
    d = Xn.shape[1]
    sums = torch.zeros((num_classes, d), dtype=Xn.dtype, device=Xn.device)
    sums.index_add_(0, y, Xn)
    counts = _confusion_free_bincount(y, num_classes).to(dtype=Xn.dtype, device=Xn.device).clamp_min(1.0)
    mu = sums / counts.unsqueeze(1)  # C x d

    Xc = Xn - mu[y]  # N x d
    S = (Xc.t() @ Xc) / max(1, Xc.shape[0])
    S = 0.5 * (S + S.t())
    diag = torch.diagonal(S, 0)
    diag.add_(alpha)

    try:
        L = torch.linalg.cholesky(S)
        W = torch.cholesky_solve(mu.t(), L)  # d x C
    except Exception:
        S2 = S.clone()
        torch.diagonal(S2, 0).add_(alpha * 10.0 + 1e-4)
        L = torch.linalg.cholesky(S2)
        W = torch.cholesky_solve(mu.t(), L)

    b = (-0.5 * (mu * W.t()).sum(dim=1)).contiguous()  # C
    W = W.contiguous()
    return W, b


def _fit_ridge_onehot_from_norm(Xn: torch.Tensor, y: torch.Tensor, num_classes: int, lam: float, fit_bias: bool = True):
    N, d = Xn.shape
    if fit_bias:
        ones = torch.ones((N, 1), dtype=Xn.dtype, device=Xn.device)
        Xa = torch.cat([Xn, ones], dim=1)
    else:
        Xa = Xn
    p = Xa.shape[1]

    A = Xa.t() @ Xa
    reg = lam * float(N)
    if reg > 0:
        diag = torch.diagonal(A, 0)
        if fit_bias:
            diag[:-1].add_(reg)
        else:
            diag.add_(reg)

    sums = torch.zeros((num_classes, p), dtype=Xn.dtype, device=Xn.device)
    sums.index_add_(0, y, Xa)
    XtY = sums.t().contiguous()  # p x C

    try:
        Waug = torch.linalg.solve(A, XtY)  # p x C
    except Exception:
        A2 = A.clone()
        torch.diagonal(A2, 0).add_(1e-3)
        Waug = torch.linalg.solve(A2, XtY)

    if fit_bias:
        W = Waug[:-1, :].contiguous()
        b = Waug[-1, :].contiguous()
    else:
        W = Waug.contiguous()
        b = torch.zeros((num_classes,), dtype=Xn.dtype, device=Xn.device)

    return W, b


def _fit_elm_from_norm(Xn: torch.Tensor, y: torch.Tensor, num_classes: int, hidden_dim: int, lam: float, seed: int = 0, fit_bias: bool = True):
    g = torch.Generator(device=Xn.device)
    g.manual_seed(seed)

    N, d = Xn.shape
    W1 = torch.randn((d, hidden_dim), dtype=Xn.dtype, device=Xn.device, generator=g) * (1.0 / math.sqrt(d))
    b1 = torch.randn((hidden_dim,), dtype=Xn.dtype, device=Xn.device, generator=g) * 0.1

    H = F.gelu(Xn @ W1 + b1)
    if fit_bias:
        ones = torch.ones((N, 1), dtype=Xn.dtype, device=Xn.device)
        Ha = torch.cat([H, ones], dim=1)
    else:
        Ha = H
    m = Ha.shape[1]

    HtH = Ha.t() @ Ha
    reg = lam * float(N)
    if reg > 0:
        diag = torch.diagonal(HtH, 0)
        if fit_bias:
            diag[:-1].add_(reg)
        else:
            diag.add_(reg)

    sums = torch.zeros((num_classes, m), dtype=Xn.dtype, device=Xn.device)
    sums.index_add_(0, y, Ha)
    HtY = sums.t().contiguous()  # m x C

    try:
        Beta = torch.linalg.solve(HtH, HtY)  # m x C
    except Exception:
        HtH2 = HtH.clone()
        torch.diagonal(HtH2, 0).add_(1e-3)
        Beta = torch.linalg.solve(HtH2, HtY)

    if fit_bias:
        BetaW = Beta[:-1, :].contiguous()  # hidden x C
        Betab = Beta[-1, :].contiguous()   # C
    else:
        BetaW = Beta.contiguous()
        Betab = torch.zeros((num_classes,), dtype=Xn.dtype, device=Xn.device)

    return W1.contiguous(), b1.contiguous(), BetaW, Betab


class FixedLinearClassifier(nn.Module):
    def __init__(self, mean: torch.Tensor, inv_std: torch.Tensor, W: torch.Tensor, b: torch.Tensor):
        super().__init__()
        self.register_buffer("mean", mean.detach().to(dtype=torch.float32))
        self.register_buffer("inv_std", inv_std.detach().to(dtype=torch.float32))
        self.register_buffer("W", W.detach().to(dtype=torch.float32))  # d x C
        self.register_buffer("b", b.detach().to(dtype=torch.float32))  # C

    def forward(self, x):
        if not torch.is_tensor(x):
            x = torch.as_tensor(x)
        x = x.to(dtype=torch.float32).view(x.shape[0], -1)
        x = (x - self.mean) * self.inv_std
        return x @ self.W + self.b


class ELMClassifier(nn.Module):
    def __init__(self, mean: torch.Tensor, inv_std: torch.Tensor, W1: torch.Tensor, b1: torch.Tensor, BetaW: torch.Tensor, Betab: torch.Tensor):
        super().__init__()
        self.register_buffer("mean", mean.detach().to(dtype=torch.float32))
        self.register_buffer("inv_std", inv_std.detach().to(dtype=torch.float32))
        self.register_buffer("W1", W1.detach().to(dtype=torch.float32))
        self.register_buffer("b1", b1.detach().to(dtype=torch.float32))
        self.register_buffer("BetaW", BetaW.detach().to(dtype=torch.float32))
        self.register_buffer("Betab", Betab.detach().to(dtype=torch.float32))

    def forward(self, x):
        if not torch.is_tensor(x):
            x = torch.as_tensor(x)
        x = x.to(dtype=torch.float32).view(x.shape[0], -1)
        x = (x - self.mean) * self.inv_std
        h = F.gelu(x @ self.W1 + self.b1)
        return h @ self.BetaW + self.Betab


class ResidualMLP(nn.Module):
    def __init__(self, input_dim: int, num_classes: int, hidden_dim: int, mean: torch.Tensor, inv_std: torch.Tensor, dropout: float = 0.1):
        super().__init__()
        self.register_buffer("mean", mean.detach().to(dtype=torch.float32))
        self.register_buffer("inv_std", inv_std.detach().to(dtype=torch.float32))
        self.fc1 = nn.Linear(input_dim, hidden_dim, bias=True)
        self.ln1 = nn.LayerNorm(hidden_dim)
        self.fc2 = nn.Linear(hidden_dim, hidden_dim, bias=True)
        self.ln2 = nn.LayerNorm(hidden_dim)
        self.drop = nn.Dropout(dropout)
        self.out = nn.Linear(hidden_dim, num_classes, bias=True)

    def forward(self, x):
        if not torch.is_tensor(x):
            x = torch.as_tensor(x)
        x = x.to(dtype=torch.float32).view(x.shape[0], -1)
        x = (x - self.mean) * self.inv_std
        h = F.gelu(self.ln1(self.fc1(x)))
        r = F.gelu(self.ln2(self.fc2(h)))
        h = h + self.drop(r)
        h = self.drop(h)
        return self.out(h)


def _count_trainable_params(model: nn.Module) -> int:
    return sum(p.numel() for p in model.parameters() if p.requires_grad)


def _choose_hidden_dim(input_dim: int, num_classes: int, param_limit: int, use_layernorm: bool = True) -> int:
    # ResidualMLP params:
    # fc1: input_dim*h + h
    # fc2: h*h + h
    # out: h*num_classes + num_classes
    # layernorms: 2 LNs -> 4h params if use_layernorm
    # total = h*(input_dim + h + num_classes + 2 (biases fc1,fc2) + 4 (LN) ) + num_classes + ??? => h*(input_dim + h + num_classes + 6) + num_classes
    add = 6 if use_layernorm else 2
    lo, hi = 16, 4096
    best = lo
    while lo <= hi:
        mid = (lo + hi) // 2
        total = mid * (input_dim + mid + num_classes + add) + num_classes
        if total <= param_limit:
            best = mid
            lo = mid + 1
        else:
            hi = mid - 1
    return best


def _train_mlp(train_loader, val_loader, input_dim: int, num_classes: int, param_limit: int, device: str):
    Xtr, ytr = _collect_xy(train_loader)
    mean, inv_std = _mean_invstd(Xtr)

    hidden = _choose_hidden_dim(input_dim, num_classes, param_limit, use_layernorm=True)
    hidden = min(hidden, 512)
    model = ResidualMLP(input_dim, num_classes, hidden, mean, inv_std, dropout=0.1).to(device=device)
    if _count_trainable_params(model) > param_limit:
        hidden = max(32, hidden - 8)
        model = ResidualMLP(input_dim, num_classes, hidden, mean, inv_std, dropout=0.1).to(device=device)

    optimizer = torch.optim.AdamW(model.parameters(), lr=2e-3, weight_decay=1e-3)
    steps_per_epoch = max(1, len(train_loader))
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=max(1, 80 * steps_per_epoch))
    criterion = nn.CrossEntropyLoss(label_smoothing=0.1)

    best_state = None
    best_acc = -1.0
    patience = 20
    bad = 0
    max_epochs = 80

    for epoch in range(max_epochs):
        model.train()
        for xb, yb in train_loader:
            if not torch.is_tensor(xb):
                xb = torch.as_tensor(xb)
            if not torch.is_tensor(yb):
                yb = torch.as_tensor(yb)
            xb = xb.to(device=device, dtype=torch.float32).view(xb.shape[0], -1)
            yb = yb.to(device=device, dtype=torch.long).view(-1)

            optimizer.zero_grad(set_to_none=True)
            logits = model(xb)
            loss = criterion(logits, yb)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
            scheduler.step()

        model.eval()
        with torch.inference_mode():
            correct = 0
            total = 0
            for xb, yb in val_loader:
                if not torch.is_tensor(xb):
                    xb = torch.as_tensor(xb)
                if not torch.is_tensor(yb):
                    yb = torch.as_tensor(yb)
                xb = xb.to(device=device, dtype=torch.float32).view(xb.shape[0], -1)
                yb = yb.to(device=device, dtype=torch.long).view(-1)
                pred = model(xb).argmax(dim=1)
                correct += (pred == yb).sum().item()
                total += yb.numel()
            acc = correct / max(1, total)

        if acc > best_acc + 1e-6:
            best_acc = acc
            best_state = {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}
            bad = 0
        else:
            bad += 1
            if bad >= patience:
                break

    if best_state is not None:
        model.load_state_dict(best_state, strict=True)
    model.eval()
    return model, best_acc


class Solution:
    def solve(self, train_loader, val_loader, metadata: dict = None) -> torch.nn.Module:
        if metadata is None:
            metadata = {}
        device = metadata.get("device", "cpu")
        input_dim = int(metadata.get("input_dim", 384))
        num_classes = int(metadata.get("num_classes", 128))
        param_limit = int(metadata.get("param_limit", 200000))

        try:
            torch.set_num_threads(min(8, os.cpu_count() or 8))
        except Exception:
            pass
        _set_seeds(0)

        Xtr, ytr = _collect_xy(train_loader)
        Xva, yva = _collect_xy(val_loader)

        # Selection normalization on train
        mean_tr, invstd_tr = _mean_invstd(Xtr)
        Xtrn = (Xtr - mean_tr) * invstd_tr
        Xvan = (Xva - mean_tr) * invstd_tr

        best = {"name": None, "score": -1.0, "params": None}

        # Nearest mean
        W_nm, b_nm = _fit_nearest_mean_from_norm(Xtrn, ytr, num_classes)
        acc_nm = _acc_from_logits(Xvan @ W_nm + b_nm, yva)
        best = {"name": "nm", "score": acc_nm, "params": (W_nm, b_nm)} if acc_nm > best["score"] else best

        # LDA sweep
        alphas = [1e-4, 3e-4, 1e-3, 3e-3, 1e-2, 3e-2, 1e-1]
        for a in alphas:
            W_lda, b_lda = _fit_lda_from_norm(Xtrn, ytr, num_classes, alpha=float(a))
            acc_lda = _acc_from_logits(Xvan @ W_lda + b_lda, yva)
            if acc_lda > best["score"]:
                best = {"name": "lda", "score": acc_lda, "params": (float(a), W_lda, b_lda)}

        # Ridge sweep (with bias)
        lams = [0.0, 1e-6, 3e-6, 1e-5, 3e-5, 1e-4, 3e-4, 1e-3, 3e-3, 1e-2, 3e-2, 1e-1]
        for lam in lams:
            W_r, b_r = _fit_ridge_onehot_from_norm(Xtrn, ytr, num_classes, lam=float(lam), fit_bias=True)
            acc_r = _acc_from_logits(Xvan @ W_r + b_r, yva)
            if acc_r > best["score"]:
                best = {"name": "ridge", "score": acc_r, "params": (float(lam), W_r, b_r)}

        # If linear is not strong enough, try ELM (still closed-form output)
        if best["score"] < 0.80:
            elm_hidden = 512
            elm_lams = [1e-4, 3e-4, 1e-3, 3e-3, 1e-2, 3e-2]
            for lam in elm_lams:
                W1, b1, BetaW, Betab = _fit_elm_from_norm(Xtrn, ytr, num_classes, hidden_dim=elm_hidden, lam=float(lam), seed=0, fit_bias=True)
                Hv = F.gelu(Xvan @ W1 + b1)
                acc_e = _acc_from_logits(Hv @ BetaW + Betab, yva)
                if acc_e > best["score"]:
                    best = {"name": "elm", "score": acc_e, "params": (elm_hidden, float(lam), 0, W1, b1, BetaW, Betab)}

        # If still low, train a small MLP
        mlp_model = None
        mlp_acc = -1.0
        if best["score"] < 0.74:
            mlp_model, mlp_acc = _train_mlp(train_loader, val_loader, input_dim, num_classes, param_limit, device)
            if mlp_acc > best["score"]:
                best = {"name": "mlp", "score": mlp_acc, "params": None}

        # Refit chosen closed-form model on train+val
        if best["name"] in ("nm", "lda", "ridge", "elm"):
            Xall = torch.cat([Xtr, Xva], dim=0)
            yall = torch.cat([ytr, yva], dim=0)
            mean_all, invstd_all = _mean_invstd(Xall)
            Xalln = (Xall - mean_all) * invstd_all

            if best["name"] == "nm":
                W, b = _fit_nearest_mean_from_norm(Xalln, yall, num_classes)
                model = FixedLinearClassifier(mean_all, invstd_all, W, b).to(device=device)
                model.eval()
                return model

            if best["name"] == "lda":
                alpha = float(best["params"][0])
                W, b = _fit_lda_from_norm(Xalln, yall, num_classes, alpha=alpha)
                model = FixedLinearClassifier(mean_all, invstd_all, W, b).to(device=device)
                model.eval()
                return model

            if best["name"] == "ridge":
                lam = float(best["params"][0])
                W, b = _fit_ridge_onehot_from_norm(Xalln, yall, num_classes, lam=lam, fit_bias=True)
                model = FixedLinearClassifier(mean_all, invstd_all, W, b).to(device=device)
                model.eval()
                return model

            if best["name"] == "elm":
                hidden_dim, lam, seed = int(best["params"][0]), float(best["params"][1]), int(best["params"][2])
                W1, b1, BetaW, Betab = _fit_elm_from_norm(Xalln, yall, num_classes, hidden_dim=hidden_dim, lam=lam, seed=seed, fit_bias=True)
                model = ELMClassifier(mean_all, invstd_all, W1, b1, BetaW, Betab).to(device=device)
                model.eval()
                return model

        # MLP fallback (already trained)
        if mlp_model is not None:
            if _count_trainable_params(mlp_model) <= param_limit:
                mlp_model.eval()
                return mlp_model
            # If somehow exceeded, fallback to nearest mean refit
            Xall = torch.cat([Xtr, Xva], dim=0)
            yall = torch.cat([ytr, yva], dim=0)
            mean_all, invstd_all = _mean_invstd(Xall)
            Xalln = (Xall - mean_all) * invstd_all
            W, b = _fit_nearest_mean_from_norm(Xalln, yall, num_classes)
            model = FixedLinearClassifier(mean_all, invstd_all, W, b).to(device=device)
            model.eval()
            return model

        # Should not happen; fallback to nearest mean on combined
        Xall = torch.cat([Xtr, Xva], dim=0)
        yall = torch.cat([ytr, yva], dim=0)
        mean_all, invstd_all = _mean_invstd(Xall)
        Xalln = (Xall - mean_all) * invstd_all
        W, b = _fit_nearest_mean_from_norm(Xalln, yall, num_classes)
        model = FixedLinearClassifier(mean_all, invstd_all, W, b).to(device=device)
        model.eval()
        return model