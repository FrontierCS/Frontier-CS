import os
import math
import torch
import torch.nn as nn
import torch.nn.functional as F


def _unpack_batch(batch):
    if isinstance(batch, (list, tuple)):
        if len(batch) >= 2:
            return batch[0], batch[1]
        return batch[0], None
    return batch, None


def _collect_loader(loader, device="cpu"):
    xs = []
    ys = []
    for batch in loader:
        x, y = _unpack_batch(batch)
        if not torch.is_tensor(x):
            x = torch.as_tensor(x)
        x = x.detach().to(device=device)
        x = x.view(x.shape[0], -1).contiguous()
        if y is not None:
            if not torch.is_tensor(y):
                y = torch.as_tensor(y)
            y = y.detach().to(device=device).long().view(-1).contiguous()
            ys.append(y)
        xs.append(x)
    x_all = torch.cat(xs, dim=0) if xs else torch.empty(0, device=device)
    y_all = torch.cat(ys, dim=0) if ys else None
    return x_all, y_all


def _make_standardizer(x, mode: str):
    if mode == "none":
        mean = torch.zeros(x.shape[1], dtype=torch.float32, device=x.device)
        inv_std = torch.ones(x.shape[1], dtype=torch.float32, device=x.device)
        return mean, inv_std
    mean = x.mean(dim=0).to(dtype=torch.float32)
    var = x.var(dim=0, unbiased=False).to(dtype=torch.float32)
    std = torch.sqrt(var.clamp_min(1e-8))
    inv_std = (1.0 / std).to(dtype=torch.float32)
    return mean, inv_std


def _standardize(x, mean, inv_std):
    return (x.to(dtype=torch.float32) - mean) * inv_std


def _accuracy_from_logits(logits, y):
    preds = logits.argmax(dim=1)
    return (preds == y).float().mean().item()


def _class_means(x, y, num_classes):
    d = x.shape[1]
    sums = torch.zeros(num_classes, d, dtype=torch.float32, device=x.device)
    counts = torch.zeros(num_classes, dtype=torch.float32, device=x.device)
    sums.index_add_(0, y, x.to(dtype=torch.float32))
    counts.index_add_(0, y, torch.ones_like(y, dtype=torch.float32))
    means = sums / counts.clamp_min(1.0).unsqueeze(1)
    return means, counts


def _ridge_fit_weights(x_std, y, num_classes, lam):
    # x_std: (N,D), float32
    # returns W_aug: (D+1,C), float32 where last row is bias
    n, d = x_std.shape
    xa = torch.cat([x_std, torch.ones(n, 1, dtype=torch.float32, device=x_std.device)], dim=1)
    xa64 = xa.to(dtype=torch.float64)
    y_onehot = torch.zeros(n, num_classes, dtype=torch.float64, device=x_std.device)
    y_onehot.scatter_(1, y.view(-1, 1), 1.0)
    xtx = xa64.T @ xa64
    eye = torch.eye(d + 1, dtype=torch.float64, device=x_std.device)
    reg = float(lam)
    a = xtx + (reg + 1e-10) * eye
    xty = xa64.T @ y_onehot
    try:
        l = torch.linalg.cholesky(a)
        w = torch.cholesky_solve(xty, l)
    except Exception:
        w = torch.linalg.solve(a, xty)
    return w.to(dtype=torch.float32)


def _lda_fit(x_std, y, num_classes, lam):
    # Shared covariance LDA with shrinkage lam*I
    n, d = x_std.shape
    means, counts = _class_means(x_std, y, num_classes)
    x_centered = x_std - means[y]
    xc64 = x_centered.to(dtype=torch.float64)
    cov = (xc64.T @ xc64) / max(1, n)
    eye = torch.eye(d, dtype=torch.float64, device=x_std.device)
    a = cov + (float(lam) + 1e-10) * eye
    mu64 = means.to(dtype=torch.float64)  # (C,D)
    try:
        l = torch.linalg.cholesky(a)
        inv_mu_t = torch.cholesky_solve(mu64.T, l)  # (D,C) = inv(A) @ mu.T
    except Exception:
        inv_mu_t = torch.linalg.solve(a, mu64.T)
    w = inv_mu_t.to(dtype=torch.float32)  # (D,C)
    # bias b_c = -0.5 * mu_c^T invS mu_c
    quad = (mu64 * inv_mu_t.T).sum(dim=1)  # (C,)
    b = (-0.5 * quad).to(dtype=torch.float32)
    return w, b


