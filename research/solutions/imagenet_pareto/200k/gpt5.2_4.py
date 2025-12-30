import math
import copy
import torch
import torch.nn as nn
import torch.nn.functional as F


def _count_params_all(model: nn.Module) -> int:
    return sum(p.numel() for p in model.parameters())


@torch.no_grad()
def _infer_dims(train_loader, metadata):
    input_dim = None
    num_classes = None
    if metadata is not None:
        input_dim = metadata.get("input_dim", None)
        num_classes = metadata.get("num_classes", None)
    if input_dim is None or num_classes is None:
        xb, yb = next(iter(train_loader))
        if not torch.is_tensor(xb):
            xb = torch.as_tensor(xb)
        if not torch.is_tensor(yb):
            yb = torch.as_tensor(yb)
        xb = xb.view(xb.shape[0], -1)
        if input_dim is None:
            input_dim = xb.shape[1]
        if num_classes is None:
            num_classes = int(yb.max().item()) + 1
    return int(input_dim), int(num_classes)


@torch.no_grad()
def _compute_mean_std_and_class_means(train_loader, input_dim: int, num_classes: int, device: torch.device):
    n = 0
    sx = torch.zeros(input_dim, dtype=torch.float64)
    sx2 = torch.zeros(input_dim, dtype=torch.float64)
    class_sum = torch.zeros(num_classes, input_dim, dtype=torch.float64)
    class_count = torch.zeros(num_classes, dtype=torch.int64)

    for xb, yb in train_loader:
        if not torch.is_tensor(xb):
            xb = torch.as_tensor(xb)
        if not torch.is_tensor(yb):
            yb = torch.as_tensor(yb)
        xb = xb.view(xb.shape[0], -1).to(dtype=torch.float64, device="cpu")
        yb = yb.view(-1).to(dtype=torch.long, device="cpu")
        n_b = xb.shape[0]
        n += n_b
        sx += xb.sum(dim=0)
        sx2 += (xb * xb).sum(dim=0)

        if yb.numel() == n_b:
            class_sum.index_add_(0, yb, xb)
            ones = torch.ones_like(yb, dtype=torch.int64)
            class_count.index_add_(0, yb, ones)

    if n <= 0:
        mean = torch.zeros(input_dim, dtype=torch.float32)
        std = torch.ones(input_dim, dtype=torch.float32)
        mu_raw = torch.zeros(num_classes, input_dim, dtype=torch.float32)
        class_count_f = torch.ones(num_classes, dtype=torch.float32)
    else:
        mean = (sx / n).to(dtype=torch.float32)
        var = (sx2 / n) - (mean.to(torch.float64) ** 2)
        var = torch.clamp(var, min=0.0)
        std = torch.sqrt(var.to(torch.float32) + 1e-6)

        denom = torch.clamp(class_count, min=1).to(dtype=torch.float64).unsqueeze(1)
        mu_raw = (class_sum / denom).to(dtype=torch.float32)
        class_count_f = class_count.to(dtype=torch.float32)
        class_count_f = torch.clamp(class_count_f, min=1.0)

    mean = mean.to(device=device)
    std = std.to(device=device)
    mu_raw = mu_raw.to(device=device)
    class_count_f = class_count_f.to(device=device)
    return mean, std, mu_raw, class_count_f


@torch.no_grad()
def _compute_within_class_covariance(train_loader, mean: torch.Tensor, std: torch.Tensor, mu_raw: torch.Tensor, input_dim: int, num_classes: int):
    device = mean.device
    invstd = (1.0 / torch.clamp(std, min=1e-6)).to(dtype=torch.float64)
    mean64 = mean.to(dtype=torch.float64)
    mu_norm = ((mu_raw - mean) / torch.clamp(std, min=1e-6)).to(dtype=torch.float64)

    sw = torch.zeros(input_dim, input_dim, dtype=torch.float64, device=device)
    n_total = 0
    for xb, yb in train_loader:
        if not torch.is_tensor(xb):
            xb = torch.as_tensor(xb)
        if not torch.is_tensor(yb):
            yb = torch.as_tensor(yb)
        xb = xb.view(xb.shape[0], -1).to(dtype=torch.float64, device=device)
        yb = yb.view(-1).to(dtype=torch.long, device=device)
        x_norm = (xb - mean64) * invstd
        mu_y = mu_norm.index_select(0, yb)
        diff = x_norm - mu_y
        sw += diff.t().mm(diff)
        n_total += xb.shape[0]

    denom = max(n_total - num_classes, 1)
    cov = sw / float(denom)
    cov = 0.5 * (cov + cov.t())
    return cov.to(dtype=torch.float64)


