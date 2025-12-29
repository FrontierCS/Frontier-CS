import math
import copy
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F


class _ResidualLinearBlock(nn.Module):
    def __init__(self, width: int, dropout: float):
        super().__init__()
        self.ln = nn.LayerNorm(width)
        self.fc = nn.Linear(width, width, bias=True)
        self.drop = nn.Dropout(dropout) if dropout and dropout > 0 else nn.Identity()

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        y = self.ln(x)
        y = F.gelu(y)
        y = self.fc(y)
        y = self.drop(y)
        return x + y


class _MLPWithCentroids(nn.Module):
    def __init__(
        self,
        input_dim: int,
        num_classes: int,
        width: int,
        num_blocks: int,
        dropout: float,
        x_mean: torch.Tensor,
        x_invstd: torch.Tensor,
        centroids: torch.Tensor,
        centroid_temp: float = 10.0,
    ):
        super().__init__()
        self.input_dim = input_dim
        self.num_classes = num_classes
        self.width = width
        self.num_blocks = num_blocks

        self.register_buffer("x_mean", x_mean.detach().clone())
        self.register_buffer("x_invstd", x_invstd.detach().clone())

        self.register_buffer("centroids", centroids.detach().clone())
        self.register_buffer("centroid_temp", torch.tensor(float(centroid_temp), dtype=torch.float32))

        self.centroid_scale = nn.Parameter(torch.tensor(1.0, dtype=torch.float32))

        self.in_ln = nn.LayerNorm(input_dim)
        self.stem = nn.Linear(input_dim, width, bias=True)
        self.blocks = nn.ModuleList([_ResidualLinearBlock(width, dropout) for _ in range(num_blocks)])
        self.out_ln = nn.LayerNorm(width)
        self.head = nn.Linear(width, num_classes, bias=True)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = x.to(dtype=torch.float32)
        x_std = (x - self.x_mean) * self.x_invstd

        x_norm = F.normalize(x_std, dim=-1)
        cent_logits = self.centroid_temp * (x_norm @ self.centroids.t())

        h = self.in_ln(x_std)
        h = self.stem(h)
        for blk in self.blocks:
            h = blk(h)
        h = self.out_ln(h)
        logits = self.head(h)

        logits = logits + self.centroid_scale * cent_logits
        return logits


class _EMA:
    def __init__(self, model: nn.Module, decay: float = 0.995):
        self.decay = float(decay)
        self.shadow = {}
        self._backup = None
        with torch.no_grad():
            for name, p in model.named_parameters():
                if p.requires_grad:
                    self.shadow[name] = p.detach().clone()

    @torch.no_grad()
    def update(self, model: nn.Module):
        d = self.decay
        for name, p in model.named_parameters():
            if not p.requires_grad:
                continue
            self.shadow[name].mul_(d).add_(p.detach(), alpha=(1.0 - d))

    @torch.no_grad()
    def apply_to(self, model: nn.Module):
        self._backup = {}
        for name, p in model.named_parameters():
            if not p.requires_grad:
                continue
            self._backup[name] = p.detach().clone()
            p.copy_(self.shadow[name])

    @torch.no_grad()
    def restore(self, model: nn.Module):
        if self._backup is None:
            return
        for name, p in model.named_parameters():
            if not p.requires_grad:
                continue
            p.copy_(self._backup[name])
        self._backup = None


def _param_count_formula(input_dim: int, num_classes: int, width: int, num_blocks: int) -> int:
    # Trainable params:
    # centroid_scale: 1
    # in_ln: 2*input_dim
    # stem: width*input_dim + width
    # each block: ln(2*width) + linear(width*width + width) = width*width + 3*width
    # out_ln: 2*width
    # head: width*num_classes + num_classes
    return (
        1
        + 2 * input_dim
        + width * input_dim
        + width
        + num_blocks * (width * width + 3 * width)
        + 2 * width
        + width * num_classes
        + num_classes
    )


def _collect_all(loader):
    xs = []
    ys = []
    for batch in loader:
        if isinstance(batch, (list, tuple)) and len(batch) >= 2:
            x, y = batch[0], batch[1]
        else:
            continue
        if not torch.is_tensor(x):
            x = torch.as_tensor(x)
        if not torch.is_tensor(y):
            y = torch.as_tensor(y)
        xs.append(x.detach().cpu())
        ys.append(y.detach().cpu())
    x = torch.cat(xs, dim=0).contiguous()
    y = torch.cat(ys, dim=0).contiguous()
    if x.dtype != torch.float32:
        x = x.to(torch.float32)
    if y.dtype != torch.long:
        y = y.to(torch.long)
    return x, y


