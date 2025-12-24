import os
import time
import math
import copy
from typing import Optional, Tuple, Dict

import torch
import torch.nn as nn
import torch.nn.functional as F


def _count_trainable_params(model: nn.Module) -> int:
    return sum(p.numel() for p in model.parameters() if p.requires_grad)


def _extract_loader(loader) -> Tuple[torch.Tensor, torch.Tensor]:
    xs = []
    ys = []
    for batch in loader:
        if isinstance(batch, (list, tuple)) and len(batch) >= 2:
            x, y = batch[0], batch[1]
        else:
            raise ValueError("Loader must yield (inputs, targets)")
        if not torch.is_tensor(x):
            x = torch.as_tensor(x)
        if not torch.is_tensor(y):
            y = torch.as_tensor(y)
        xs.append(x.detach().cpu())
        ys.append(y.detach().cpu())
    x = torch.cat(xs, dim=0)
    y = torch.cat(ys, dim=0)
    return x, y


def _compute_mean_std(x: torch.Tensor, eps: float = 1e-6) -> Tuple[torch.Tensor, torch.Tensor]:
    x = x.float()
    mean = x.mean(dim=0)
    var = x.var(dim=0, unbiased=False)
    std = torch.sqrt(var + eps)
    std = torch.clamp(std, min=1e-3)
    return mean, std


def _accuracy(model: nn.Module, x: torch.Tensor, y: torch.Tensor, batch_size: int = 512) -> float:
    model.eval()
    correct = 0
    total = 0
    with torch.no_grad():
        n = x.shape[0]
        for i in range(0, n, batch_size):
            xb = x[i:i + batch_size]
            yb = y[i:i + batch_size]
            logits = model(xb)
            pred = logits.argmax(dim=1)
            correct += (pred == yb).sum().item()
            total += yb.numel()
    return correct / max(1, total)


def _ce_soft(logits: torch.Tensor, soft_targets: torch.Tensor) -> torch.Tensor:
    logp = F.log_softmax(logits, dim=1)
    return -(soft_targets * logp).sum(dim=1).mean()


class _TinyMLP(nn.Module):
    def __init__(
        self,
        input_dim: int,
        num_classes: int,
        w1: int,
        w2: int,
        w3: int,
        mean: torch.Tensor,
        std: torch.Tensor,
        dropout: float = 0.10,
    ):
        super().__init__()
        self.register_buffer("x_mean", mean.view(1, -1).float(), persistent=True)
        self.register_buffer("x_std", std.view(1, -1).float(), persistent=True)

        self.fc1 = nn.Linear(input_dim, w1, bias=True)
        self.bn1 = nn.BatchNorm1d(w1, eps=1e-5, momentum=0.06, affine=True, track_running_stats=True)

        self.fc2 = nn.Linear(w1, w2, bias=True)
        self.bn2 = nn.BatchNorm1d(w2, eps=1e-5, momentum=0.06, affine=True, track_running_stats=True)

        self.fc3 = nn.Linear(w2, w3, bias=True)
        self.bn3 = nn.BatchNorm1d(w3, eps=1e-5, momentum=0.06, affine=True, track_running_stats=True)

        self.head = nn.Linear(w3, num_classes, bias=True)

        self.drop = nn.Dropout(p=dropout)

        for m in self.modules():
            if isinstance(m, nn.Linear):
                nn.init.kaiming_uniform_(m.weight, a=math.sqrt(5))
                if m.bias is not None:
                    fan_in, _ = nn.init._calculate_fan_in_and_fan_out(m.weight)
                    bound = 1 / math.sqrt(max(1, fan_in))
                    nn.init.uniform_(m.bias, -bound, bound)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        if x.dim() > 2:
            x = x.view(x.size(0), -1)
        x = x.float()
        x = (x - self.x_mean) / self.x_std

        x = self.fc1(x)
        x = self.bn1(x)
        x = F.gelu(x)
        x = self.drop(x)

        x = self.fc2(x)
        x = self.bn2(x)
        x = F.gelu(x)
        x = self.drop(x)

        x = self.fc3(x)
        x = self.bn3(x)
        x = F.gelu(x)
        x = self.drop(x)

        x = self.head(x)
        return x