@torch.no_grad()
def _fit_shrinkage_lda(cov_within: torch.Tensor, mu_raw: torch.Tensor, mean: torch.Tensor, std: torch.Tensor, class_prior: torch.Tensor, shrink: float = 0.2):
    device = mean.device
    d = mean.numel()
    invstd = 1.0 / torch.clamp(std, min=1e-6)
    mu_norm = (mu_raw - mean) * invstd

    cov = cov_within
    tr = torch.trace(cov)
    if not torch.isfinite(tr) or tr.item() <= 0:
        tr = torch.tensor(float(d), dtype=torch.float64, device=device)
    scale = (tr / float(d)).clamp(min=1e-8)
    eye = torch.eye(d, dtype=torch.float64, device=device)
    cov_reg = (1.0 - shrink) * cov + shrink * scale * eye
    cov_reg = cov_reg + 1e-4 * eye

    chol = torch.linalg.cholesky(cov_reg)
    rhs = mu_norm.t().to(dtype=torch.float64)
    W = torch.cholesky_solve(rhs, chol).to(dtype=torch.float32)
    wT = W.t().to(dtype=torch.float32)
    mu32 = mu_norm.to(dtype=torch.float32)
    bias = -0.5 * torch.sum(mu32 * wT, dim=1)
    prior = torch.clamp(class_prior, min=1e-12)
    bias = bias + torch.log(prior)
    return W.to(device=device), bias.to(device=device)


class _MLPBackbone(nn.Module):
    def __init__(self, input_dim: int, num_classes: int, hidden_dim: int, dropout: float):
        super().__init__()
        self.fc1 = nn.Linear(input_dim, hidden_dim)
        self.ln1 = nn.LayerNorm(hidden_dim)
        self.fc2 = nn.Linear(hidden_dim, hidden_dim)
        self.ln2 = nn.LayerNorm(hidden_dim)
        self.fc3 = nn.Linear(hidden_dim, num_classes)
        self.dropout = float(dropout)

    def forward(self, x):
        x = self.fc1(x)
        x = self.ln1(x)
        x = F.gelu(x)
        if self.dropout > 0:
            x = F.dropout(x, p=self.dropout, training=self.training)
        r = self.fc2(x)
        r = self.ln2(r)
        r = F.gelu(r)
        if self.dropout > 0:
            r = F.dropout(r, p=self.dropout, training=self.training)
        x = x + r
        x = self.fc3(x)
        return x


class _HybridClassifier(nn.Module):
    def __init__(
        self,
        mlp: nn.Module,
        mean: torch.Tensor,
        std: torch.Tensor,
        cent_W: torch.Tensor,
        cent_b: torch.Tensor,
        lda_W: torch.Tensor,
        lda_b: torch.Tensor,
        comb_w: torch.Tensor,
        comb_scale: torch.Tensor,
    ):
        super().__init__()
        self.mlp = mlp
        self.register_buffer("mean", mean)
        self.register_buffer("invstd", 1.0 / torch.clamp(std, min=1e-6))
        self.register_buffer("cent_W", cent_W)
        self.register_buffer("cent_b", cent_b)
        self.register_buffer("lda_W", lda_W)
        self.register_buffer("lda_b", lda_b)
        self.register_buffer("comb_w", comb_w)
        self.register_buffer("comb_scale", comb_scale)

    def forward(self, x):
        if not torch.is_tensor(x):
            x = torch.as_tensor(x)
        x = x.view(x.shape[0], -1)
        x = x.to(dtype=torch.float32, device=self.mean.device)
        xn = (x - self.mean) * self.invstd

        w = self.comb_w
        s = self.comb_scale

        out = None

        if w[0].item() != 0.0:
            lm = self.mlp(xn) * s[0]
            out = lm * w[0]

        if w[1].item() != 0.0:
            lc = (xn.matmul(self.cent_W.t()) + self.cent_b) * s[1]
            out = lc * w[1] if out is None else out + lc * w[1]

        if w[2].item() != 0.0:
            ll = (xn.matmul(self.lda_W) + self.lda_b) * s[2]
            out = ll * w[2] if out is None else out + ll * w[2]

        if out is None:
            out = self.mlp(xn)

        return out


class _EMA:
    def __init__(self, model: nn.Module, decay: float = 0.995):
        self.decay = float(decay)
        self.shadow = {}
        self.backup = {}
        for name, p in model.named_parameters():
            if p.requires_grad:
                self.shadow[name] = p.detach().clone()

    @torch.no_grad()
    def update(self, model: nn.Module):
        d = self.decay
        for name, p in model.named_parameters():
            if p.requires_grad and name in self.shadow:
                self.shadow[name].mul_(d).add_(p.detach(), alpha=(1.0 - d))

    @torch.no_grad()
    def apply(self, model: nn.Module):
        self.backup = {}
        for name, p in model.named_parameters():
            if p.requires_grad and name in self.shadow:
                self.backup[name] = p.detach().clone()
                p.copy_(self.shadow[name])

    @torch.no_grad()
    def restore(self, model: nn.Module):
        for name, p in model.named_parameters():
            if p.requires_grad and name in self.backup:
                p.copy_(self.backup[name])
        self.backup = {}


