import os
import math
import torch
import torch.nn as nn


def _set_torch_threads():
    try:
        n = os.cpu_count() or 8
        torch.set_num_threads(min(8, n))
        torch.set_num_interop_threads(1)
    except Exception:
        pass


def _collect_xy(loader):
    xs, ys = [], []
    for batch in loader:
        if isinstance(batch, (list, tuple)) and len(batch) >= 2:
            x, y = batch[0], batch[1]
        else:
            continue
        xs.append(x.detach().to("cpu"))
        ys.append(y.detach().to("cpu"))
    if not xs:
        return torch.empty(0, 0), torch.empty(0, dtype=torch.long)
    X = torch.cat(xs, dim=0)
    y = torch.cat(ys, dim=0)
    if X.dtype != torch.float32:
        X = X.float()
    if y.dtype != torch.long:
        y = y.long()
    return X, y


def _standardize_fit(X, eps=1e-6):
    mean = X.mean(dim=0)
    var = X.var(dim=0, unbiased=False)
    std = torch.sqrt(var + eps)
    return mean, std


def _standardize_apply(X, mean, std):
    return (X - mean) / std


def _accuracy_from_logits(logits, y):
    if logits.numel() == 0:
        return 0.0
    preds = logits.argmax(dim=1)
    return (preds == y).float().mean().item()


def _bincount(y, K):
    bc = torch.bincount(y, minlength=K)
    if bc.numel() < K:
        bc = torch.cat([bc, torch.zeros(K - bc.numel(), dtype=bc.dtype)], dim=0)
    return bc


def _class_means_and_vars(X, y, K):
    # X: (N, D)
    N, D = X.shape
    sums = torch.zeros(K, D, dtype=X.dtype)
    sums.index_add_(0, y, X)
    counts = _bincount(y, K).to(X.dtype).clamp_min(1.0)
    means = sums / counts[:, None]

    sumsq = torch.zeros(K, D, dtype=X.dtype)
    sumsq.index_add_(0, y, X * X)
    vars_ = (sumsq / counts[:, None]) - (means * means)
    vars_ = vars_.clamp_min(0.0)
    return means, vars_, counts


def _lda_precompute(X, y, K):
    # X: standardized float32
    X64 = X.double()
    y64 = y
    means32, _, counts32 = _class_means_and_vars(X, y, K)
    means64 = means32.double()
    counts64 = counts32.double()
    N = X.shape[0]
    D = X.shape[1]

    priors = (counts64 / max(1.0, float(N))).clamp_min(1e-12)
    log_priors = priors.log()

    # pooled covariance
    mu_y = means64[y64]  # (N, D)
    Xc = X64 - mu_y
    denom = max(1.0, float(N - K))
    S = (Xc.t().matmul(Xc)) / denom  # (D, D)
    avgvar = torch.trace(S) / float(D)
    return {
        "means": means64,        # (K, D)
        "log_priors": log_priors,  # (K,)
        "S": S,                  # (D, D)
        "avgvar": avgvar,        # scalar
    }


def _lda_from_precompute(pre, shrink, eps_scale=1e-4):
    means = pre["means"]           # (K, D)
    log_priors = pre["log_priors"] # (K,)
    S = pre["S"]                   # (D, D)
    avgvar = pre["avgvar"]         # scalar
    D = S.shape[0]

    # Regularization: (1-shrink) S + shrink * avgvar I + eps * avgvar I
    eps = eps_scale
    Sreg = (1.0 - shrink) * S + (shrink + eps) * avgvar * torch.eye(D, dtype=S.dtype)

    # Solve Sreg @ W = means^T
    W = torch.linalg.solve(Sreg, means.t())  # (D, K)

    # b_k = -0.5 * mu_k^T invS mu_k + log prior
    quad = (means * W.t()).sum(dim=1)  # (K,)
    b = (-0.5 * quad) + log_priors

    return W.float(), b.float()


def _gnb_precompute(X, y, K):
    means32, vars32, counts32 = _class_means_and_vars(X, y, K)
    global_var32 = X.var(dim=0, unbiased=False).clamp_min(0.0)
    priors32 = (counts32 / max(1.0, float(X.shape[0]))).clamp_min(1e-12)
    return {
        "means": means32,
        "vars": vars32,
        "global_var": global_var32,
        "log_priors": priors32.log(),
    }


