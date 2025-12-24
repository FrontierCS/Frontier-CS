import math
import os
import copy
from typing import Tuple, Optional, Dict

import torch
import torch.nn as nn
import torch.nn.functional as F


def _param_count_trainable(model: nn.Module) -> int:
    return sum(p.numel() for p in model.parameters() if p.requires_grad)


@torch.inference_mode()
def _accuracy(model: nn.Module, x: torch.Tensor, y: torch.Tensor, batch_size: int = 512) -> float:
    model.eval()
    n = x.shape[0]
    correct = 0
    for i in range(0, n, batch_size):
        xb = x[i:i + batch_size]
        yb = y[i:i + batch_size]
        logits = model(xb)
        pred = logits.argmax(dim=1)
        correct += (pred == yb).sum().item()
    return correct / max(1, n)


def _collect_loader(loader, device: torch.device) -> Tuple[torch.Tensor, torch.Tensor]:
    xs = []
    ys = []
    for xb, yb in loader:
        if not torch.is_tensor(xb):
            xb = torch.tensor(xb)
        if not torch.is_tensor(yb):
            yb = torch.tensor(yb)
        xb = xb.to(device=device, dtype=torch.float32, non_blocking=False)
        yb = yb.to(device=device, dtype=torch.long, non_blocking=False)
        if xb.dim() > 2:
            xb = xb.view(xb.size(0), -1)
        xs.append(xb)
        ys.append(yb)
    x = torch.cat(xs, dim=0) if xs else torch.empty((0,), device=device, dtype=torch.float32)
    y = torch.cat(ys, dim=0) if ys else torch.empty((0,), device=device, dtype=torch.long)
    return x, y


class _ResBlock(nn.Module):
    __slots__ = ("ln", "fc", "drop", "res_scale")

    def __init__(self, dim: int, dropout: float, res_scale: float = 0.8):
        super().__init__()
        self.ln = nn.LayerNorm(dim)
        self.fc = nn.Linear(dim, dim, bias=False)
        self.drop = nn.Dropout(dropout)
        self.res_scale = float(res_scale)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        y = self.ln(x)
        y = self.fc(y)
        y = F.gelu(y)
        y = self.drop(y)
        return x + y * self.res_scale


class _CosineClassifier(nn.Module):
    __slots__ = ("weight", "logit_scale")

    def __init__(self, in_dim: int, num_classes: int, init_scale: float = 10.0):
        super().__init__()
        self.weight = nn.Parameter(torch.empty(num_classes, in_dim))
        nn.init.normal_(self.weight, mean=0.0, std=0.02)
        self.logit_scale = nn.Parameter(torch.tensor(math.log(init_scale), dtype=torch.float32))

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = F.normalize(x, dim=-1, eps=1e-6)
        w = F.normalize(self.weight, dim=-1, eps=1e-6)
        scale = self.logit_scale.exp().clamp(1.0, 100.0)
        return (x @ w.t()) * scale


class _MLPNet(nn.Module):
    def __init__(
        self,
        input_dim: int,
        num_classes: int,
        h1: int,
        h2: int,
        n_res: int,
        mean: torch.Tensor,
        inv_std: torch.Tensor,
        dropout: float = 0.12,
        res_scale: float = 0.8,
    ):
        super().__init__()
        self.register_buffer("mean", mean.view(1, -1).to(dtype=torch.float32), persistent=False)
        self.register_buffer("inv_std", inv_std.view(1, -1).to(dtype=torch.float32), persistent=False)

        self.fc1 = nn.Linear(input_dim, h1, bias=False)
        self.ln1 = nn.LayerNorm(h1)
        self.drop1 = nn.Dropout(dropout)

        self.fc2 = nn.Linear(h1, h2, bias=False)
        self.ln2 = nn.LayerNorm(h2)
        self.drop2 = nn.Dropout(dropout)

        self.blocks = nn.ModuleList([_ResBlock(h2, dropout=dropout, res_scale=res_scale) for _ in range(n_res)])

        self.final_ln = nn.LayerNorm(h2)
        self.final_drop = nn.Dropout(dropout)
        self.head = _CosineClassifier(h2, num_classes, init_scale=10.0)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = x.to(dtype=torch.float32)
        x = (x - self.mean) * self.inv_std

        x = self.fc1(x)
        x = self.ln1(x)
        x = F.gelu(x)
        x = self.drop1(x)

        x = self.fc2(x)
        x = self.ln2(x)
        x = F.gelu(x)
        x = self.drop2(x)

        for b in self.blocks:
            x = b(x)

        x = self.final_ln(x)
        x = F.gelu(x)
        x = self.final_drop(x)

        return self.head(x)