@torch.no_grad()
def _eval_logits_on_loader(mlp: nn.Module, val_loader, mean: torch.Tensor, std: torch.Tensor, cent_W: torch.Tensor, cent_b: torch.Tensor, lda_W: torch.Tensor, lda_b: torch.Tensor, device: torch.device):
    invstd = 1.0 / torch.clamp(std, min=1e-6)
    mlp.eval()

    all_lm = []
    all_lc = []
    all_ll = []
    all_y = []

    for xb, yb in val_loader:
        if not torch.is_tensor(xb):
            xb = torch.as_tensor(xb)
        if not torch.is_tensor(yb):
            yb = torch.as_tensor(yb)
        xb = xb.view(xb.shape[0], -1).to(dtype=torch.float32, device=device)
        yb = yb.view(-1).to(dtype=torch.long, device=device)
        xn = (xb - mean) * invstd

        lm = mlp(xn)
        lc = xn.matmul(cent_W.t()) + cent_b
        ll = xn.matmul(lda_W) + lda_b

        all_lm.append(lm.cpu())
        all_lc.append(lc.cpu())
        all_ll.append(ll.cpu())
        all_y.append(yb.cpu())

    lm = torch.cat(all_lm, dim=0)
    lc = torch.cat(all_lc, dim=0)
    ll = torch.cat(all_ll, dim=0)
    y = torch.cat(all_y, dim=0)
    return lm, lc, ll, y


@torch.no_grad()
def _acc_from_logits(logits: torch.Tensor, y: torch.Tensor) -> float:
    pred = logits.argmax(dim=1)
    return (pred == y).to(torch.float32).mean().item()


