import os
import math
from copy import deepcopy
import torch
import torch.nn as nn
import torch.nn.functional as F


def _collect_from_loader(loader, device="cpu"):
    xs, ys = [], []
    for batch in loader:
        if isinstance(batch, (list, tuple)) and len(batch) >= 2:
            x, y = batch[0], batch[1]
        else:
            continue
        if not torch.is_tensor(x):
            x = torch.tensor(x)
        if not torch.is_tensor(y):
            y = torch.tensor(y)
        xs.append(x.detach().to(device="cpu"))
        ys.append(y.detach().to(device="cpu"))
    if not xs:
        return torch.empty(0), torch.empty(0, dtype=torch.long)
    X = torch.cat(xs, dim=0).contiguous()
    y = torch.cat(ys, dim=0).contiguous().long()
    return X, y


@torch.inference_mode()
def _acc_from_logits(logits, y):
    return (logits.argmax(dim=1) == y).float().mean().item()


@torch.inference_mode()
def _acc_model_on_tensor(model, X, y, batch_size=256):
    model.eval()
    n = y.numel()
    correct = 0
    for i in range(0, n, batch_size):
        xb = X[i:i + batch_size]
        yb = y[i:i + batch_size]
        out = model(xb)
        pred = out.argmax(dim=1)
        correct += (pred == yb).sum().item()
    return correct / max(1, n)


def _trainable_param_count(model: nn.Module) -> int:
    return sum(p.numel() for p in model.parameters() if p.requires_grad)


class Preprocessor(nn.Module):
    def __init__(self, mean1, std1, P, mean2, std2):
        super().__init__()
        self.register_buffer("mean1", mean1.float().contiguous())
        self.register_buffer("std1", std1.float().contiguous())
        if P is None:
            P = torch.empty(0, 0, dtype=torch.float32)
            self.use_pca = False
        else:
            P = P.float().contiguous()
            self.use_pca = P.numel() > 0
        self.register_buffer("P", P)
        self.register_buffer("mean2", mean2.float().contiguous())
        self.register_buffer("std2", std2.float().contiguous())

    def forward(self, x):
        if not torch.is_tensor(x):
            x = torch.tensor(x)
        x = x.to(dtype=torch.float32, device=self.mean1.device)
        x = (x - self.mean1) / self.std1
        if self.use_pca:
            x = x @ self.P
        x = (x - self.mean2) / self.std2
        return x


class LDAModel(nn.Module):
    def __init__(self, pre: Preprocessor, W, b):
        super().__init__()
        self.pre = pre
        self.register_buffer("W", W.float().contiguous())  # (D, C)
        self.register_buffer("b", b.float().contiguous())  # (C,)

    def forward(self, x):
        z = self.pre(x)
        return z @ self.W + self.b


class KNNModel(nn.Module):
    def __init__(self, pre: Preprocessor, train_feats, train_labels, num_classes: int, k: int = 7, temperature: float = 0.07):
        super().__init__()
        self.pre = pre
        self.register_buffer("train_feats", train_feats.float().contiguous())
        self.register_buffer("train_labels", train_labels.long().contiguous())
        self.num_classes = int(num_classes)
        self.k = int(k)
        self.temperature = float(temperature)

    def forward(self, x):
        z = self.pre(x)
        z = F.normalize(z, dim=1, eps=1e-12)
        sims = z @ self.train_feats.t()
        vals, idx = torch.topk(sims, k=self.k, dim=1, largest=True, sorted=False)
        lbl = self.train_labels[idx]
        vals = (vals - vals[:, :1]) / max(self.temperature, 1e-6)
        w = torch.exp(vals)
        out = torch.zeros(z.size(0), self.num_classes, dtype=torch.float32, device=z.device)
        out.scatter_add_(1, lbl, w)
        return out


class LogSoftmaxEnsemble(nn.Module):
    def __init__(self, models, weights=None):
        super().__init__()
        self.models = nn.ModuleList(models)
        if weights is None:
            weights = [1.0] * len(models)
        self.weights = [float(w) for w in weights]

    def forward(self, x):
        acc = None
        for m, w in zip(self.models, self.weights):
            logits = m(x)
            lp = F.log_softmax(logits, dim=1)
            if acc is None:
                acc = lp * w
            else:
                acc = acc + lp * w
        return acc