def _diag_nb_fit(x_std, y, num_classes, var_smooth):
    # Gaussian Naive Bayes with diagonal cov per class
    n, d = x_std.shape
    means, counts = _class_means(x_std, y, num_classes)  # (C,D)
    x_centered = x_std - means[y]
    # compute per-class variance
    sums2 = torch.zeros(num_classes, d, dtype=torch.float32, device=x_std.device)
    sums2.index_add_(0, y, (x_centered * x_centered).to(dtype=torch.float32))
    counts_f = counts.clamp_min(1.0).unsqueeze(1)
    var = sums2 / counts_f
    var = var + float(var_smooth)
    inv_var = 1.0 / var
    # Precompute matrices for efficient scoring:
    # score = -0.5 * [ x^2 @ inv_var.T - 2 x @ (mu*inv_var).T + sum(mu^2*inv_var + log(var)) ]
    a = inv_var  # (C,D)
    b = means * inv_var  # (C,D)
    const = (means * means * inv_var + torch.log(var)).sum(dim=1)  # (C,)
    return a, b, const


class _PrototypeCosine(nn.Module):
    def __init__(self, mean, inv_std, prototypes, normalize_input=True):
        super().__init__()
        self.register_buffer("mean", mean.clone())
        self.register_buffer("inv_std", inv_std.clone())
        proto = prototypes.to(dtype=torch.float32)
        proto = F.normalize(proto, dim=1, eps=1e-8)
        self.register_buffer("proto", proto)
        self.normalize_input = bool(normalize_input)

    def forward(self, x):
        x = x.view(x.shape[0], -1)
        x = _standardize(x, self.mean, self.inv_std)
        if self.normalize_input:
            x = F.normalize(x, dim=1, eps=1e-8)
        return x @ self.proto.t()


class _RidgeLinear(nn.Module):
    def __init__(self, mean, inv_std, w_aug):
        super().__init__()
        self.register_buffer("mean", mean.clone())
        self.register_buffer("inv_std", inv_std.clone())
        self.register_buffer("w_aug", w_aug.clone())  # (D+1,C)

    def forward(self, x):
        x = x.view(x.shape[0], -1)
        x = _standardize(x, self.mean, self.inv_std)
        xa = torch.cat([x, torch.ones(x.shape[0], 1, dtype=torch.float32, device=x.device)], dim=1)
        return xa @ self.w_aug


class _LDA(nn.Module):
    def __init__(self, mean, inv_std, w, b):
        super().__init__()
        self.register_buffer("mean", mean.clone())
        self.register_buffer("inv_std", inv_std.clone())
        self.register_buffer("w", w.clone())  # (D,C)
        self.register_buffer("b", b.clone())  # (C,)

    def forward(self, x):
        x = x.view(x.shape[0], -1)
        x = _standardize(x, self.mean, self.inv_std)
        return x @ self.w + self.b


class _DiagNB(nn.Module):
    def __init__(self, mean, inv_std, a, b, const):
        super().__init__()
        self.register_buffer("mean", mean.clone())
        self.register_buffer("inv_std", inv_std.clone())
        self.register_buffer("a", a.clone())  # (C,D)
        self.register_buffer("b", b.clone())  # (C,D)
        self.register_buffer("const", const.clone())  # (C,)

    def forward(self, x):
        x = x.view(x.shape[0], -1)
        x = _standardize(x, self.mean, self.inv_std)
        x2 = x * x
        t1 = x2 @ self.a.t()
        t2 = x @ self.b.t()
        return -0.5 * (t1 - 2.0 * t2 + self.const)