def _gnb_from_precompute(pre, shrink, var_eps=1e-4):
    means = pre["means"]           # (K, D)
    vars_ = pre["vars"]            # (K, D)
    global_var = pre["global_var"] # (D,)
    log_priors = pre["log_priors"] # (K,)

    vars_sh = (1.0 - shrink) * vars_ + shrink * global_var[None, :]
    vars_sh = (vars_sh + var_eps).clamp_min(var_eps)

    inv_var = 1.0 / vars_sh
    A = means * inv_var  # (K, D)
    B = -0.5 * inv_var   # (K, D)
    mu2_over_var_sum = (means * means * inv_var).sum(dim=1)  # (K,)
    logdet = vars_sh.log().sum(dim=1)  # (K,)
    bias = (-0.5 * mu2_over_var_sum) + (-0.5 * logdet) + log_priors  # (K,)

    return A, B, bias


def _logits_lda(Xs, W, b):
    return Xs.matmul(W) + b


def _logits_gnb(Xs, A, B, bias):
    x2 = Xs * Xs
    return Xs.matmul(A.t()) + x2.matmul(B.t()) + bias


def _fit_linear_lbfgs(Z, y, out_dim, l2=1e-3, max_iter=200):
    # Z: (N, F), y: (N,)
    model = nn.Linear(Z.shape[1], out_dim, bias=True)
    model.train()
    optimizer = torch.optim.LBFGS(
        model.parameters(),
        lr=1.0,
        max_iter=max_iter,
        tolerance_grad=1e-9,
        tolerance_change=1e-12,
        history_size=20,
        line_search_fn="strong_wolfe",
    )
    criterion = nn.CrossEntropyLoss()

    def closure():
        optimizer.zero_grad(set_to_none=True)
        logits = model(Z)
        loss = criterion(logits, y)
        if l2 and l2 > 0:
            loss = loss + 0.5 * l2 * (model.weight.pow(2).sum())
        loss.backward()
        return loss

    optimizer.step(closure)
    model.eval()
    return model


class _Standardizer(nn.Module):
    def __init__(self, mean, std):
        super().__init__()
        self.mean = nn.Parameter(mean.detach().clone().float(), requires_grad=False)
        self.inv_std = nn.Parameter((1.0 / std.detach().clone().float()).clamp(max=1e6), requires_grad=False)

    def forward(self, x):
        x = x.float()
        return (x - self.mean) * self.inv_std


class _LDAModel(nn.Module):
    def __init__(self, mean, std, W, b):
        super().__init__()
        self.std = _Standardizer(mean, std)
        self.W = nn.Parameter(W.detach().clone().float(), requires_grad=False)  # (D, K)
        self.b = nn.Parameter(b.detach().clone().float(), requires_grad=False)  # (K,)

    def forward(self, x):
        xs = self.std(x)
        return xs.matmul(self.W) + self.b


class _GNBModel(nn.Module):
    def __init__(self, mean, std, A, B, bias):
        super().__init__()
        self.std = _Standardizer(mean, std)
        self.A = nn.Parameter(A.detach().clone().float(), requires_grad=False)       # (K, D)
        self.B = nn.Parameter(B.detach().clone().float(), requires_grad=False)       # (K, D)
        self.bias = nn.Parameter(bias.detach().clone().float(), requires_grad=False) # (K,)

    def forward(self, x):
        xs = self.std(x)
        x2 = xs * xs
        return xs.matmul(self.A.t()) + x2.matmul(self.B.t()) + self.bias


class _EnsembleModel(nn.Module):
    def __init__(self, model1, model2, beta: float):
        super().__init__()
        self.model1 = model1
        self.model2 = model2
        self.beta = nn.Parameter(torch.tensor(float(beta), dtype=torch.float32), requires_grad=False)

    def forward(self, x):
        return self.model1(x) + self.beta * self.model2(x)


class _StackedModel(nn.Module):
    def __init__(self, model1, model2, head: nn.Linear):
        super().__init__()
        self.model1 = model1
        self.model2 = model2
        self.head = head

    def forward(self, x):
        l1 = self.model1(x)
        l2 = self.model2(x)
        z = torch.cat([l1, l2], dim=1)
        return self.head(z)