class BottleneckResidual(nn.Module):
    def __init__(self, dim, bottleneck, dropout=0.10):
        super().__init__()
        self.ln = nn.LayerNorm(dim)
        self.fc1 = nn.Linear(dim, bottleneck)
        self.fc2 = nn.Linear(bottleneck, dim)
        self.dropout = nn.Dropout(dropout)

    def forward(self, x):
        y = self.ln(x)
        y = F.gelu(self.fc1(y))
        y = self.dropout(y)
        y = self.fc2(y)
        return x + y


class MLPCore(nn.Module):
    def __init__(self, feat_dim: int, num_classes: int, hidden_dim: int, b1: int, b2: int, dropout=0.10):
        super().__init__()
        self.fc_in = nn.Linear(feat_dim, hidden_dim)
        self.dropout0 = nn.Dropout(dropout)
        self.block1 = BottleneckResidual(hidden_dim, b1, dropout=dropout)
        self.block2 = BottleneckResidual(hidden_dim, b2, dropout=dropout)
        self.ln_out = nn.LayerNorm(hidden_dim)
        self.fc_out = nn.Linear(hidden_dim, num_classes)

    def forward(self, z):
        z = F.gelu(self.fc_in(z))
        z = self.dropout0(z)
        z = self.block1(z)
        z = self.block2(z)
        z = self.ln_out(z)
        return self.fc_out(z)


class MLPModel(nn.Module):
    def __init__(self, pre: Preprocessor, core: MLPCore):
        super().__init__()
        self.pre = pre
        self.core = core

    def forward(self, x):
        z = self.pre(x)
        return self.core(z)


def _mlp_param_count(feat_dim, num_classes, hidden_dim, b1, b2):
    # fc_in
    total = feat_dim * hidden_dim + hidden_dim
    # blocks (each: dim->b -> dim)
    for b in (b1, b2):
        total += hidden_dim * b + b
        total += b * hidden_dim + hidden_dim
        total += 2 * hidden_dim  # LayerNorm affine
    total += 2 * hidden_dim  # ln_out
    total += hidden_dim * num_classes + num_classes  # fc_out
    return total