def _estimate_params(input_dim: int, num_classes: int, h1: int, h2: int, n_res: int) -> int:
    # bias=False for linears, LN has 2*dim params.
    # Structure: fc1(in->h1), ln1; fc2(h1->h2), ln2; n_res*(ln+fc); final_ln; cosine head (weight + logit_scale)
    linear_params = input_dim * h1 + h1 * h2 + n_res * (h2 * h2) + h2 * num_classes
    ln_params = 2 * h1 + 2 * h2 + n_res * (2 * h2) + 2 * h2  # ln1 + ln2 + each block ln + final_ln
    head_extra = 1  # logit_scale
    return linear_params + ln_params + head_extra


def _pick_arch(input_dim: int, num_classes: int, param_limit: int, n_res: int, h1_max: int = 512) -> Tuple[int, int, int]:
    h1_start = max(input_dim, 128)
    best = None
    for h2 in range(512, 127, -8):
        for h1 in range(min(h1_max, 512) // 8 * 8, h1_start - 1, -8):
            est = _estimate_params(input_dim, num_classes, h1, h2, n_res)
            if est <= param_limit:
                best = (h1, h2, n_res)
                break
        if best is not None:
            break
    if best is None:
        # Fallback small
        h1 = max(input_dim, 256)
        h2 = 192
        while _estimate_params(input_dim, num_classes, h1, h2, n_res) > param_limit and h2 > 64:
            h2 -= 8
        return (h1, max(64, h2), n_res)
    return best


def _train_model(
    model: nn.Module,
    x_train: torch.Tensor,
    y_train: torch.Tensor,
    x_val: Optional[torch.Tensor],
    y_val: Optional[torch.Tensor],
    *,
    epochs: int,
    batch_size: int,
    lr: float,
    weight_decay: float,
    label_smoothing: float,
    noise_std: Optional[torch.Tensor],
    noise_factor: float,
    early_stop_patience: Optional[int],
    min_epochs: int,
    seed: int = 0,
) -> Tuple[nn.Module, Dict[str, torch.Tensor], float]:
    torch.manual_seed(seed)

    opt = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=weight_decay, betas=(0.9, 0.95))
    steps_per_epoch = max(1, (x_train.shape[0] + batch_size - 1) // batch_size)
    total_steps = max(1, epochs * steps_per_epoch)
    sched = torch.optim.lr_scheduler.OneCycleLR(
        opt,
        max_lr=lr,
        total_steps=total_steps,
        pct_start=0.1,
        anneal_strategy="cos",
        div_factor=10.0,
        final_div_factor=50.0,
    )

    best_state = {k: v.detach().clone() for k, v in model.state_dict().items()}
    best_acc = -1.0
    bad = 0

    n = x_train.shape[0]
    for ep in range(epochs):
        model.train()
        perm = torch.randperm(n, device=x_train.device)
        for i in range(0, n, batch_size):
            idx = perm[i:i + batch_size]
            xb = x_train.index_select(0, idx)
            yb = y_train.index_select(0, idx)

            if noise_factor > 0.0 and noise_std is not None:
                xb = xb + torch.randn_like(xb) * (noise_std * noise_factor)

            logits = model(xb)
            loss = F.cross_entropy(logits, yb, label_smoothing=label_smoothing)

            opt.zero_grad(set_to_none=True)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            opt.step()
            sched.step()

        if x_val is not None and y_val is not None:
            acc = _accuracy(model, x_val, y_val, batch_size=512)
            if acc > best_acc + 1e-6:
                best_acc = acc
                best_state = {k: v.detach().clone() for k, v in model.state_dict().items()}
                bad = 0
            else:
                bad += 1

            if early_stop_patience is not None and ep + 1 >= min_epochs and bad >= early_stop_patience:
                break

    return model, best_state, best_acc


class Solution:
    def solve(self, train_loader, val_loader, metadata: dict = None) -> torch.nn.Module:
        if metadata is None:
            metadata = {}
        num_classes = int(metadata.get("num_classes", 128))
        input_dim = int(metadata.get("input_dim", 384))
        param_limit = int(metadata.get("param_limit", 500_000))
        device = torch.device(str(metadata.get("device", "cpu")))

        try:
            threads = min(8, os.cpu_count() or 8)
            torch.set_num_threads(threads)
            torch.set_num_interop_threads(1)
        except Exception:
            pass

        x_train, y_train = _collect_loader(train_loader, device=device)
        if val_loader is not None:
            x_val, y_val = _collect_loader(val_loader, device=device)
            if x_val.numel() == 0:
                x_val, y_val = None, None
        else:
            x_val, y_val = None, None

        if x_train.dim() != 2 or x_train.shape[1] != input_dim:
            x_train = x_train.view(x_train.size(0), -1)
        if x_val is not None and (x_val.dim() != 2 or x_val.shape[1] != input_dim):
            x_val = x_val.view(x_val.size(0), -1)

        mean = x_train.mean(dim=0)
        std = x_train.std(dim=0, unbiased=False).clamp_min(1e-6)
        inv_std = 1.0 / std

        candidates = []
        for n_res in (1, 2, 3):
            h1, h2, n_res = _pick_arch(input_dim, num_classes, param_limit, n_res=n_res, h1_max=512)
            est = _estimate_params(input_dim, num_classes, h1, h2, n_res)
            if est <= param_limit:
                candidates.append((h1, h2, n_res, est))
        if not candidates:
            candidates = [(max(input_dim, 384), 256, 1, _estimate_params(input_dim, num_classes, max(input_dim, 384), 256, 1))]

        # Quick selection among candidates
        best_cand = candidates[0]
        best_cand_acc = -1.0
        if x_val is not None:
            for ci, (h1, h2, n_res, _) in enumerate(candidates[:3]):
                m = _MLPNet(
                    input_dim=input_dim,
                    num_classes=num_classes,
                    h1=h1,
                    h2=h2,
                    n_res=n_res,
                    mean=mean,
                    inv_std=inv_std,
                    dropout=0.12 if n_res <= 2 else 0.13,
                    res_scale=0.8 if n_res <= 3 else 0.7,
                ).to(device)
                if _param_count_trainable(m) > param_limit:
                    continue
                _, state, acc = _train_model(
                    m,
                    x_train,
                    y_train,
                    x_val,
                    y_val,
                    epochs=25,
                    batch_size=128,
                    lr=2.5e-3,
                    weight_decay=1.5e-3,
                    label_smoothing=0.06,
                    noise_std=std,
                    noise_factor=0.02,
                    early_stop_patience=None,
                    min_epochs=1,
                    seed=1234 + ci,
                )
                m.load_state_dict(state, strict=True)
                acc2 = _accuracy(m, x_val, y_val, batch_size=512)
                if acc2 > best_cand_acc:
                    best_cand_acc = acc2
                    best_cand = (h1, h2, n_res, _param_count_trainable(m))

        h1, h2, n_res, _ = best_cand

        model = _MLPNet(
            input_dim=input_dim,
            num_classes=num_classes,
            h1=h1,
            h2=h2,
            n_res=n_res,
            mean=mean,
            inv_std=inv_std,
            dropout=0.12 if n_res <= 2 else 0.13,
            res_scale=0.8 if n_res <= 3 else 0.7,
        ).to(device)

        if _param_count_trainable(model) > param_limit:
            # Emergency fallback
            model = _MLPNet(
                input_dim=input_dim,
                num_classes=num_classes,
                h1=max(input_dim, 384),
                h2=256,
                n_res=1,
                mean=mean,
                inv_std=inv_std,
                dropout=0.10,
                res_scale=0.8,
            ).to(device)

        # Main training with early stopping
        model, best_state, _ = _train_model(
            model,
            x_train,
            y_train,
            x_val,
            y_val,
            epochs=140,
            batch_size=128,
            lr=3.0e-3,
            weight_decay=1.8e-3,
            label_smoothing=0.06,
            noise_std=std,
            noise_factor=0.02,
            early_stop_patience=25 if x_val is not None else None,
            min_epochs=50,
            seed=2025,
        )
        model.load_state_dict(best_state, strict=True)

        # Optional fine-tune on train+val (if available)
        if x_val is not None and y_val is not None and x_val.shape[0] > 0:
            x_all = torch.cat([x_train, x_val], dim=0)
            y_all = torch.cat([y_train, y_val], dim=0)
            model, best_state2, _ = _train_model(
                model,
                x_all,
                y_all,
                None,
                None,
                epochs=35,
                batch_size=128,
                lr=7.5e-4,
                weight_decay=1.2e-3,
                label_smoothing=0.03,
                noise_std=std,
                noise_factor=0.0,
                early_stop_patience=None,
                min_epochs=1,
                seed=777,
            )
            # keep final model (already trained); no val to select

        if _param_count_trainable(model) > param_limit:
            # Hard constraint safety: return a smaller guaranteed model
            model = _MLPNet(
                input_dim=input_dim,
                num_classes=num_classes,
                h1=max(input_dim, 320),
                h2=192,
                n_res=1,
                mean=mean,
                inv_std=inv_std,
                dropout=0.10,
                res_scale=0.8,
            ).to(device)

        model.eval()
        return model