class _KNN(nn.Module):
    def __init__(self, mean, inv_std, train_x, train_y, num_classes, k=5, temp=20.0):
        super().__init__()
        self.register_buffer("mean", mean.clone())
        self.register_buffer("inv_std", inv_std.clone())
        tx = train_x.to(dtype=torch.float32)
        tx = F.normalize(tx, dim=1, eps=1e-8)
        self.register_buffer("train_x", tx)
        self.register_buffer("train_y", train_y.to(dtype=torch.long))
        self.num_classes = int(num_classes)
        self.k = int(k)
        self.temp = float(temp)

    def forward(self, x):
        x = x.view(x.shape[0], -1)
        x = _standardize(x, self.mean, self.inv_std)
        x = F.normalize(x, dim=1, eps=1e-8)
        sim = x @ self.train_x.t()
        k = min(self.k, self.train_x.shape[0])
        vals, idx = torch.topk(sim, k=k, dim=1, largest=True, sorted=True)
        weights = torch.softmax(vals * self.temp, dim=1)
        labs = self.train_y[idx]
        out = torch.zeros(x.shape[0], self.num_classes, dtype=torch.float32, device=x.device)
        out.scatter_add_(1, labs, weights)
        return out


class _Ensemble(nn.Module):
    def __init__(self, models, weights):
        super().__init__()
        self.models = nn.ModuleList(models)
        w = torch.tensor(weights, dtype=torch.float32)
        w = w / w.sum().clamp_min(1e-12)
        self.register_buffer("weights", w)

    def forward(self, x):
        logits = None
        for i, m in enumerate(self.models):
            li = m(x)
            wi = self.weights[i]
            logits = li.mul(wi) if logits is None else logits.add(li.mul(wi))
        return logits