def _compute_mean_invstd(x: torch.Tensor, eps: float = 1e-5):
    mean = x.mean(dim=0)
    var = x.var(dim=0, unbiased=False)
    invstd = torch.rsqrt(var + eps)
    return mean, invstd


def _compute_centroids(x_std: torch.Tensor, y: torch.Tensor, num_classes: int):
    input_dim = x_std.shape[1]
    cent = torch.zeros(num_classes, input_dim, dtype=torch.float32)
    cnt = torch.zeros(num_classes, dtype=torch.float32)
    for c in range(num_classes):
        mask = (y == c)
        if mask.any():
            xc = x_std[mask]
            cent[c] = xc.mean(dim=0)
            cnt[c] = float(xc.shape[0])
        else:
            cent[c].zero_()
            cnt[c] = 1.0
    cent = F.normalize(cent, dim=-1)
    return cent


@torch.no_grad()
def _accuracy(model: nn.Module, x: torch.Tensor, y: torch.Tensor, batch_size: int = 1024) -> float:
    model.eval()
    n = x.shape[0]
    correct = 0
    for i in range(0, n, batch_size):
        xb = x[i : i + batch_size]
        yb = y[i : i + batch_size]
        logits = model(xb)
        pred = logits.argmax(dim=1)
        correct += (pred == yb).sum().item()
    return correct / max(1, n)


