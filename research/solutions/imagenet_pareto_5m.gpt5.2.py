import math
import os
import copy
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F


class _InputNorm(nn.Module):
    def __init__(self, mean: torch.Tensor, inv_std: torch.Tensor):
        super().__init__()
        self.register_buffer("mean", mean)
        self.register_buffer("inv_std", inv_std)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return (x - self.mean) * self.inv_std


class _ResidualBottleneckBlock(nn.Module):
    def __init__(self, dim: int, inner_dim: int, dropout: float = 0.1, gamma_init: float = 0.2):
        super().__init__()
        self.ln = nn.LayerNorm(dim, eps=1e-5)
        self.fc1 = nn.Linear(dim, inner_dim, bias=False)
        self.fc2 = nn.Linear(inner_dim, dim, bias=False)
        self.dropout = nn.Dropout(dropout)
        self.gamma = nn.Parameter(torch.full((dim,), float(gamma_init)))

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        h = self.ln(x)
        h = self.fc1(h)
        h = F.gelu(h, approximate="tanh")
        h = self.dropout(h)
        h = self.fc2(h)
        h = self.dropout(h)
        return x + h * self.gamma


class _MLPResNet(nn.Module):
    def __init__(
        self,
        input_dim: int,
        num_classes: int,
        width: int,
        depth: int,
        inner_dim: int,
        dropout: float,
        mean: torch.Tensor,
        inv_std: torch.Tensor,
    ):
        super().__init__()
        self.norm_in = _InputNorm(mean, inv_std)
        self.proj = nn.Linear(input_dim, width, bias=False)
        self.ln0 = nn.LayerNorm(width, eps=1e-5)
        self.blocks = nn.ModuleList(
            [_ResidualBottleneckBlock(width, inner_dim, dropout=dropout) for _ in range(depth)]
        )
        self.lnf = nn.LayerNorm(width, eps=1e-5)
        self.head = nn.Linear(width, num_classes, bias=True)

        self._init_weights()

    def _init_weights(self):
        for m in self.modules():
            if isinstance(m, nn.Linear):
                nn.init.kaiming_normal_(m.weight, a=math.sqrt(5))
                if m.bias is not None:
                    nn.init.zeros_(m.bias)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        if x.dim() > 2:
            x = x.view(x.size(0), -1)
        x = x.to(dtype=torch.float32)
        x = self.norm_in(x)
        x = self.proj(x)
        x = self.ln0(x)
        for blk in self.blocks:
            x = blk(x)
        x = self.lnf(x)
        x = self.head(x)
        return x


class _EMA:
    def __init__(self, model: nn.Module, decay: float = 0.995):
        self.decay = float(decay)
        self.ema_model = copy.deepcopy(model)
        self.ema_model.eval()
        for p in self.ema_model.parameters():
            p.requires_grad_(False)

    @torch.no_grad()
    def update(self, model: nn.Module):
        msd = model.state_dict()
        esd = self.ema_model.state_dict()
        for k, v in esd.items():
            sv = msd[k]
            if not torch.is_floating_point(v):
                v.copy_(sv)
            else:
                v.mul_(self.decay).add_(sv, alpha=1.0 - self.decay)

    def state_dict(self):
        return self.ema_model.state_dict()

    def load_state_dict(self, sd):
        self.ema_model.load_state_dict(sd, strict=True)

    def to(self, device: torch.device):
        self.ema_model.to(device)


def _count_trainable_params(model: nn.Module) -> int:
    return sum(p.numel() for p in model.parameters() if p.requires_grad)


def _collect_loader(loader):
    xs = []
    ys = []
    for a, b in loader:
        if a.dim() > 2:
            a = a.view(a.size(0), -1)
        xs.append(a.detach().cpu().to(torch.float32))
        ys.append(b.detach().cpu().to(torch.long))
    x = torch.cat(xs, dim=0) if xs else torch.empty(0)
    y = torch.cat(ys, dim=0) if ys else torch.empty(0, dtype=torch.long)
    return x, y


@torch.no_grad()
def _accuracy(model: nn.Module, x: torch.Tensor, y: torch.Tensor, batch_size: int = 512) -> float:
    model.eval()
    n = x.size(0)
    if n == 0:
        return 0.0
    correct = 0
    for i in range(0, n, batch_size):
        xb = x[i : i + batch_size]
        yb = y[i : i + batch_size]
        logits = model(xb)
        pred = logits.argmax(dim=1)
        correct += (pred == yb).sum().item()
    return correct / n


def _soft_cross_entropy(logits: torch.Tensor, soft_targets: torch.Tensor) -> torch.Tensor:
    logp = F.log_softmax(logits, dim=1)
    return -(soft_targets * logp).sum(dim=1).mean()