class Solution:
    def solve(self, train_loader, val_loader, metadata: dict = None) -> torch.nn.Module:
        _set_torch_threads()

        if metadata is None:
            metadata = {}
        device = metadata.get("device", "cpu")
        num_classes = int(metadata.get("num_classes", 128))
        input_dim = int(metadata.get("input_dim", 384))
        param_limit = int(metadata.get("param_limit", 2_500_000))

        Xtr, ytr = _collect_xy(train_loader)
        Xva, yva = _collect_xy(val_loader) if val_loader is not None else (torch.empty(0, input_dim), torch.empty(0, dtype=torch.long))

        if Xtr.numel() == 0:
            # Fallback: simple linear model with zero weights
            model = nn.Linear(input_dim, num_classes)
            with torch.no_grad():
                model.weight.zero_()
                model.bias.zero_()
            return model.to(device)

        if Xtr.dim() != 2:
            Xtr = Xtr.view(Xtr.shape[0], -1)
        if Xva.numel() and Xva.dim() != 2:
            Xva = Xva.view(Xva.shape[0], -1)

        if Xtr.shape[1] != input_dim:
            input_dim = int(Xtr.shape[1])

        # Phase 1: choose hyperparams using train normalization and val accuracy
        mean_tr, std_tr = _standardize_fit(Xtr)
        Xtr_s = _standardize_apply(Xtr, mean_tr, std_tr)
        Xva_s = _standardize_apply(Xva, mean_tr, std_tr) if Xva.numel() else Xva

        lda_shrinks = [0.0, 0.02, 0.05, 0.1, 0.2, 0.4]
        gnb_shrinks = [0.0, 0.02, 0.05, 0.1, 0.2, 0.4]

        lda_pre = _lda_precompute(Xtr_s, ytr, num_classes)
        gnb_pre = _gnb_precompute(Xtr_s, ytr, num_classes)

        lda_candidates = []
        for s in lda_shrinks:
            try:
                W, b = _lda_from_precompute(lda_pre, shrink=float(s))
                logits_va = _logits_lda(Xva_s, W, b) if Xva.numel() else torch.empty(0, num_classes)
                acc = _accuracy_from_logits(logits_va, yva) if Xva.numel() else 0.0
                lda_candidates.append((acc, float(s), W, b))
            except Exception:
                continue
        lda_candidates.sort(key=lambda t: t[0], reverse=True)
        if not lda_candidates:
            # fallback minimal
            W = torch.zeros(input_dim, num_classes, dtype=torch.float32)
            b = torch.zeros(num_classes, dtype=torch.float32)
            lda_candidates = [(0.0, 0.2, W, b)]

        gnb_candidates = []
        for s in gnb_shrinks:
            try:
                A, B, bias = _gnb_from_precompute(gnb_pre, shrink=float(s), var_eps=1e-4)
                logits_va = _logits_gnb(Xva_s, A, B, bias) if Xva.numel() else torch.empty(0, num_classes)
                acc = _accuracy_from_logits(logits_va, yva) if Xva.numel() else 0.0
                gnb_candidates.append((acc, float(s), A, B, bias))
            except Exception:
                continue
        gnb_candidates.sort(key=lambda t: t[0], reverse=True)
        if not gnb_candidates:
            A = torch.zeros(num_classes, input_dim, dtype=torch.float32)
            B = torch.zeros(num_classes, input_dim, dtype=torch.float32)
            bias = torch.zeros(num_classes, dtype=torch.float32)
            gnb_candidates = [(0.0, 0.2, A, B, bias)]

        # keep top-2 each for pairing
        lda_top = lda_candidates[:2]
        gnb_top = gnb_candidates[:2]

        best_kind = "lda"
        best_score = lda_top[0][0]
        best_conf = {"lda_shrink": lda_top[0][1]}

        # consider pure GNB
        if gnb_top[0][0] > best_score:
            best_kind = "gnb"
            best_score = gnb_top[0][0]
            best_conf = {"gnb_shrink": gnb_top[0][1]}

        # consider logistic regression on standardized features (from scratch)
        if Xva.numel():
            try:
                lin0 = _fit_linear_lbfgs(Xtr_s, ytr, out_dim=num_classes, l2=1e-3, max_iter=200)
                with torch.no_grad():
                    acc0 = _accuracy_from_logits(lin0(Xva_s), yva)
                if acc0 > best_score:
                    best_kind = "logreg"
                    best_score = acc0
                    best_conf = {"l2": 1e-3, "init": "none"}
            except Exception:
                pass

        # consider logistic regression init from best LDA
        if Xva.numel():
            try:
                _, lda_s, Wbest, bbest = lda_top[0]
                lin1 = nn.Linear(input_dim, num_classes, bias=True)
                with torch.no_grad():
                    lin1.weight.copy_(Wbest.t().contiguous())
                    lin1.bias.copy_(bbest.contiguous())
                lin1.train()
                opt = torch.optim.LBFGS(
                    lin1.parameters(),
                    lr=1.0,
                    max_iter=150,
                    tolerance_grad=1e-9,
                    tolerance_change=1e-12,
                    history_size=20,
                    line_search_fn="strong_wolfe",
                )
                crit = nn.CrossEntropyLoss()
                l2 = 5e-4

                def closure():
                    opt.zero_grad(set_to_none=True)
                    logits = lin1(Xtr_s)
                    loss = crit(logits, ytr) + 0.5 * l2 * lin1.weight.pow(2).sum()
                    loss.backward()
                    return loss

                opt.step(closure)
                lin1.eval()
                with torch.no_grad():
                    acc1 = _accuracy_from_logits(lin1(Xva_s), yva)
                if acc1 > best_score:
                    best_kind = "logreg"
                    best_score = acc1
                    best_conf = {"l2": l2, "init": "lda", "lda_shrink": lda_s}
            except Exception:
                pass

        # ensembles and stacking
        beta_grid = [0.25, 0.5, 1.0, 2.0, 4.0]
        l2_grid_stack = [1e-4, 5e-4, 1e-3, 5e-3]

        if Xva.numel():
            for acc_lda, s_lda, W, b in lda_top:
                logits_tr_lda = _logits_lda(Xtr_s, W, b)
                logits_va_lda = _logits_lda(Xva_s, W, b)

                for acc_gnb, s_gnb, A, B, bias in gnb_top:
                    logits_tr_gnb = _logits_gnb(Xtr_s, A, B, bias)
                    logits_va_gnb = _logits_gnb(Xva_s, A, B, bias)

                    # linear ensemble
                    for beta in beta_grid:
                        logits_va = logits_va_lda + float(beta) * logits_va_gnb
                        acc = _accuracy_from_logits(logits_va, yva)
                        if acc > best_score:
                            best_kind = "ens"
                            best_score = acc
                            best_conf = {"lda_shrink": s_lda, "gnb_shrink": s_gnb, "beta": float(beta)}

                    # stacking
                    Ztr = torch.cat([logits_tr_lda, logits_tr_gnb], dim=1)
                    Zva = torch.cat([logits_va_lda, logits_va_gnb], dim=1)
                    for l2s in l2_grid_stack:
                        try:
                            head = _fit_linear_lbfgs(Ztr, ytr, out_dim=num_classes, l2=float(l2s), max_iter=200)
                            with torch.no_grad():
                                acc = _accuracy_from_logits(head(Zva), yva)
                            if acc > best_score:
                                best_kind = "stack"
                                best_score = acc
                                best_conf = {"lda_shrink": s_lda, "gnb_shrink": s_gnb, "l2": float(l2s)}
                        except Exception:
                            continue

        # Phase 2: refit final model using train+val combined for better test performance
        if Xva.numel():
            Xall = torch.cat([Xtr, Xva], dim=0)
            yall = torch.cat([ytr, yva], dim=0)
        else:
            Xall, yall = Xtr, ytr

        mean_all, std_all = _standardize_fit(Xall)
        Xall_s = _standardize_apply(Xall, mean_all, std_all)

        final_model = None

        if best_kind == "lda":
            lda_pre2 = _lda_precompute(Xall_s, yall, num_classes)
            s = float(best_conf.get("lda_shrink", lda_top[0][1]))
            W, b = _lda_from_precompute(lda_pre2, shrink=s)
            final_model = _LDAModel(mean_all, std_all, W, b)

        elif best_kind == "gnb":
            gnb_pre2 = _gnb_precompute(Xall_s, yall, num_classes)
            s = float(best_conf.get("gnb_shrink", gnb_top[0][1]))
            A, B, bias = _gnb_from_precompute(gnb_pre2, shrink=s, var_eps=1e-4)
            final_model = _GNBModel(mean_all, std_all, A, B, bias)

        elif best_kind == "ens":
            lda_pre2 = _lda_precompute(Xall_s, yall, num_classes)
            gnb_pre2 = _gnb_precompute(Xall_s, yall, num_classes)
            s_lda = float(best_conf["lda_shrink"])
            s_gnb = float(best_conf["gnb_shrink"])
            beta = float(best_conf["beta"])
            W, b = _lda_from_precompute(lda_pre2, shrink=s_lda)
            A, B, bias = _gnb_from_precompute(gnb_pre2, shrink=s_gnb, var_eps=1e-4)
            m1 = _LDAModel(mean_all, std_all, W, b)
            m2 = _GNBModel(mean_all, std_all, A, B, bias)
            final_model = _EnsembleModel(m1, m2, beta=beta)

        elif best_kind == "stack":
            lda_pre2 = _lda_precompute(Xall_s, yall, num_classes)
            gnb_pre2 = _gnb_precompute(Xall_s, yall, num_classes)
            s_lda = float(best_conf["lda_shrink"])
            s_gnb = float(best_conf["gnb_shrink"])
            l2s = float(best_conf.get("l2", 1e-3))
            W, b = _lda_from_precompute(lda_pre2, shrink=s_lda)
            A, B, bias = _gnb_from_precompute(gnb_pre2, shrink=s_gnb, var_eps=1e-4)

            base_lda = _LDAModel(mean_all, std_all, W, b)
            base_gnb = _GNBModel(mean_all, std_all, A, B, bias)

            with torch.no_grad():
                logits_all_lda = base_lda(Xall)
                logits_all_gnb = base_gnb(Xall)
                Zall = torch.cat([logits_all_lda, logits_all_gnb], dim=1)

            head = _fit_linear_lbfgs(Zall, yall, out_dim=num_classes, l2=l2s, max_iter=250)
            final_model = _StackedModel(base_lda, base_gnb, head)

        elif best_kind == "logreg":
            l2 = float(best_conf.get("l2", 1e-3))
            init = best_conf.get("init", "none")
            lin = nn.Linear(input_dim, num_classes, bias=True)

            if init == "lda":
                s = float(best_conf.get("lda_shrink", lda_top[0][1]))
                lda_pre2 = _lda_precompute(Xall_s, yall, num_classes)
                W, b = _lda_from_precompute(lda_pre2, shrink=s)
                with torch.no_grad():
                    lin.weight.copy_(W.t().contiguous())
                    lin.bias.copy_(b.contiguous())

            lin.train()
            opt = torch.optim.LBFGS(
                lin.parameters(),
                lr=1.0,
                max_iter=200,
                tolerance_grad=1e-9,
                tolerance_change=1e-12,
                history_size=20,
                line_search_fn="strong_wolfe",
            )
            crit = nn.CrossEntropyLoss()

            def closure():
                opt.zero_grad(set_to_none=True)
                logits = lin(Xall_s)
                loss = crit(logits, yall) + 0.5 * l2 * lin.weight.pow(2).sum()
                loss.backward()
                return loss

            opt.step(closure)
            lin.eval()

            class _StdLinear(nn.Module):
                def __init__(self, mean, std, lin_layer):
                    super().__init__()
                    self.std = _Standardizer(mean, std)
                    self.lin = lin_layer

                def forward(self, x):
                    xs = self.std(x)
                    return self.lin(xs)

            final_model = _StdLinear(mean_all, std_all, lin)

        else:
            # fallback to best LDA
            lda_pre2 = _lda_precompute(Xall_s, yall, num_classes)
            W, b = _lda_from_precompute(lda_pre2, shrink=0.1)
            final_model = _LDAModel(mean_all, std_all, W, b)

        final_model = final_model.to(device)
        final_model.eval()

        # Safety check: ensure under param_limit if evaluator counts all parameters
        total_params = sum(p.numel() for p in final_model.parameters())
        if total_params > param_limit:
            # Hard fallback: tiny linear
            fallback = nn.Linear(input_dim, num_classes).to(device)
            fallback.eval()
            return fallback

        return final_model
