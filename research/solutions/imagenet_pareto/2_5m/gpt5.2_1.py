import math
import os
import random
from copy import deepcopy

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import DataLoader, TensorDataset


def _set_seed(seed: int = 0):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)


def _count_trainable_params(model: nn.Module) -> int:
    return sum(p.numel() for p in model.parameters() if p.requires_grad)


def _loader_to_tensors(loader: DataLoader):
    xs = []
    ys = []
    for batch in loader:
        if isinstance(batch, (list, tuple)) and len(batch) >= 2:
            x, y = batch[0], batch[1]
        else:
            raise ValueError("Unsupported batch format")
        if not torch.is_tensor(x):
            x = torch.tensor(x)
        if not torch.is_tensor(y):
            y = torch.tensor(y)
        xs.append(x.detach().cpu())
        ys.append(y.detach().cpu())
    X = torch.cat(xs, dim=0)
    y = torch.cat(ys, dim=0)
    if X.dtype != torch.float32:
        X = X.float()
    y = y.long()
    return X, y


def _compute_mean_invstd(X: torch.Tensor, eps: float = 1e-6):
    mean = X.mean(dim=0)
    var = X.var(dim=0, unbiased=False)
    inv_std = torch.rsqrt(var + eps)
    return mean, inv_std


class InputStandardize(nn.Module):
    def __init__(self, mean: torch.Tensor, inv_std: torch.Tensor):
        super().__init__()
        self.register_buffer("mean", mean.view(1, -1).contiguous())
        self.register_buffer("inv_std", inv_std.view(1, -1).contiguous())

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        if x.dim() > 2:
            x = x.view(x.size(0), -1)
        if x.dtype != torch.float32:
            x = x.float()
        return (x - self.mean) * self.inv_std


class CosineClassifier(nn.Module):
    def __init__(self, in_dim: int, num_classes: int, init_scale: float = 15.0):
        super().__init__()
        self.weight = nn.Parameter(torch.empty(num_classes, in_dim))
        nn.init.normal_(self.weight, mean=0.0, std=0.02)
        self.logit_scale = nn.Parameter(torch.tensor(float(init_scale)))

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = F.normalize(x, dim=1)
        w = F.normalize(self.weight, dim=1)
        s = self.logit_scale.clamp(1.0, 100.0)
        return s * F.linear(x, w)


class MLPResNet(nn.Module):
    def __init__(self, input_dim: int, width: int, num_classes: int, mean: torch.Tensor, inv_std: torch.Tensor, dropout: float = 0.10):
        super().__init__()
        self.inp = InputStandardize(mean, inv_std)

        self.fc1 = nn.Linear(input_dim, width, bias=True)
        self.ln1 = nn.LayerNorm(width)

        self.fc2 = nn.Linear(width, width, bias=True)
        self.ln2 = nn.LayerNorm(width)

        self.fc3 = nn.Linear(width, width, bias=True)
        self.ln3 = nn.LayerNorm(width)

        self.drop = nn.Dropout(dropout)
        self.head = CosineClassifier(width, num_classes, init_scale=15.0)

        self._init_weights()

    def _init_weights(self):
        for m in self.modules():
            if isinstance(m, nn.Linear):
                nn.init.kaiming_normal_(m.weight, nonlinearity="relu")
                if m.bias is not None:
                    nn.init.zeros_(m.bias)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self.inp(x)
        x = F.gelu(self.ln1(self.fc1(x)))

        y = F.gelu(self.ln2(self.fc2(x)))
        y = self.drop(y)
        x = x + y

        y = F.gelu(self.ln3(self.fc3(x)))
        y = self.drop(y)
        x = x + y

        return self.head(x)


class EMA:
    def __init__(self, model: nn.Module, decay: float = 0.995):
        self.decay = float(decay)
        self.shadow = {}
        self._init_from(model)

    def _init_from(self, model: nn.Module):
        self.shadow = {}
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
            s = self.shadow.get(name, None)
            if s is None:
                self.shadow[name] = p.detach().clone()
            else:
                s.mul_(d).add_(p.detach(), alpha=(1.0 - d))

    def state_dict(self):
        return {k: v.clone() for k, v in self.shadow.items()}

    @torch.no_grad()
    def copy_to(self, model: nn.Module):
        for name, p in model.named_parameters():
            if p.requires_grad and name in self.shadow:
                p.copy_(self.shadow[name])


