import math
import copy
import torch
import torch.nn as nn


class _EMA:
    def __init__(self, model: nn.Module, decay: float = 0.999):
        self.decay = float(decay)
        self.params = [p for p in model.parameters() if p.requires_grad]
        self.shadow = [p.detach().clone() for p in self.params]
        self._backup = None

    @torch.no_grad()
    def update(self):
        d = self.decay
        for s, p in zip(self.shadow, self.params):
            s.mul_(d).add_(p.detach(), alpha=1.0 - d)

    @torch.no_grad()
    def apply_shadow(self):
        self._backup = [p.detach().clone() for p in self.params]
        for p, s in zip(self.params, self.shadow):
            p.copy_(s)

    @torch.no_grad()
    def restore(self):
        if self._backup is None:
            return
        for p, b in zip(self.params, self._backup):
            p.copy_(b)
        self._backup = None


class _NormalizedLinear(nn.Module):
    def __init__(self, input_dim: int, num_classes: int, mean: torch.Tensor, std: torch.Tensor):
        super().__init__()
        self.register_buffer("mean", mean.detach().clone().view(1, -1))
        self.register_buffer("std", std.detach().clone().view(1, -1))
        self.linear = nn.Linear(input_dim, num_classes)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = x.float()
        x = (x - self.mean) / self.std
        return self.linear(x)


class _MLPBlock(nn.Module):
    def __init__(self, width: int, dropout: float):
        super().__init__()
        self.norm = nn.LayerNorm(width)
        self.fc1 = nn.Linear(width, width, bias=True)
        self.act = nn.GELU()
        self.drop = nn.Dropout(dropout) if dropout and dropout > 0 else nn.Identity()
        self.fc2 = nn.Linear(width, width, bias=True)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        h = self.norm(x)
        h = self.fc1(h)
        h = self.act(h)
        h = self.drop(h)
        h = self.fc2(h)
        h = self.drop(h)
        return x + h


class _ResMLPClassifier(nn.Module):
    def __init__(self, input_dim: int, num_classes: int, mean: torch.Tensor, std: torch.Tensor, width: int, blocks: int, dropout: float):
        super().__init__()
        self.register_buffer("mean", mean.detach().clone().view(1, -1))
        self.register_buffer("std", std.detach().clone().view(1, -1))
        self.norm_in = nn.LayerNorm(input_dim)
        self.fc_in = nn.Linear(input_dim, width, bias=True)
        self.blocks = nn.ModuleList([_MLPBlock(width, dropout) for _ in range(blocks)])
        self.norm_out = nn.LayerNorm(width)
        self.fc_out = nn.Linear(width, num_classes, bias=True)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = x.float()
        x = (x - self.mean) / self.std
        x = self.norm_in(x)
        x = self.fc_in(x)
        for b in self.blocks:
            x = b(x)
        x = self.norm_out(x)
        x = self.fc_out(x)
        return x


def _gather_from_loader(loader, device: str):
    xs = []
    ys = []
    for xb, yb in loader:
        xs.append(xb.to(device=device, dtype=torch.float32))
        ys.append(yb.to(device=device, dtype=torch.long))
    X = torch.cat(xs, dim=0) if xs else torch.empty(0, device=device)
    y = torch.cat(ys, dim=0) if ys else torch.empty(0, device=device, dtype=torch.long)
    return X, y


def _accuracy_from_tensors(model: nn.Module, X: torch.Tensor, y: torch.Tensor, batch: int = 1024) -> float:
    model.eval()
    correct = 0
    total = int(y.numel())
    if total == 0:
        return 0.0
    with torch.inference_mode():
        for i in range(0, X.shape[0], batch):
            xb = X[i:i + batch]
            logits = model(xb)
            pred = logits.argmax(dim=1)
            correct += int((pred == y[i:i + batch]).sum().item())
    return float(correct) / float(total)


def _param_count(model: nn.Module) -> int:
    return sum(p.numel() for p in model.parameters() if p.requires_grad)


def _compute_mean_std(X: torch.Tensor):
    mean = X.mean(dim=0)
    var = X.var(dim=0, unbiased=False)
    std = torch.sqrt(var + 1e-6)
    std = std.clamp_min(1e-3)
    return mean, std