def _pick_mlp_arch(feat_dim, num_classes, param_limit):
    hidden_candidates = [1024, 960, 928, 896, 864, 832, 816, 800, 768, 736, 704, 672, 640, 608, 576, 544, 512]
    b1_candidates = [384, 352, 320, 288, 256, 224, 192, 160, 128]
    b2_candidates = [256, 224, 192, 176, 160, 144, 128, 112, 96, 80, 64]
    best = None
    best_params = -1
    for h in hidden_candidates:
        for b1 in b1_candidates:
            if b1 >= h:
                continue
            for b2 in b2_candidates:
                if b2 >= h:
                    continue
                params = _mlp_param_count(feat_dim, num_classes, h, b1, b2)
                if params <= param_limit and params > best_params:
                    best_params = params
                    best = (h, b1, b2)
    if best is None:
        best = (512, min(128, max(32, feat_dim // 2)), min(64, max(16, feat_dim // 4)))
    return best


def _build_preprocessor(X_train_raw, input_dim, pca_dim=256):
    X_train_raw = X_train_raw.float()
    mean1 = X_train_raw.mean(dim=0)
    std1 = X_train_raw.std(dim=0, unbiased=False).clamp_min(1e-6)
    X0 = (X_train_raw - mean1) / std1

    d = int(input_dim)
    q = int(min(pca_dim, d, max(8, d)))
    if q >= d:
        P = None
        Xf = X0
    else:
        q = min(q, X0.shape[0] - 1, d)
        if q < 8:
            P = None
            Xf = X0
        else:
            torch.manual_seed(0)
            U, S, V = torch.pca_lowrank(X0, q=q, center=False)
            P = V[:, :q].contiguous()
            Xf = X0 @ P

    mean2 = Xf.mean(dim=0)
    std2 = Xf.std(dim=0, unbiased=False).clamp_min(1e-6)
    pre = Preprocessor(mean1, std1, P, mean2, std2)
    feat_dim = Xf.shape[1]
    return pre, feat_dim


def _lda_fit(X_feat, y, num_classes, shrinkage=0.10):
    X = X_feat.double()
    y = y.long()
    n, d = X.shape
    C = int(num_classes)
    means = torch.zeros(C, d, dtype=torch.float64)
    counts = torch.bincount(y, minlength=C).double().clamp_min(1.0)
    for c in range(C):
        mask = (y == c)
        if mask.any():
            means[c] = X[mask].mean(dim=0)
    centered = X - means[y]
    denom = max(1, n - C)
    cov = (centered.t() @ centered) / float(denom)

    alpha = float(shrinkage)
    avg_var = cov.diag().mean()
    cov = (1.0 - alpha) * cov + alpha * avg_var * torch.eye(d, dtype=torch.float64)

    chol = torch.linalg.cholesky(cov)
    W = torch.cholesky_solve(means.t(), chol)  # (d, C)
    quad = (means * W.t()).sum(dim=1)  # (C,)
    priors = counts / counts.sum()
    b = -0.5 * quad + torch.log(priors.clamp_min(1e-12))
    return W.float().contiguous(), b.float().contiguous()


def _knn_select_best(train_feat, y_train, val_feat, y_val, num_classes):
    train_f = F.normalize(train_feat.float(), dim=1, eps=1e-12)
    val_f = F.normalize(val_feat.float(), dim=1, eps=1e-12)

    sims = val_f @ train_f.t()  # (Nv, Nt)
    max_k = 25
    max_k = min(max_k, train_f.shape[0])
    topv, topi = torch.topk(sims, k=max_k, dim=1, largest=True, sorted=False)
    topl = y_train[topi]

    k_list = [1, 3, 5, 7, 9, 15, 25]
    k_list = [k for k in k_list if k <= max_k]
    t_list = [0.03, 0.05, 0.07, 0.10, 0.15, 0.20, 0.30]

    best = None
    best_acc = -1.0
    best_logits = None

    Nv = y_val.numel()
    for k in k_list:
        lbl = topl[:, :k]
        v = topv[:, :k]
        for t in t_list:
            vv = (v - v[:, :1]) / max(float(t), 1e-6)
            w = torch.exp(vv)
            out = torch.zeros(Nv, int(num_classes), dtype=torch.float32)
            out.scatter_add_(1, lbl, w)
            acc = _acc_from_logits(out, y_val)
            if acc > best_acc:
                best_acc = acc
                best = (k, float(t))
                best_logits = out
    return best, best_acc, best_logits, train_f


def _train_mlp_core(core: MLPCore, X_train_feat, y_train, X_val_feat, y_val, max_epochs=220, batch_size=256):
    device = torch.device("cpu")
    core.to(device)
    X_train_feat = X_train_feat.float().contiguous()
    y_train = y_train.long().contiguous()
    X_val_feat = X_val_feat.float().contiguous()
    y_val = y_val.long().contiguous()

    ds = torch.utils.data.TensorDataset(X_train_feat, y_train)
    loader = torch.utils.data.DataLoader(ds, batch_size=batch_size, shuffle=True, drop_last=False, num_workers=0)

    base_lr = 3e-3
    optimizer = torch.optim.AdamW(core.parameters(), lr=base_lr, weight_decay=0.02)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=max_epochs)

    criterion = nn.CrossEntropyLoss(label_smoothing=0.10)

    best_state = None
    best_acc = -1.0
    patience = 30
    bad = 0
    eval_every = 2
    warmup = 8

    for epoch in range(1, max_epochs + 1):
        core.train()
        if epoch <= warmup:
            lr = base_lr * (epoch / warmup)
            for pg in optimizer.param_groups:
                pg["lr"] = lr

        for xb, yb in loader:
            if xb.numel() == 0:
                continue
            noise_std = 0.03
            xb = xb + torch.randn_like(xb) * noise_std

            optimizer.zero_grad(set_to_none=True)
            logits = core(xb)
            loss = criterion(logits, yb)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(core.parameters(), 1.0)
            optimizer.step()

        scheduler.step()

        if epoch % eval_every == 0 or epoch == max_epochs:
            core.eval()
            with torch.inference_mode():
                logits_val = core(X_val_feat)
                acc = _acc_from_logits(logits_val, y_val)
            if acc > best_acc + 1e-5:
                best_acc = acc
                best_state = deepcopy(core.state_dict())
                bad = 0
            else:
                bad += 1
                if bad >= patience:
                    break

    if best_state is not None:
        core.load_state_dict(best_state)
    core.eval()
    return best_acc


class Solution:
    def solve(self, train_loader, val_loader, metadata: dict = None) -> torch.nn.Module:
        try:
            torch.set_num_threads(min(8, os.cpu_count() or 1))
        except Exception:
            pass
        try:
            torch.set_num_interop_threads(1)
        except Exception:
            pass

        if metadata is None:
            metadata = {}
        input_dim = int(metadata.get("input_dim", 384))
        num_classes = int(metadata.get("num_classes", 128))
        param_limit = int(metadata.get("param_limit", 1_000_000))
        device = metadata.get("device", "cpu")
        if device != "cpu":
            device = "cpu"

        X_train_raw, y_train = _collect_from_loader(train_loader, device=device)
        X_val_raw, y_val = _collect_from_loader(val_loader, device=device)

        if X_train_raw.numel() == 0:
            model = nn.Linear(input_dim, num_classes)
            return model.eval()

        pre, feat_dim = _build_preprocessor(X_train_raw, input_dim=input_dim, pca_dim=256)

        with torch.inference_mode():
            X_train_feat = pre(X_train_raw)
            X_val_feat = pre(X_val_raw)

        # LDA
        W_lda, b_lda = _lda_fit(X_train_feat, y_train, num_classes=num_classes, shrinkage=0.10)
        lda_logits_val = X_val_feat @ W_lda + b_lda
        lda_acc = _acc_from_logits(lda_logits_val, y_val)
        lda_model = LDAModel(pre, W_lda, b_lda).eval()

        # KNN
        best_knn, knn_acc, knn_logits_val, train_f_norm = _knn_select_best(
            X_train_feat, y_train, X_val_feat, y_val, num_classes=num_classes
        )
        if best_knn is None:
            best_knn = (7, 0.07)
            knn_acc = -1.0
        knn_k, knn_t = best_knn
        knn_model = KNNModel(pre, train_f_norm, y_train, num_classes=num_classes, k=knn_k, temperature=knn_t).eval()

        best_model = lda_model
        best_acc = lda_acc
        if knn_acc > best_acc:
            best_model = knn_model
            best_acc = knn_acc

        # LDA+KNN ensemble
        ens_model = None
        ens_acc = -1.0
        if knn_logits_val is not None:
            lda_lp = F.log_softmax(lda_logits_val, dim=1)
            knn_lp = F.log_softmax(knn_logits_val, dim=1)
            for w_lda in (0.5, 1.0, 1.5, 2.0):
                for w_knn in (0.5, 1.0, 1.5, 2.0):
                    lp = w_lda * lda_lp + w_knn * knn_lp
                    acc = _acc_from_logits(lp, y_val)
                    if acc > ens_acc:
                        ens_acc = acc
                        ens_model = LogSoftmaxEnsemble([lda_model, knn_model], [w_lda, w_knn]).eval()
        if ens_acc > best_acc:
            best_acc = ens_acc
            best_model = ens_model

        # If already very strong, skip MLP training
        if best_acc >= 0.93:
            return best_model.eval()

        # MLP
        h, b1, b2 = _pick_mlp_arch(int(feat_dim), num_classes, param_limit)
        core = MLPCore(int(feat_dim), num_classes, hidden_dim=int(h), b1=int(b1), b2=int(b2), dropout=0.10)
        if _trainable_param_count(core) > param_limit:
            # fallback smaller
            core = MLPCore(int(feat_dim), num_classes, hidden_dim=640, b1=192, b2=96, dropout=0.10)

        _train_mlp_core(core, X_train_feat, y_train, X_val_feat, y_val, max_epochs=220, batch_size=256)

        mlp_logits_val = core(X_val_feat)
        mlp_acc = _acc_from_logits(mlp_logits_val, y_val)
        mlp_model = MLPModel(pre, core).eval()

        if _trainable_param_count(mlp_model) > param_limit:
            # Hard constraint protection: if something went wrong, don't return it
            mlp_model = None
            mlp_acc = -1.0

        if mlp_acc > best_acc:
            best_acc = mlp_acc
            best_model = mlp_model

        # Ensemble with MLP if available
        if mlp_model is not None and knn_logits_val is not None:
            mlp_lp = F.log_softmax(mlp_logits_val, dim=1)
            lda_lp = F.log_softmax(lda_logits_val, dim=1)
            knn_lp = F.log_softmax(knn_logits_val, dim=1)

            candidates = []
            candidates.append(([mlp_model, knn_model], [1.0, 1.0], mlp_lp + knn_lp))
            candidates.append(([mlp_model, lda_model], [1.0, 1.0], mlp_lp + lda_lp))
            candidates.append(([mlp_model, lda_model, knn_model], [1.0, 0.75, 1.0], mlp_lp + 0.75 * lda_lp + knn_lp))

            for mods, ws, lp in candidates:
                acc = _acc_from_logits(lp, y_val)
                if acc > best_acc:
                    best_acc = acc
                    best_model = LogSoftmaxEnsemble(mods, ws).eval()

        if best_model is None:
            best_model = lda_model.eval()

        # Final safety check
        if _trainable_param_count(best_model) > param_limit:
            return lda_model.eval()
        return best_model.eval()