def _make_soft_targets(y: torch.Tensor, num_classes: int, smoothing: float) -> torch.Tensor:
    oh = F.one_hot(y, num_classes=num_classes).to(dtype=torch.float32)
    if smoothing > 0.0:
        oh = oh * (1.0 - smoothing) + (smoothing / float(num_classes))
    return oh


def _clone_state_dict(sd):
    out = {}
    for k, v in sd.items():
        out[k] = v.detach().clone()
    return out


class Solution:
    def solve(self, train_loader, val_loader, metadata: dict = None) -> torch.nn.Module:
        if metadata is None:
            metadata = {}
        input_dim = int(metadata.get("input_dim", 384))
        num_classes = int(metadata.get("num_classes", 128))
        param_limit = int(metadata.get("param_limit", 5_000_000))
        device = torch.device(metadata.get("device", "cpu"))

        nthreads = os.cpu_count() or 8
        torch.set_num_threads(min(8, max(1, nthreads)))

        seed = 12345
        torch.manual_seed(seed)
        np.random.seed(seed)

        x_train, y_train = _collect_loader(train_loader)
        x_val, y_val = _collect_loader(val_loader)

        if x_train.numel() == 0:
            mean = torch.zeros(1, input_dim, dtype=torch.float32)
            inv_std = torch.ones(1, input_dim, dtype=torch.float32)
        else:
            mean = x_train.mean(dim=0, keepdim=True)
            std = x_train.std(dim=0, unbiased=False, keepdim=True).clamp_min(1e-6)
            inv_std = 1.0 / std

        def estimate_params(width: int, depth: int, expansion: float = 0.5) -> int:
            inner = max(8, int(round(width * expansion / 8.0)) * 8)
            proj = input_dim * width
            ln0 = 2 * width
            lnf = 2 * width
            # each block: LN (2w) + fc1 (w*inner) + fc2 (inner*w) + gamma (w)
            blocks = depth * (2 * width + 2 * width * inner + width)
            head = width * num_classes + num_classes
            return int(proj + ln0 + blocks + lnf + head)

        best = None
        safety = 20_000
        effective_limit = max(1, param_limit - safety)

        for depth in range(4, 9):
            for width in range(512, 2049, 16):
                est = estimate_params(width, depth, expansion=0.5)
                if est <= effective_limit:
                    if best is None or est > best[0]:
                        best = (est, width, depth)

        if best is None:
            best = (0, 512, 4)

        _, width, depth = best
        inner_dim = max(8, int(round(width * 0.5 / 8.0)) * 8)

        model = _MLPResNet(
            input_dim=input_dim,
            num_classes=num_classes,
            width=width,
            depth=depth,
            inner_dim=inner_dim,
            dropout=0.10,
            mean=mean,
            inv_std=inv_std,
        ).to(device)

        while _count_trainable_params(model) > param_limit and width > 256:
            width -= 16
            inner_dim = max(8, int(round(width * 0.5 / 8.0)) * 8)
            model = _MLPResNet(
                input_dim=input_dim,
                num_classes=num_classes,
                width=width,
                depth=depth,
                inner_dim=inner_dim,
                dropout=0.10,
                mean=mean,
                inv_std=inv_std,
            ).to(device)

        x_train = x_train.to(device)
        y_train = y_train.to(device)
        x_val = x_val.to(device)
        y_val = y_val.to(device)

        train_bs = 256 if x_train.size(0) >= 256 else max(32, int(x_train.size(0)))
        val_bs = 512

        base_lr = 2.5e-3
        min_lr = 1.5e-4
        weight_decay = 0.06
        epochs = 220
        warmup_epochs = 6
        patience = 35
        mixup_alpha = 0.2
        smoothing = 0.08
        ema_decay = 0.995

        optimizer = torch.optim.AdamW(model.parameters(), lr=base_lr, weight_decay=weight_decay)
        steps_per_epoch = max(1, (x_train.size(0) + train_bs - 1) // train_bs)
        total_steps = epochs * steps_per_epoch
        warmup_steps = warmup_epochs * steps_per_epoch

        ema = _EMA(model, decay=ema_decay)
        ema.to(device)

        best_acc = -1.0
        best_sd = None
        bad = 0
        global_step = 0

        def set_lr(step: int):
            if step < warmup_steps:
                lr = base_lr * float(step + 1) / float(max(1, warmup_steps))
            else:
                denom = max(1, total_steps - warmup_steps)
                progress = float(step - warmup_steps) / float(denom)
                lr = min_lr + 0.5 * (base_lr - min_lr) * (1.0 + math.cos(math.pi * progress))
            for pg in optimizer.param_groups:
                pg["lr"] = lr

        for epoch in range(epochs):
            model.train()
            perm = torch.randperm(x_train.size(0), device=device)

            use_mixup = (epoch < int(epochs * 0.75))
            for si in range(0, x_train.size(0), train_bs):
                idx = perm[si : si + train_bs]
                xb = x_train[idx]
                yb = y_train[idx]

                if use_mixup and mixup_alpha > 0.0 and xb.size(0) >= 2:
                    lam = float(np.random.beta(mixup_alpha, mixup_alpha))
                    j = torch.randperm(xb.size(0), device=device)
                    xb2 = xb[j]
                    yb2 = yb[j]
                    xb = xb.mul(lam).add(xb2, alpha=(1.0 - lam))
                    y1 = _make_soft_targets(yb, num_classes, smoothing)
                    y2 = _make_soft_targets(yb2, num_classes, smoothing)
                    soft = y1.mul(lam).add(y2, alpha=(1.0 - lam))
                    logits = model(xb)
                    loss = _soft_cross_entropy(logits, soft)
                else:
                    logits = model(xb)
                    loss = F.cross_entropy(logits, yb, label_smoothing=smoothing)

                optimizer.zero_grad(set_to_none=True)
                loss.backward()
                torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
                set_lr(global_step)
                optimizer.step()
                ema.update(model)
                global_step += 1

            val_acc = _accuracy(ema.ema_model, x_val, y_val, batch_size=val_bs)

            if val_acc > best_acc + 1e-4:
                best_acc = val_acc
                best_sd = _clone_state_dict(ema.state_dict())
                bad = 0
            else:
                bad += 1
                if bad >= patience:
                    break

        if best_sd is not None:
            model.load_state_dict(best_sd, strict=True)

        # Stage 2: train on (train+val) with a small internal holdout
        if x_val.numel() > 0:
            x_all = torch.cat([x_train, x_val], dim=0)
            y_all = torch.cat([y_train, y_val], dim=0)
        else:
            x_all = x_train
            y_all = y_train

        n_all = x_all.size(0)
        holdout = max(256, int(0.1 * n_all))
        holdout = min(holdout, max(1, n_all // 4))
        perm2 = torch.randperm(n_all, device=device)
        val2_idx = perm2[:holdout]
        tr2_idx = perm2[holdout:]

        x_tr2 = x_all[tr2_idx]
        y_tr2 = y_all[tr2_idx]
        x_va2 = x_all[val2_idx]
        y_va2 = y_all[val2_idx]

        ft_epochs = 90
        ft_warmup_epochs = 3
        ft_patience = 12
        ft_base_lr = 7.5e-4
        ft_min_lr = 1.5e-4
        ft_wd = 0.035
        ft_smoothing = 0.04

        optimizer = torch.optim.AdamW(model.parameters(), lr=ft_base_lr, weight_decay=ft_wd)
        steps_per_epoch = max(1, (x_tr2.size(0) + train_bs - 1) // train_bs)
        total_steps = ft_epochs * steps_per_epoch
        warmup_steps = ft_warmup_epochs * steps_per_epoch
        global_step = 0

        ema = _EMA(model, decay=0.996)
        ema.to(device)

        best2_acc = -1.0
        best2_sd = None
        bad = 0

        def set_lr2(step: int):
            if step < warmup_steps:
                lr = ft_base_lr * float(step + 1) / float(max(1, warmup_steps))
            else:
                denom = max(1, total_steps - warmup_steps)
                progress = float(step - warmup_steps) / float(denom)
                lr = ft_min_lr + 0.5 * (ft_base_lr - ft_min_lr) * (1.0 + math.cos(math.pi * progress))
            for pg in optimizer.param_groups:
                pg["lr"] = lr

        for epoch in range(ft_epochs):
            model.train()
            perm = torch.randperm(x_tr2.size(0), device=device)
            for si in range(0, x_tr2.size(0), train_bs):
                idx = perm[si : si + train_bs]
                xb = x_tr2[idx]
                yb = y_tr2[idx]

                logits = model(xb)
                loss = F.cross_entropy(logits, yb, label_smoothing=ft_smoothing)

                optimizer.zero_grad(set_to_none=True)
                loss.backward()
                torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
                set_lr2(global_step)
                optimizer.step()
                ema.update(model)
                global_step += 1

            va_acc2 = _accuracy(ema.ema_model, x_va2, y_va2, batch_size=val_bs)
            if va_acc2 > best2_acc + 1e-4:
                best2_acc = va_acc2
                best2_sd = _clone_state_dict(ema.state_dict())
                bad = 0
            else:
                bad += 1
                if bad >= ft_patience:
                    break

        if best2_sd is not None:
            model.load_state_dict(best2_sd, strict=True)

        model.eval()
        return model