def _lda_weights_bias(Xn: torch.Tensor, y: torch.Tensor, num_classes: int, shrinkage: float = 0.08):
    # Xn already normalized (mean/std)
    device = Xn.device
    n, d = Xn.shape
    y = y.long()
    counts = torch.bincount(y, minlength=num_classes).clamp_min(1).to(device=device, dtype=torch.float64)
    mu = torch.zeros((num_classes, d), device=device, dtype=torch.float64)
    X64 = Xn.to(dtype=torch.float64)

    for k in range(num_classes):
        mask = (y == k)
        if mask.any():
            mu[k] = X64[mask].mean(dim=0)
        else:
            mu[k].zero_()

    mu_y = mu[y]
    resid = X64 - mu_y
    denom = max(1, n - num_classes)
    cov = (resid.transpose(0, 1) @ resid) / float(denom)
    cov = (cov + cov.transpose(0, 1)) * 0.5
    tr = cov.diag().sum()
    if float(tr.item()) <= 0.0:
        tr = torch.tensor(1.0, device=device, dtype=torch.float64)
    iso = (tr / float(d)) * torch.eye(d, device=device, dtype=torch.float64)
    cov = (1.0 - shrinkage) * cov + shrinkage * iso
    cov = cov + 1e-5 * torch.eye(d, device=device, dtype=torch.float64)

    L = torch.linalg.cholesky(cov)
    W = torch.cholesky_solve(mu.transpose(0, 1), L).transpose(0, 1)  # K x D
    b = -0.5 * (mu * W).sum(dim=1)

    priors = counts / counts.sum()
    logp = torch.log(priors)
    b = b + logp

    return W.to(dtype=torch.float32), b.to(dtype=torch.float32)


def _train_linear_lbfgs(model: _NormalizedLinear, X: torch.Tensor, y: torch.Tensor, max_iter: int = 120, wd: float = 2e-4):
    model.train()
    ce = nn.CrossEntropyLoss()
    opt = torch.optim.LBFGS(model.parameters(), lr=1.0, max_iter=max_iter, history_size=20, line_search_fn="strong_wolfe")

    def closure():
        opt.zero_grad(set_to_none=True)
        logits = model(X)
        loss = ce(logits, y)
        if wd and wd > 0:
            l2 = 0.0
            for p in model.parameters():
                if p.requires_grad:
                    l2 = l2 + (p.float() ** 2).sum()
            loss = loss + 0.5 * wd * l2
        loss.backward()
        return loss

    opt.step(closure)


def _mlp_param_estimate(input_dim: int, num_classes: int, width: int, blocks: int) -> int:
    # LayerNorm: 2*dim
    total = 0
    total += 2 * input_dim  # norm_in
    total += input_dim * width + width  # fc_in
    for _ in range(blocks):
        total += 2 * width  # block norm
        total += width * width + width  # fc1
        total += width * width + width  # fc2
    total += 2 * width  # norm_out
    total += width * num_classes + num_classes  # fc_out
    return int(total)


def _choose_width_under_limit(input_dim: int, num_classes: int, blocks: int, limit: int, margin: int = 8192):
    lo, hi = 64, 4096
    best = lo
    target = max(1, limit - margin)
    while lo <= hi:
        mid = (lo + hi) // 2
        p = _mlp_param_estimate(input_dim, num_classes, mid, blocks)
        if p <= target:
            best = mid
            lo = mid + 1
        else:
            hi = mid - 1
    return best