class Solution:
    def solve(self, train_loader, val_loader, metadata: dict = None) -> torch.nn.Module:
        if metadata is None:
            metadata = {}
        device = metadata.get("device", "cpu")
        input_dim = int(metadata.get("input_dim", 384))
        num_classes = int(metadata.get("num_classes", 128))
        param_limit = int(metadata.get("param_limit", 5_000_000))

        try:
            torch.set_num_threads(min(8, torch.get_num_threads()))
        except Exception:
            pass

        torch.manual_seed(0)
        np.random.seed(0)

        x_train, y_train = _collect_all(train_loader)
        if val_loader is not None:
            x_val, y_val = _collect_all(val_loader)
        else:
            x_val, y_val = None, None

        if x_train.shape[1] != input_dim:
            input_dim = int(x_train.shape[1])
        if num_classes <= int(y_train.max().item()) + 1:
            num_classes = int(y_train.max().item()) + 1

        x_mean, x_invstd = _compute_mean_invstd(x_train)
        x_train_std = (x_train - x_mean) * x_invstd
        centroids = _compute_centroids(x_train_std, y_train, num_classes=num_classes)

        # Select (width, blocks) close to param_limit
        best = None
        best_params = -1
        for b in range(3, 13):
            for w in range(256, 2049, 16):
                p = _param_count_formula(input_dim, num_classes, w, b)
                if p <= param_limit and p > best_params:
                    best_params = p
                    best = (w, b)
        if best is None:
            # Fallback minimal
            best = (256, 3)

        width, num_blocks = best

        dropout = 0.10
        model = _MLPWithCentroids(
            input_dim=input_dim,
            num_classes=num_classes,
            width=width,
            num_blocks=num_blocks,
            dropout=dropout,
            x_mean=x_mean.to(torch.float32),
            x_invstd=x_invstd.to(torch.float32),
            centroids=centroids.to(torch.float32),
            centroid_temp=10.0,
        ).to(device)

        # Final safety check
        param_count = sum(p.numel() for p in model.parameters() if p.requires_grad)
        if param_count > param_limit:
            # Reduce width until within limit
            w = width
            b = num_blocks
            while w > 128 and sum(p.numel() for p in model.parameters() if p.requires_grad) > param_limit:
                w -= 16
                model = _MLPWithCentroids(
                    input_dim=input_dim,
                    num_classes=num_classes,
                    width=w,
                    num_blocks=b,
                    dropout=dropout,
                    x_mean=x_mean.to(torch.float32),
                    x_invstd=x_invstd.to(torch.float32),
                    centroids=centroids.to(torch.float32),
                    centroid_temp=10.0,
                ).to(device)

        # Training setup
        criterion = nn.CrossEntropyLoss(label_smoothing=0.05)
        # Exclude LayerNorm bias/weight and centroid_scale from weight decay
        decay, no_decay = [], []
        for name, p in model.named_parameters():
            if not p.requires_grad:
                continue
            if p.ndim == 1 or "ln" in name.lower() or "layernorm" in name.lower() or name.endswith(".bias") or name == "centroid_scale":
                no_decay.append(p)
            else:
                decay.append(p)

        optimizer = torch.optim.AdamW(
            [{"params": decay, "weight_decay": 1e-2}, {"params": no_decay, "weight_decay": 0.0}],
            lr=2.5e-3,
            betas=(0.9, 0.99),
        )

        ema = _EMA(model, decay=0.995)

        n_train = x_train.shape[0]
        if x_val is not None:
            n_val = x_val.shape[0]
        else:
            n_val = 0

        batch_size = 512 if n_train >= 512 else max(64, int(2 ** math.floor(math.log2(max(1, n_train)))))
        max_epochs = 220
        warmup_epochs = 10
        lr_max = 2.5e-3
        lr_min = 2.0e-4
        patience = 45
        min_epochs = 60
        mixup_alpha = 0.2

        best_state = None
        best_acc = -1.0
        best_loss = float("inf")
        bad_epochs = 0

        x_train = x_train.to(device)
        y_train = y_train.to(device)
        if x_val is not None:
            x_val = x_val.to(device)
            y_val = y_val.to(device)

        for epoch in range(max_epochs):
            if epoch < warmup_epochs:
                lr = lr_max * float(epoch + 1) / float(warmup_epochs)
            else:
                t = float(epoch - warmup_epochs) / float(max(1, max_epochs - warmup_epochs - 1))
                lr = lr_min + 0.5 * (lr_max - lr_min) * (1.0 + math.cos(math.pi * t))
            for pg in optimizer.param_groups:
                pg["lr"] = lr

            model.train()
            perm = torch.randperm(n_train, device=device)
            use_mixup = epoch < int(0.85 * max_epochs)
            total_loss = 0.0

            for i in range(0, n_train, batch_size):
                idx = perm[i : i + batch_size]
                xb = x_train.index_select(0, idx)
                yb = y_train.index_select(0, idx)

                if use_mixup and mixup_alpha > 0:
                    lam = np.random.beta(mixup_alpha, mixup_alpha)
                    lam = float(lam)
                    perm2 = torch.randperm(xb.shape[0], device=device)
                    xb2 = xb.index_select(0, perm2)
                    yb2 = yb.index_select(0, perm2)
                    xm = xb.mul(lam).add(xb2, alpha=(1.0 - lam))
                    logits = model(xm)
                    loss = lam * criterion(logits, yb) + (1.0 - lam) * criterion(logits, yb2)
                else:
                    logits = model(xb)
                    loss = criterion(logits, yb)

                optimizer.zero_grad(set_to_none=True)
                loss.backward()
                torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
                optimizer.step()
                ema.update(model)

                total_loss += float(loss.detach().cpu().item()) * xb.shape[0]

            avg_train_loss = total_loss / max(1, n_train)

            if x_val is not None and n_val > 0:
                ema.apply_to(model)
                with torch.no_grad():
                    model.eval()
                    logits_v = model(x_val)
                    val_loss = float(criterion(logits_v, y_val).detach().cpu().item())
                    val_acc = float((logits_v.argmax(dim=1) == y_val).float().mean().detach().cpu().item())
                state = copy.deepcopy(model.state_dict())
                ema.restore(model)

                improved = (val_acc > best_acc + 1e-4) or (abs(val_acc - best_acc) <= 1e-4 and val_loss < best_loss - 1e-4)
                if improved:
                    best_acc = val_acc
                    best_loss = val_loss
                    best_state = state
                    bad_epochs = 0
                else:
                    bad_epochs += 1

                if epoch >= min_epochs and bad_epochs >= patience:
                    break
            else:
                # No validation: keep EMA weights at end
                pass

        if best_state is not None:
            model.load_state_dict(best_state)

        # Optional short fine-tune on train+val if val exists
        if x_val is not None and n_val > 0:
            x_all = torch.cat([x_train, x_val], dim=0)
            y_all = torch.cat([y_train, y_val], dim=0)
            n_all = x_all.shape[0]
            ft_epochs = 25
            ft_lr = 7.5e-4
            for pg in optimizer.param_groups:
                pg["lr"] = ft_lr
            for epoch in range(ft_epochs):
                model.train()
                perm = torch.randperm(n_all, device=device)
                for i in range(0, n_all, batch_size):
                    idx = perm[i : i + batch_size]
                    xb = x_all.index_select(0, idx)
                    yb = y_all.index_select(0, idx)
                    logits = model(xb)
                    loss = criterion(logits, yb)
                    optimizer.zero_grad(set_to_none=True)
                    loss.backward()
                    torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
                    optimizer.step()

        model.eval()
        return model.to(device)