def _choose_widths(input_dim: int, num_classes: int, param_limit: int) -> Tuple[int, int, int]:
    d = int(input_dim)
    c = int(num_classes)
    w2 = d
    w3 = int(round((2.0 / 3.0) * d))
    w3 = max(64, (w3 // 16) * 16)
    if w3 < 64:
        w3 = 64

    def total_params(w1v: int, w3v: int) -> int:
        return (d * w1v + w1v) + (w1v * w2 + w2) + (w2 * w3v + w3v) + (w3v * c + c) + 2 * (w1v + w2 + w3v)

    # max w1 under limit (approx), with slack for safety
    base = (w2 * w3 + w3) + (w3 * c + c) + (w2) + 2 * (w2 + w3)
    # Remaining for first two linears and BN1: d*w1 + w1*w2 + w1 + 2*w1 = w1*(d+w2+3)
    rem = max(0, param_limit - base)
    denom = d + w2 + 3
    w1 = int(rem // max(1, denom))
    w1 = max(128, w1)
    w1 = (w1 // 8) * 8

    # Fit strictly
    while total_params(w1, w3) > param_limit and w1 > 128:
        w1 -= 8

    # If still too big, reduce w3
    while total_params(w1, w3) > param_limit and w3 > 64:
        w3 -= 16
        while total_params(w1, w3) > param_limit and w1 > 128:
            w1 -= 8

    # Ensure feasible
    if total_params(w1, w3) > param_limit:
        # fallback small
        w1 = max(128, (d * 3) // 2)
        w1 = (w1 // 8) * 8
        w3 = max(64, (d // 2 // 16) * 16)
        while total_params(w1, w3) > param_limit and w1 > 128:
            w1 -= 8
        while total_params(w1, w3) > param_limit and w3 > 64:
            w3 -= 16

    return int(w1), int(w2), int(w3)


class Solution:
    def solve(self, train_loader, val_loader, metadata: dict = None) -> nn.Module:
        if metadata is None:
            metadata = {}
        device = metadata.get("device", "cpu")
        if device != "cpu":
            device = "cpu"

        input_dim = int(metadata.get("input_dim", 384))
        num_classes = int(metadata.get("num_classes", 128))
        param_limit = int(metadata.get("param_limit", 500_000))

        try:
            torch.set_num_threads(min(8, os.cpu_count() or 8))
        except Exception:
            pass
        torch.manual_seed(0)

        x_train, y_train = _extract_loader(train_loader)
        x_val, y_val = _extract_loader(val_loader)

        if x_train.dim() > 2:
            x_train = x_train.view(x_train.size(0), -1)
        if x_val.dim() > 2:
            x_val = x_val.view(x_val.size(0), -1)

        x_train = x_train.float()
        x_val = x_val.float()
        y_train = y_train.long()
        y_val = y_val.long()

        mean, std = _compute_mean_std(x_train)

        w1, w2, w3 = _choose_widths(input_dim=input_dim, num_classes=num_classes, param_limit=param_limit)
        model = _TinyMLP(
            input_dim=input_dim,
            num_classes=num_classes,
            w1=w1,
            w2=w2,
            w3=w3,
            mean=mean,
            std=std,
            dropout=0.10,
        ).to("cpu")

        if _count_trainable_params(model) > param_limit:
            # last-resort shrink
            for _ in range(200):
                if _count_trainable_params(model) <= param_limit:
                    break
                w1 = max(128, w1 - 8)
                model = _TinyMLP(
                    input_dim=input_dim,
                    num_classes=num_classes,
                    w1=w1,
                    w2=w2,
                    w3=w3,
                    mean=mean,
                    std=std,
                    dropout=0.10,
                ).to("cpu")

        # Build internal loaders for speed/consistency
        n_train = x_train.shape[0]
        n_val = x_val.shape[0]
        train_bs = 256 if n_train >= 256 else max(32, (n_train // 2) if n_train >= 64 else n_train)
        val_bs = 512 if n_val >= 512 else max(64, n_val)

        train_ds = torch.utils.data.TensorDataset(x_train, y_train)
        train_dl = torch.utils.data.DataLoader(train_ds, batch_size=train_bs, shuffle=True, drop_last=(n_train >= train_bs))

        # Training
        label_smoothing = 0.06
        mixup_alpha = 0.20
        mixup_prob = 0.80
        noise_std = 0.015

        max_epochs = 220
        patience = 35
        min_epochs = 35

        optimizer = torch.optim.AdamW(model.parameters(), lr=5e-3, weight_decay=1.5e-4, betas=(0.9, 0.99))
        steps_per_epoch = max(1, len(train_dl))
        scheduler = torch.optim.lr_scheduler.OneCycleLR(
            optimizer,
            max_lr=5e-3,
            epochs=max_epochs,
            steps_per_epoch=steps_per_epoch,
            pct_start=0.12,
            anneal_strategy="cos",
            div_factor=10.0,
            final_div_factor=80.0,
        )

        # EMA
        ema_decay = 0.995
        ema_shadow: Dict[str, torch.Tensor] = {}
        for name, p in model.named_parameters():
            if p.requires_grad:
                ema_shadow[name] = p.detach().clone()

        def ema_update():
            with torch.no_grad():
                for name, p in model.named_parameters():
                    if not p.requires_grad:
                        continue
                    ema_shadow[name].mul_(ema_decay).add_(p.detach(), alpha=(1.0 - ema_decay))

        def ema_apply():
            with torch.no_grad():
                for name, p in model.named_parameters():
                    if not p.requires_grad:
                        continue
                    p.copy_(ema_shadow[name])

        best_state = copy.deepcopy(model.state_dict())
        best_val = -1.0
        best_epoch = -1
        bad = 0

        start_time = time.monotonic()
        time_budget = 3300.0  # leave margin

        for epoch in range(max_epochs):
            if time.monotonic() - start_time > time_budget:
                break

            model.train()
            for xb, yb in train_dl:
                xb = xb.float()
                yb = yb.long()

                if noise_std > 0:
                    xb = xb + torch.randn_like(xb) * noise_std

                do_mixup = (mixup_alpha > 0) and (torch.rand(()) < mixup_prob)
                if do_mixup:
                    lam = torch.distributions.Beta(mixup_alpha, mixup_alpha).sample().item()
                    lam = float(max(0.05, min(0.95, lam)))
                    idx = torch.randperm(xb.size(0))
                    xb2 = xb[idx]
                    yb2 = yb[idx]
                    xb_mix = xb.mul(lam).add(xb2, alpha=(1.0 - lam))

                    y1 = F.one_hot(yb, num_classes=num_classes).float()
                    y2 = F.one_hot(yb2, num_classes=num_classes).float()
                    y_soft = y1.mul(lam).add(y2, alpha=(1.0 - lam))
                    if label_smoothing > 0:
                        y_soft = y_soft * (1.0 - label_smoothing) + (label_smoothing / num_classes)

                    logits = model(xb_mix)
                    loss = _ce_soft(logits, y_soft)
                else:
                    logits = model(xb)
                    loss = F.cross_entropy(logits, yb, label_smoothing=label_smoothing)

                optimizer.zero_grad(set_to_none=True)
                loss.backward()
                torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
                optimizer.step()
                scheduler.step()
                ema_update()

            # Evaluate (EMA weights)
            current_state = copy.deepcopy(model.state_dict())
            ema_apply()
            val_acc = _accuracy(model, x_val, y_val, batch_size=val_bs)

            if val_acc > best_val + 1e-5:
                best_val = val_acc
                best_epoch = epoch
                best_state = copy.deepcopy(model.state_dict())
                bad = 0
            else:
                bad += 1

            model.load_state_dict(current_state)

            if epoch >= min_epochs and bad >= patience:
                break

        # Load best EMA state
        model.load_state_dict(best_state)

        # Optional small fine-tune on train+val with reduced LR
        x_all = torch.cat([x_train, x_val], dim=0)
        y_all = torch.cat([y_train, y_val], dim=0)
        all_ds = torch.utils.data.TensorDataset(x_all, y_all)
        all_bs = 256 if x_all.shape[0] >= 256 else max(32, x_all.shape[0] // 2)
        all_dl = torch.utils.data.DataLoader(all_ds, batch_size=all_bs, shuffle=True, drop_last=(x_all.shape[0] >= all_bs))

        ft_epochs = 18
        ft_optimizer = torch.optim.AdamW(model.parameters(), lr=1.5e-3, weight_decay=1.2e-4, betas=(0.9, 0.99))
        ft_steps = max(1, len(all_dl) * ft_epochs)
        ft_scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(ft_optimizer, T_max=max(1, ft_steps), eta_min=2.5e-4)

        model.train()
        step = 0
        for _ in range(ft_epochs):
            if time.monotonic() - start_time > time_budget:
                break
            for xb, yb in all_dl:
                xb = xb.float()
                yb = yb.long()
                if noise_std > 0:
                    xb = xb + torch.randn_like(xb) * (noise_std * 0.6)

                logits = model(xb)
                loss = F.cross_entropy(logits, yb, label_smoothing=label_smoothing)

                ft_optimizer.zero_grad(set_to_none=True)
                loss.backward()
                torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
                ft_optimizer.step()
                ft_scheduler.step()
                step += 1

        model.eval()
        return model.to("cpu")