class Solution:
    def solve(self, train_loader, val_loader, metadata: dict = None) -> torch.nn.Module:
        if metadata is None:
            metadata = {}
        device = metadata.get("device", "cpu")
        if device is None:
            device = "cpu"
        device = str(device)

        try:
            torch.set_num_threads(min(8, os.cpu_count() or 8))
        except Exception:
            pass

        num_classes = int(metadata.get("num_classes", 128))
        input_dim = int(metadata.get("input_dim", 384))
        param_limit = int(metadata.get("param_limit", 5_000_000))

        x_train, y_train = _collect_loader(train_loader, device="cpu")
        if y_train is None:
            raise ValueError("Training loader must provide labels.")
        x_train = x_train.to(dtype=torch.float32).view(x_train.shape[0], -1).contiguous()
        y_train = y_train.to(dtype=torch.long).contiguous()
        if x_train.shape[1] != input_dim:
            input_dim = x_train.shape[1]

        if val_loader is not None:
            x_val, y_val = _collect_loader(val_loader, device="cpu")
            x_val = x_val.to(dtype=torch.float32).view(x_val.shape[0], -1).contiguous()
            y_val = y_val.to(dtype=torch.long).contiguous() if y_val is not None else None
        else:
            x_val, y_val = None, None

        preproc_modes = ["standardize", "none"]

        ridge_lams = [1e-6, 1e-5, 1e-4, 5e-4, 1e-3, 5e-3, 1e-2, 5e-2, 1e-1]
        lda_lams = [1e-5, 1e-4, 5e-4, 1e-3, 5e-3, 1e-2, 5e-2]
        nb_smooth = [1e-6, 1e-5, 1e-4, 5e-4, 1e-3, 5e-3, 1e-2]
        k_list = [1, 3, 5, 7, 9, 15]
        temp_list = [5.0, 10.0, 20.0, 40.0]
        k_max = max(k_list)

        candidates = []

        def _eval_model(model):
            if x_val is None or y_val is None:
                return -1.0
            with torch.no_grad():
                logits = model(x_val)
                return _accuracy_from_logits(logits, y_val)

        with torch.no_grad():
            for mode in preproc_modes:
                mean, inv_std = _make_standardizer(x_train, mode)
                xtr = _standardize(x_train, mean, inv_std)
                xva = _standardize(x_val, mean, inv_std) if x_val is not None else None

                # Prototype cosine variants (mean of raw standardized vs mean of normalized)
                means_c_raw, _ = _class_means(xtr, y_train, num_classes)
                proto_raw = means_c_raw
                model_proto_raw = _PrototypeCosine(mean, inv_std, proto_raw, normalize_input=True)
                acc = _eval_model(model_proto_raw)
                candidates.append(("proto_cos_rawmean", mode, {"variant": "rawmean"}, acc, model_proto_raw))

                xtr_n = F.normalize(xtr, dim=1, eps=1e-8)
                means_c_norm, _ = _class_means(xtr_n, y_train, num_classes)
                model_proto_norm = _PrototypeCosine(mean, inv_std, means_c_norm, normalize_input=True)
                acc = _eval_model(model_proto_norm)
                candidates.append(("proto_cos_normmean", mode, {"variant": "normmean"}, acc, model_proto_norm))

                # kNN cosine via precomputed sim/topk (only if val available)
                if x_val is not None and y_val is not None:
                    xva_n = F.normalize(xva, dim=1, eps=1e-8)
                    sim = xva_n @ xtr_n.t()
                    vals_max, idx_max = torch.topk(sim, k=min(k_max, sim.shape[1]), dim=1, largest=True, sorted=True)
                    labs_max = y_train[idx_max]

                    for k in k_list:
                        vals_k = vals_max[:, :k]
                        labs_k = labs_max[:, :k]
                        for temp in temp_list:
                            weights = torch.softmax(vals_k * temp, dim=1)
                            out = torch.zeros(xva.shape[0], num_classes, dtype=torch.float32)
                            out.scatter_add_(1, labs_k, weights)
                            acc = _accuracy_from_logits(out, y_val)
                            candidates.append(("knn_cos", mode, {"k": k, "temp": temp}, acc, None))

                # Ridge regression
                for lam in ridge_lams:
                    w_aug = _ridge_fit_weights(xtr, y_train, num_classes, lam)
                    model = _RidgeLinear(mean, inv_std, w_aug)
                    acc = _eval_model(model)
                    candidates.append(("ridge", mode, {"lam": lam}, acc, model))

                # LDA
                for lam in lda_lams:
                    w, b = _lda_fit(xtr, y_train, num_classes, lam)
                    model = _LDA(mean, inv_std, w, b)
                    acc = _eval_model(model)
                    candidates.append(("lda", mode, {"lam": lam}, acc, model))

                # Diagonal Gaussian NB
                for vs in nb_smooth:
                    a, b, const = _diag_nb_fit(xtr, y_train, num_classes, vs)
                    model = _DiagNB(mean, inv_std, a, b, const)
                    acc = _eval_model(model)
                    candidates.append(("diag_nb", mode, {"var_smooth": vs}, acc, model))

        # Choose best (with fallback when no val)
        if x_val is None or y_val is None:
            # Default to ridge with moderate regularization
            mode = "standardize"
            mean, inv_std = _make_standardizer(x_train, mode)
            xtr = _standardize(x_train, mean, inv_std)
            w_aug = _ridge_fit_weights(xtr, y_train, num_classes, 1e-3)
            model = _RidgeLinear(mean, inv_std, w_aug).to(device)
            model.eval()
            return model

        candidates_sorted = sorted(candidates, key=lambda t: (t[3] if t[3] is not None else -1.0), reverse=True)
        top = candidates_sorted[:8]

        # Build ensemble candidates from top fixed-logit models (excluding knn placeholder)
        fixed_models = []
        for name, mode, hp, acc, model in top:
            if model is not None and acc is not None and acc >= 0.0:
                fixed_models.append((name, mode, hp, acc, model))
        ensemble_best = None
        ensemble_best_acc = -1.0
        if len(fixed_models) >= 2:
            weights_grid = [(0.5, 0.5), (0.7, 0.3), (0.3, 0.7), (0.6, 0.4), (0.4, 0.6)]
            for i in range(min(4, len(fixed_models))):
                for j in range(i + 1, min(4, len(fixed_models))):
                    m1 = fixed_models[i][4]
                    m2 = fixed_models[j][4]
                    for w1, w2 in weights_grid:
                        ens = _Ensemble([m1, m2], [w1, w2])
                        acc = _eval_model(ens)
                        if acc > ensemble_best_acc:
                            ensemble_best_acc = acc
                            ensemble_best = ("ensemble2", None, {"pair": (fixed_models[i], fixed_models[j]), "weights": (w1, w2)}, acc, ens)

        best = candidates_sorted[0]
        if ensemble_best is not None and ensemble_best[3] is not None and ensemble_best[3] > best[3] + 1e-4:
            best = ensemble_best

        # Retrain/rebuild best using combined train+val for final
        x_all = torch.cat([x_train, x_val], dim=0)
        y_all = torch.cat([y_train, y_val], dim=0)

        def _build_model_from_spec(spec):
            name, mode, hp, acc, model_obj = spec
            if name == "ensemble2":
                (spec1, spec2) = hp["pair"]
                w1, w2 = hp["weights"]
                m1 = _build_model_from_spec((spec1[0], spec1[1], spec1[2], spec1[3], spec1[4]))
                m2 = _build_model_from_spec((spec2[0], spec2[1], spec2[2], spec2[3], spec2[4]))
                return _Ensemble([m1, m2], [w1, w2])

            if mode is None:
                mode = "standardize"

            mean, inv_std = _make_standardizer(x_all, mode)
            xa = _standardize(x_all, mean, inv_std)

            if name.startswith("proto_cos"):
                variant = hp.get("variant", "rawmean")
                if variant == "normmean":
                    xa_n = F.normalize(xa, dim=1, eps=1e-8)
                    means_c, _ = _class_means(xa_n, y_all, num_classes)
                    return _PrototypeCosine(mean, inv_std, means_c, normalize_input=True)
                means_c, _ = _class_means(xa, y_all, num_classes)
                return _PrototypeCosine(mean, inv_std, means_c, normalize_input=True)

            if name == "knn_cos":
                k = int(hp["k"])
                temp = float(hp["temp"])
                return _KNN(mean, inv_std, xa, y_all, num_classes, k=k, temp=temp)

            if name == "ridge":
                lam = float(hp["lam"])
                w_aug = _ridge_fit_weights(xa, y_all, num_classes, lam)
                return _RidgeLinear(mean, inv_std, w_aug)

            if name == "lda":
                lam = float(hp["lam"])
                w, b = _lda_fit(xa, y_all, num_classes, lam)
                return _LDA(mean, inv_std, w, b)

            if name == "diag_nb":
                vs = float(hp["var_smooth"])
                a, b, const = _diag_nb_fit(xa, y_all, num_classes, vs)
                return _DiagNB(mean, inv_std, a, b, const)

            # fallback
            w_aug = _ridge_fit_weights(xa, y_all, num_classes, 1e-3)
            return _RidgeLinear(mean, inv_std, w_aug)

        final_model = _build_model_from_spec(best).to(device)
        final_model.eval()

        # Hard constraint check (trainable params only)
        trainable_params = sum(p.numel() for p in final_model.parameters() if p.requires_grad)
        if trainable_params > param_limit:
            # Fallback to parameter-free prototype
            mean, inv_std = _make_standardizer(x_all, "standardize")
            xa = _standardize(x_all, mean, inv_std)
            means_c, _ = _class_means(xa, y_all, num_classes)
            final_model = _PrototypeCosine(mean, inv_std, means_c, normalize_input=True).to(device)
            final_model.eval()

        return final_model