def _max_width_for_limit(input_dim: int, num_classes: int, param_limit: int, multiple: int = 16) -> int:
    # Model params for 2 residual blocks:
    # fc1: (input_dim+1)*w
    # fc2, fc3: 2*(w^2+w)
    # ln1,ln2,ln3: 3*(2w)
    # cosine head: num_classes*w + 1 (scale)
    # total = 2w^2 + (input_dim + num_classes + 9)*w + 1
    a = 2
    b = input_dim + num_classes + 9
    c = 1

    lo, hi = 64, 4096
    while a * hi * hi + b * hi + c <= param_limit:
        hi *= 2
        if hi > 65536:
            break

    best = lo
    lo = 64
    while lo <= hi:
        mid = (lo + hi) // 2
        val = a * mid * mid + b * mid + c
        if val <= param_limit:
            best = mid
            lo = mid + 1
        else:
            hi = mid - 1

    best = (best // multiple) * multiple
    best = max(best, multiple)
    while best > multiple and (a * best * best + b * best + c) > param_limit:
        best -= multiple
    return best


@torch.inference_mode()
def _accuracy(model: nn.Module, loader: DataLoader, device: torch.device) -> float:
    model.eval()
    correct = 0
    total = 0
    for x, y in loader:
        x = x.to(device, non_blocking=False)
        y = y.to(device, non_blocking=False)
        logits = model(x)
        pred = logits.argmax(dim=1)
        correct += (pred == y).sum().item()
        total += y.numel()
    return float(correct) / float(max(1, total))


def _mixup(x: torch.Tensor, y: torch.Tensor, alpha: float):
    if alpha <= 0.0:
        return x, y, y, 1.0
    lam = float(np.random.beta(alpha, alpha))
    perm = torch.randperm(x.size(0), device=x.device)
    x_m = lam * x + (1.0 - lam) * x[perm]
    y_a = y
    y_b = y[perm]
    return x_m, y_a, y_b, lam


class Solution:
    def solve(self, train_loader, val_loader, metadata: dict = None) -> torch.nn.Module:
        if metadata is None:
            metadata = {}
        input_dim = int(metadata.get("input_dim", 384))
        num_classes = int(metadata.get("num_classes", 128))
        param_limit = int(metadata.get("param_limit", 2_500_000))
        device_str = str(metadata.get("device", "cpu"))
        device = torch.device(device_str)

        try:
            torch.set_num_threads(min(8, os.cpu_count() or 8))
        except Exception:
            pass
        _set_seed(0)

        Xtr, ytr = _loader_to_tensors(train_loader)
        Xva, yva = _loader_to_tensors(val_loader)

        if Xtr.dim() > 2:
            Xtr = Xtr.view(Xtr.size(0), -1)
        if Xva.dim() > 2:
            Xva = Xva.view(Xva.size(0), -1)

        if Xtr.size(1) != input_dim:
            input_dim = int(Xtr.size(1))

        mean, inv_std = _compute_mean_invstd(Xtr)

        bs = 256
        train_dl = DataLoader(TensorDataset(Xtr, ytr), batch_size=bs, shuffle=True, drop_last=False, num_workers=0)
        val_dl = DataLoader(TensorDataset(Xva, yva), batch_size=512, shuffle=False, drop_last=False, num_workers=0)

        width = _max_width_for_limit(input_dim, num_classes, param_limit, multiple=16)
        model = MLPResNet(input_dim=input_dim, width=width, num_classes=num_classes, mean=mean, inv_std=inv_std, dropout=0.10).to(device)

        if _count_trainable_params(model) > param_limit:
            # Conservative fallback
            width = max(128, (width // 32) * 32 - 32)
            model = MLPResNet(input_dim=input_dim, width=width, num_classes=num_classes, mean=mean, inv_std=inv_std, dropout=0.10).to(device)

        if _count_trainable_params(model) > param_limit:
            # Hard guarantee
            width = 512
            model = MLPResNet(input_dim=input_dim, width=width, num_classes=num_classes, mean=mean, inv_std=inv_std, dropout=0.10).to(device)

        opt = torch.optim.AdamW(model.parameters(), lr=3e-3, betas=(0.9, 0.95), weight_decay=0.02)

        steps_per_epoch = max(1, len(train_dl))
        max_epochs = 300
        total_steps = max_epochs * steps_per_epoch
        warmup_steps = min(100, max(10, total_steps // 20))
        min_lr_ratio = 0.05

        def lr_lambda(step: int):
            if step < warmup_steps:
                return float(step + 1) / float(max(1, warmup_steps))
            t = float(step - warmup_steps) / float(max(1, total_steps - warmup_steps))
            t = min(1.0, max(0.0, t))
            cos = 0.5 * (1.0 + math.cos(math.pi * t))
            return min_lr_ratio + (1.0 - min_lr_ratio) * cos

        sched = torch.optim.lr_scheduler.LambdaLR(opt, lr_lambda=lr_lambda)

        ema = EMA(model, decay=0.995)

        best_state = deepcopy(model.state_dict())
        best_val = -1.0
        best_epoch = 0

        label_smoothing = 0.05
        mixup_alpha = 0.20
        input_noise_std = 0.02

        global_step = 0
        patience = 50
        min_epochs = 40

        for epoch in range(max_epochs):
            model.train()
            for xb, yb in train_dl:
                xb = xb.to(device, non_blocking=False)
                yb = yb.to(device, non_blocking=False)

                if input_noise_std > 0.0:
                    xb = xb + input_noise_std * torch.randn_like(xb)

                xb, ya, yb2, lam = _mixup(xb, yb, mixup_alpha)

                opt.zero_grad(set_to_none=True)
                logits = model(xb)
                if lam == 1.0:
                    loss = F.cross_entropy(logits, ya, label_smoothing=label_smoothing)
                else:
                    loss = lam * F.cross_entropy(logits, ya, label_smoothing=label_smoothing) + (1.0 - lam) * F.cross_entropy(
                        logits, yb2, label_smoothing=label_smoothing
                    )

                loss.backward()
                torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
                opt.step()
                sched.step()
                ema.update(model)

                global_step += 1

            val_acc = _accuracy(model, val_dl, device)
            if val_acc > best_val:
                best_val = val_acc
                best_state = deepcopy(model.state_dict())
                best_epoch = epoch

            if epoch >= min_epochs and (epoch - best_epoch) >= patience:
                break

        model.load_state_dict(best_state)
        raw_val = _accuracy(model, val_dl, device)

        # Evaluate EMA weights on val and keep if better
        ema_state = ema.state_dict()
        tmp_state = deepcopy(model.state_dict())
        model.load_state_dict({**tmp_state, **ema_state}, strict=False)
        ema_val = _accuracy(model, val_dl, device)
        if ema_val >= raw_val:
            model.load_state_dict({**best_state, **ema_state}, strict=False)
        else:
            model.load_state_dict(best_state)

        model.eval()
        return model