class Solution:
    def solve(self, train_loader, val_loader, metadata: dict = None) -> torch.nn.Module:
        torch.manual_seed(0)

        device_str = "cpu"
        if metadata is not None:
            device_str = metadata.get("device", "cpu")
        device = torch.device(device_str)

        input_dim, num_classes = _infer_dims(train_loader, metadata)
        param_limit = 200000 if metadata is None else int(metadata.get("param_limit", 200000))

        hidden_dim = 256
        dropout = 0.10

        mlp = _MLPBackbone(input_dim, num_classes, hidden_dim, dropout=dropout)
        if _count_params_all(mlp) > param_limit:
            for h in range(hidden_dim, 31, -8):
                mlp_try = _MLPBackbone(input_dim, num_classes, h, dropout=dropout)
                if _count_params_all(mlp_try) <= param_limit:
                    mlp = mlp_try
                    hidden_dim = h
                    break
            if _count_params_all(mlp) > param_limit:
                mlp = _MLPBackbone(input_dim, num_classes, 64, dropout=dropout)

        mlp.to(device)

        mean, std, mu_raw, class_count = _compute_mean_std_and_class_means(train_loader, input_dim, num_classes, device)
        class_prior = class_count / torch.clamp(class_count.sum(), min=1.0)

        mu_norm = (mu_raw - mean) / torch.clamp(std, min=1e-6)
        cent_W = (2.0 * mu_norm).to(dtype=torch.float32, device=device)
        cent_b = (-(mu_norm * mu_norm).sum(dim=1)).to(dtype=torch.float32, device=device)

        cov_within = _compute_within_class_covariance(train_loader, mean, std, mu_raw, input_dim, num_classes)
        lda_W, lda_b = _fit_shrinkage_lda(cov_within, mu_raw, mean, std, class_prior, shrink=0.2)
        lda_W = lda_W.to(dtype=torch.float32, device=device)
        lda_b = lda_b.to(dtype=torch.float32, device=device)

        epochs = 80
        lr = 2.5e-3
        weight_decay = 2e-4
        label_smoothing = 0.10
        mixup_alpha = 0.20

        optimizer = torch.optim.AdamW(mlp.parameters(), lr=lr, weight_decay=weight_decay, betas=(0.9, 0.99))
        scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=max(1, epochs))

        criterion = nn.CrossEntropyLoss(label_smoothing=label_smoothing)

        ema = _EMA(mlp, decay=0.995)

        best_state = copy.deepcopy(mlp.state_dict())
        best_acc = -1.0
        patience = 20
        bad = 0

        invstd = 1.0 / torch.clamp(std, min=1e-6)

        for epoch in range(epochs):
            mlp.train()
            for xb, yb in train_loader:
                if not torch.is_tensor(xb):
                    xb = torch.as_tensor(xb)
                if not torch.is_tensor(yb):
                    yb = torch.as_tensor(yb)
                xb = xb.view(xb.shape[0], -1).to(dtype=torch.float32, device=device)
                yb = yb.view(-1).to(dtype=torch.long, device=device)

                xn = (xb - mean) * invstd

                do_mixup = (mixup_alpha > 0.0) and (epoch < int(0.85 * epochs)) and (xn.shape[0] >= 2)
                if do_mixup:
                    lam = torch.distributions.Beta(mixup_alpha, mixup_alpha).sample().item()
                    idx = torch.randperm(xn.shape[0], device=device)
                    x_mix = xn.mul(lam).add(xn.index_select(0, idx), alpha=(1.0 - lam))
                    y_a = yb
                    y_b = yb.index_select(0, idx)
                    logits = mlp(x_mix)
                    loss = lam * criterion(logits, y_a) + (1.0 - lam) * criterion(logits, y_b)
                else:
                    logits = mlp(xn)
                    loss = criterion(logits, yb)

                optimizer.zero_grad(set_to_none=True)
                loss.backward()
                torch.nn.utils.clip_grad_norm_(mlp.parameters(), 1.0)
                optimizer.step()
                ema.update(mlp)

            scheduler.step()

            if val_loader is not None and ((epoch + 1) % 2 == 0 or epoch == epochs - 1):
                ema.apply(mlp)
                mlp.eval()
                correct = 0
                total = 0
                with torch.no_grad():
                    for xb, yb in val_loader:
                        if not torch.is_tensor(xb):
                            xb = torch.as_tensor(xb)
                        if not torch.is_tensor(yb):
                            yb = torch.as_tensor(yb)
                        xb = xb.view(xb.shape[0], -1).to(dtype=torch.float32, device=device)
                        yb = yb.view(-1).to(dtype=torch.long, device=device)
                        xn = (xb - mean) * invstd
                        out = mlp(xn)
                        pred = out.argmax(dim=1)
                        correct += (pred == yb).sum().item()
                        total += yb.numel()
                acc = correct / max(total, 1)
                ema.restore(mlp)

                if acc > best_acc + 1e-6:
                    best_acc = acc
                    ema.apply(mlp)
                    best_state = copy.deepcopy(mlp.state_dict())
                    ema.restore(mlp)
                    bad = 0
                else:
                    bad += 1
                    if bad >= patience:
                        break

        mlp.load_state_dict(best_state, strict=True)
        ema.apply(mlp)

        comb_w = torch.tensor([1.0, 0.0, 0.0], dtype=torch.float32, device=device)
        comb_scale = torch.tensor([1.0, 1.0, 1.0], dtype=torch.float32, device=device)

        if val_loader is not None:
            lm, lc, ll, yv = _eval_logits_on_loader(mlp, val_loader, mean, std, cent_W, cent_b, lda_W, lda_b, device=device)
            lm = lm.to(dtype=torch.float32)
            lc = lc.to(dtype=torch.float32)
            ll = ll.to(dtype=torch.float32)

            def _std_safe(t):
                s = t.float().std().item()
                if not math.isfinite(s) or s < 1e-6:
                    return 1.0
                return s

            sm = 1.0 / _std_safe(lm)
            sc = 1.0 / _std_safe(lc)
            sl = 1.0 / _std_safe(ll)

            lm_s = lm * sm
            lc_s = lc * sc
            ll_s = ll * sl

            best = -1.0
            best_w = (1.0, 0.0, 0.0)

            step = 0.1
            nsteps = int(1.0 / step + 1e-9)
            for i in range(nsteps + 1):
                wm = i * step
                for j in range(nsteps + 1 - i):
                    wc = j * step
                    wl = 1.0 - wm - wc
                    if wl < -1e-9:
                        continue
                    logits = lm_s.mul(wm).add(lc_s, alpha=wc).add(ll_s, alpha=wl)
                    acc = _acc_from_logits(logits, yv)
                    if acc > best + 1e-9:
                        best = acc
                        best_w = (wm, wc, wl)

            comb_w = torch.tensor(best_w, dtype=torch.float32, device=device)
            comb_scale = torch.tensor([sm, sc, sl], dtype=torch.float32, device=device)

        model = _HybridClassifier(
            mlp=mlp,
            mean=mean.detach(),
            std=std.detach(),
            cent_W=cent_W.detach(),
            cent_b=cent_b.detach(),
            lda_W=lda_W.detach(),
            lda_b=lda_b.detach(),
            comb_w=comb_w.detach(),
            comb_scale=comb_scale.detach(),
        ).to(device)

        return model