def _train_resmlp(
    model: _ResMLPClassifier,
    X_train: torch.Tensor,
    y_train: torch.Tensor,
    X_val: torch.Tensor,
    y_val: torch.Tensor,
    max_epochs: int = 260,
    batch_size: int = 256,
    lr: float = 2.5e-3,
    weight_decay: float = 1.5e-4,
    label_smoothing: float = 0.04,
    grad_clip: float = 1.0,
    patience: int = 40,
    dropout_noise_std: float = 0.00,
):
    device = X_train.device
    criterion = nn.CrossEntropyLoss(label_smoothing=label_smoothing)
    opt = torch.optim.AdamW(model.parameters(), lr=lr, betas=(0.9, 0.99), eps=1e-8, weight_decay=weight_decay)

    warmup = min(10, max(2, max_epochs // 20))

    def lr_factor(epoch: int):
        if epoch < warmup:
            return float(epoch + 1) / float(warmup)
        t = (epoch - warmup) / float(max(1, max_epochs - warmup))
        return 0.5 * (1.0 + math.cos(math.pi * t))

    sched = torch.optim.lr_scheduler.LambdaLR(opt, lr_lambda=lr_factor)

    ema = _EMA(model, decay=0.999)
    best_state = None
    best_acc = -1.0
    best_epoch = 0
    no_improve = 0

    n = X_train.shape[0]
    for epoch in range(max_epochs):
        model.train()
        perm = torch.randperm(n, device=device)
        total_loss = 0.0
        steps = 0

        for i in range(0, n, batch_size):
            idx = perm[i:i + batch_size]
            xb = X_train[idx]
            yb = y_train[idx]
            if dropout_noise_std and dropout_noise_std > 0:
                xb = xb + torch.randn_like(xb) * dropout_noise_std

            opt.zero_grad(set_to_none=True)
            logits = model(xb)
            loss = criterion(logits, yb)
            loss.backward()
            if grad_clip and grad_clip > 0:
                nn.utils.clip_grad_norm_(model.parameters(), grad_clip)
            opt.step()
            ema.update()

            total_loss += float(loss.detach().item())
            steps += 1

        sched.step()

        # Validation with EMA weights
        ema.apply_shadow()
        val_acc = _accuracy_from_tensors(model, X_val, y_val, batch=1024)
        ema.restore()

        if val_acc > best_acc + 1e-5:
            best_acc = val_acc
            best_epoch = epoch
            best_state = copy.deepcopy(model.state_dict())
            no_improve = 0
        else:
            no_improve += 1
            if no_improve >= patience:
                break

    if best_state is not None:
        model.load_state_dict(best_state)
    return model, float(best_acc), int(best_epoch)


def _finetune_on_combined(
    model: nn.Module,
    X_all: torch.Tensor,
    y_all: torch.Tensor,
    epochs: int = 20,
    batch_size: int = 256,
    lr: float = 2e-4,
    weight_decay: float = 1e-4,
    label_smoothing: float = 0.02,
    grad_clip: float = 1.0,
):
    model.train()
    criterion = nn.CrossEntropyLoss(label_smoothing=label_smoothing)
    opt = torch.optim.AdamW(model.parameters(), lr=lr, betas=(0.9, 0.99), eps=1e-8, weight_decay=weight_decay)
    n = X_all.shape[0]
    for _ in range(max(1, epochs)):
        perm = torch.randperm(n, device=X_all.device)
        for i in range(0, n, batch_size):
            idx = perm[i:i + batch_size]
            xb = X_all[idx]
            yb = y_all[idx]
            opt.zero_grad(set_to_none=True)
            logits = model(xb)
            loss = criterion(logits, yb)
            loss.backward()
            if grad_clip and grad_clip > 0:
                nn.utils.clip_grad_norm_(model.parameters(), grad_clip)
            opt.step()
    return model


class Solution:
    def solve(self, train_loader, val_loader, metadata: dict = None) -> torch.nn.Module:
        if metadata is None:
            metadata = {}
        device = metadata.get("device", "cpu")
        num_classes = int(metadata.get("num_classes", 128))
        input_dim = int(metadata.get("input_dim", 384))
        param_limit = int(metadata.get("param_limit", 5_000_000))

        torch.manual_seed(0)

        X_train, y_train = _gather_from_loader(train_loader, device=device)
        X_val, y_val = _gather_from_loader(val_loader, device=device)

        if X_train.numel() == 0:
            mean = torch.zeros((input_dim,), device=device, dtype=torch.float32)
            std = torch.ones((input_dim,), device=device, dtype=torch.float32)
            model = _NormalizedLinear(input_dim, num_classes, mean, std).to(device)
            model.eval()
            return model

        mean_tr, std_tr = _compute_mean_std(X_train)
        Xtr_n = (X_train - mean_tr) / std_tr
        Xval_n = (X_val - mean_tr) / std_tr if X_val.numel() else X_val

        # Linear (LDA init -> LBFGS fine-tune)
        W, b = _lda_weights_bias(Xtr_n, y_train, num_classes=num_classes, shrinkage=0.08)
        lin_model = _NormalizedLinear(input_dim, num_classes, mean_tr, std_tr).to(device)
        with torch.no_grad():
            lin_model.linear.weight.copy_(W)
            lin_model.linear.bias.copy_(b)

        try:
            _train_linear_lbfgs(lin_model, X_train, y_train, max_iter=120, wd=2e-4)
        except Exception:
            pass

        lin_val_acc = _accuracy_from_tensors(lin_model, X_val, y_val, batch=1024) if X_val.numel() else 0.0

        # If linear already excellent, train final linear on combined train+val and return
        if lin_val_acc >= 0.95 or X_val.numel() == 0:
            if X_val.numel():
                X_all = torch.cat([X_train, X_val], dim=0)
                y_all = torch.cat([y_train, y_val], dim=0)
            else:
                X_all, y_all = X_train, y_train

            mean_all, std_all = _compute_mean_std(X_all)
            Xall_n = (X_all - mean_all) / std_all
            W2, b2 = _lda_weights_bias(Xall_n, y_all, num_classes=num_classes, shrinkage=0.08)
            final_lin = _NormalizedLinear(input_dim, num_classes, mean_all, std_all).to(device)
            with torch.no_grad():
                final_lin.linear.weight.copy_(W2)
                final_lin.linear.bias.copy_(b2)
            try:
                _train_linear_lbfgs(final_lin, X_all, y_all, max_iter=160, wd=2e-4)
            except Exception:
                pass

            if _param_count(final_lin) > param_limit:
                final_lin = lin_model
            final_lin.eval()
            return final_lin

        # Train one ResMLP candidate (near limit)
        # Choose blocks by a simple heuristic; deeper often helps but keep compute sane.
        candidate_blocks = [2, 3, 4, 5]
        best_cfg = None
        for blocks in candidate_blocks:
            width = _choose_width_under_limit(input_dim, num_classes, blocks, param_limit, margin=12288)
            if width < 128:
                continue
            est = _mlp_param_estimate(input_dim, num_classes, width, blocks)
            if est <= param_limit:
                best_cfg = (blocks, width, est)
        if best_cfg is None:
            lin_model.eval()
            return lin_model

        blocks, width, _ = best_cfg
        mlp = _ResMLPClassifier(
            input_dim=input_dim,
            num_classes=num_classes,
            mean=mean_tr,
            std=std_tr,
            width=width,
            blocks=blocks,
            dropout=0.02,
        ).to(device)

        if _param_count(mlp) > param_limit:
            lin_model.eval()
            return lin_model

        mlp, mlp_val_acc, best_epoch = _train_resmlp(
            mlp,
            X_train=X_train,
            y_train=y_train,
            X_val=X_val,
            y_val=y_val,
            max_epochs=280,
            batch_size=256,
            lr=2.3e-3,
            weight_decay=1.5e-4,
            label_smoothing=0.04,
            grad_clip=1.0,
            patience=45,
            dropout_noise_std=0.0,
        )

        # Compare and pick best
        if mlp_val_acc + 1e-6 >= lin_val_acc:
            # light fine-tune on combined train+val
            if X_val.numel():
                X_all = torch.cat([X_train, X_val], dim=0)
                y_all = torch.cat([y_train, y_val], dim=0)
                mlp = _finetune_on_combined(
                    mlp,
                    X_all,
                    y_all,
                    epochs=18,
                    batch_size=256,
                    lr=1.8e-4,
                    weight_decay=1.2e-4,
                    label_smoothing=0.02,
                    grad_clip=1.0,
                )
            if _param_count(mlp) > param_limit:
                lin_model.eval()
                return lin_model
            mlp.eval()
            return mlp
        else:
            # train final linear on combined
            X_all = torch.cat([X_train, X_val], dim=0)
            y_all = torch.cat([y_train, y_val], dim=0)
            mean_all, std_all = _compute_mean_std(X_all)
            Xall_n = (X_all - mean_all) / std_all
            W2, b2 = _lda_weights_bias(Xall_n, y_all, num_classes=num_classes, shrinkage=0.08)
            final_lin = _NormalizedLinear(input_dim, num_classes, mean_all, std_all).to(device)
            with torch.no_grad():
                final_lin.linear.weight.copy_(W2)
                final_lin.linear.bias.copy_(b2)
            try:
                _train_linear_lbfgs(final_lin, X_all, y_all, max_iter=160, wd=2e-4)
            except Exception:
                pass
            if _param_count(final_lin) > param_limit:
                final_lin = lin_model
            final_lin.eval()
            return final_lin