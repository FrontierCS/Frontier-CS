import os
import math
import time
import copy
import random
import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import TensorDataset, DataLoader


class _ResLinearBlock(nn.Module):
    def __init__(self, dim: int, dropout: float):
        super().__init__()
        self.ln = nn.LayerNorm(dim)
        self.fc = nn.Linear(dim, dim, bias=True)
        self.act = nn.GELU()
        self.drop = nn.Dropout(dropout)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        y = self.ln(x)
        y = self.fc(y)
        y = self.act(y)
        y = self.drop(y)
        return x + y


class _ResMLP(nn.Module):
    def __init__(
        self,
        input_dim: int,
        num_classes: int,
        hidden_dim: int,
        num_blocks: int,
        dropout: float,
        feat_mean: torch.Tensor,
        feat_std: torch.Tensor,
    ):
        super().__init__()
        self.register_buffer("feat_mean", feat_mean.view(1, -1))
        self.register_buffer("feat_std", feat_std.view(1, -1))

        self.ln_in = nn.LayerNorm(input_dim)
        self.fc_in = nn.Linear(input_dim, hidden_dim, bias=True)
        self.act = nn.GELU()
        self.drop_in = nn.Dropout(dropout)

        self.blocks = nn.ModuleList([_ResLinearBlock(hidden_dim, dropout) for _ in range(num_blocks)])
        self.ln_out = nn.LayerNorm(hidden_dim)
        self.head = nn.Linear(hidden_dim, num_classes, bias=True)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        if not torch.is_tensor(x):
            x = torch.as_tensor(x)
        if x.dim() > 2:
            x = x.view(x.size(0), -1)
        x = x.to(dtype=self.feat_mean.dtype)
        x = (x - self.feat_mean) / self.feat_std
        x = self.ln_in(x)
        x = self.fc_in(x)
        x = self.act(x)
        x = self.drop_in(x)
        for b in self.blocks:
            x = b(x)
        x = self.ln_out(x)
        x = self.head(x)
        return x


def _count_trainable_params(model: nn.Module) -> int:
    return sum(p.numel() for p in model.parameters() if p.requires_grad)


def _collect_from_loader(loader) -> tuple[torch.Tensor, torch.Tensor]:
    xs = []
    ys = []
    for xb, yb in loader:
        if not torch.is_tensor(xb):
            xb = torch.as_tensor(xb)
        if not torch.is_tensor(yb):
            yb = torch.as_tensor(yb)
        if xb.dim() > 2:
            xb = xb.view(xb.size(0), -1)
        xs.append(xb.to(dtype=torch.float32, device="cpu"))
        ys.append(yb.to(dtype=torch.long, device="cpu"))
    X = torch.cat(xs, dim=0)
    y = torch.cat(ys, dim=0)
    return X, y


@torch.inference_mode()
def _eval_acc(model: nn.Module, loader: DataLoader, device: torch.device) -> float:
    model.eval()
    correct = 0
    total = 0
    for xb, yb in loader:
        xb = xb.to(device=device, dtype=torch.float32)
        yb = yb.to(device=device, dtype=torch.long)
        logits = model(xb)
        pred = logits.argmax(dim=1)
        correct += (pred == yb).sum().item()
        total += yb.numel()
    return correct / max(1, total)


def _train(
    model: nn.Module,
    train_loader: DataLoader,
    val_loader: DataLoader,
    device: torch.device,
    epochs: int,
    lr: float,
    weight_decay: float,
    mixup_alpha: float,
    mixup_prob: float,
    label_smoothing: float,
    noise_std: float,
    patience: int,
) -> float:
    model.to(device=device)
    opt = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=weight_decay, betas=(0.9, 0.99))
    steps_per_epoch = max(1, len(train_loader))
    total_steps = max(1, epochs * steps_per_epoch)
    sched = torch.optim.lr_scheduler.OneCycleLR(
        opt,
        max_lr=lr,
        total_steps=total_steps,
        pct_start=0.12,
        div_factor=12.0,
        final_div_factor=300.0,
        anneal_strategy="cos",
    )

    ce = nn.CrossEntropyLoss()
    ce_smooth = nn.CrossEntropyLoss(label_smoothing=label_smoothing) if label_smoothing and label_smoothing > 0 else ce

    best_acc = -1.0
    best_state = None
    bad = 0

    for ep in range(epochs):
        model.train()
        for xb, yb in train_loader:
            xb = xb.to(device=device, dtype=torch.float32)
            yb = yb.to(device=device, dtype=torch.long)

            if noise_std and noise_std > 0:
                xb = xb + noise_std * torch.randn_like(xb)

            do_mix = (mixup_alpha and mixup_alpha > 0) and (random.random() < mixup_prob) and (xb.size(0) >= 2)
            if do_mix:
                lam = float(np.random.beta(mixup_alpha, mixup_alpha))
                perm = torch.randperm(xb.size(0), device=device)
                xb_mix = xb.mul(lam).add_(xb[perm], alpha=(1.0 - lam))
                ya = yb
                yb2 = yb[perm]
                logits = model(xb_mix)
                loss = lam * ce(logits, ya) + (1.0 - lam) * ce(logits, yb2)
            else:
                logits = model(xb)
                loss = ce_smooth(logits, yb)

            opt.zero_grad(set_to_none=True)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            opt.step()
            sched.step()

        val_acc = _eval_acc(model, val_loader, device=device)

        if val_acc > best_acc + 1e-4:
            best_acc = val_acc
            best_state = {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}
            bad = 0
        else:
            bad += 1

        if best_acc >= 0.999 and ep >= 8:
            break
        if patience and patience > 0 and bad >= patience:
            break

    if best_state is not None:
        model.load_state_dict(best_state)
    return best_acc


def _param_formula(input_dim: int, num_classes: int, num_blocks: int, h: int) -> int:
    # matches _ResMLP exactly
    # ln_in: 2*input_dim
    # fc_in: input_dim*h + h
    # each block: ln 2h + fc h*h + bias h  => h*h + 3h
    # ln_out: 2h
    # head: h*num_classes + num_classes
    return (2 * input_dim) + (input_dim * h + h) + num_blocks * (h * h + 3 * h) + (2 * h) + (h * num_classes + num_classes)


def _max_hidden_under_limit(input_dim: int, num_classes: int, num_blocks: int, limit: int) -> int:
    lo, hi = 1, 4096
    while _param_formula(input_dim, num_classes, num_blocks, hi) <= limit and hi < 65536:
        hi *= 2
    hi = min(hi, 65536)
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if _param_formula(input_dim, num_classes, num_blocks, mid) <= limit:
            lo = mid
        else:
            hi = mid - 1
    return lo


class Solution:
    def solve(self, train_loader, val_loader, metadata: dict = None) -> torch.nn.Module:
        if metadata is None:
            metadata = {}
        input_dim = int(metadata.get("input_dim", 384))
        num_classes = int(metadata.get("num_classes", 128))
        param_limit = int(metadata.get("param_limit", 5_000_000))
        device_str = str(metadata.get("device", "cpu"))

        try:
            nthreads = min(8, os.cpu_count() or 8)
            torch.set_num_threads(nthreads)
        except Exception:
            pass

        seed = 0
        random.seed(seed)
        np.random.seed(seed)
        torch.manual_seed(seed)

        X_train, y_train = _collect_from_loader(train_loader)
        X_val, y_val = _collect_from_loader(val_loader)

        mu = X_train.mean(dim=0)
        sigma = X_train.std(dim=0, unbiased=False).clamp_min(1e-3)

        train_ds = TensorDataset(X_train, y_train)
        val_ds = TensorDataset(X_val, y_val)

        batch_size = 256
        train_dl = DataLoader(train_ds, batch_size=batch_size, shuffle=True, num_workers=0, drop_last=False)
        val_dl = DataLoader(val_ds, batch_size=1024, shuffle=False, num_workers=0, drop_last=False)

        device = torch.device(device_str)

        candidates = []
        for num_blocks in (3, 5):
            h = _max_hidden_under_limit(input_dim, num_classes, num_blocks, param_limit)
            candidates.append((num_blocks, h))

        dropout = 0.05

        best_candidate_acc = -1.0
        best_model = None

        pre_epochs = 10
        for num_blocks, h in candidates:
            model = _ResMLP(
                input_dim=input_dim,
                num_classes=num_classes,
                hidden_dim=h,
                num_blocks=num_blocks,
                dropout=dropout,
                feat_mean=mu,
                feat_std=sigma,
            )
            if _count_trainable_params(model) > param_limit:
                while h > 1:
                    h -= 1
                    model = _ResMLP(
                        input_dim=input_dim,
                        num_classes=num_classes,
                        hidden_dim=h,
                        num_blocks=num_blocks,
                        dropout=dropout,
                        feat_mean=mu,
                        feat_std=sigma,
                    )
                    if _count_trainable_params(model) <= param_limit:
                        break

            _train(
                model,
                train_dl,
                val_dl,
                device=device,
                epochs=pre_epochs,
                lr=3.2e-3,
                weight_decay=1.2e-2,
                mixup_alpha=0.25,
                mixup_prob=0.5,
                label_smoothing=0.10,
                noise_std=0.010,
                patience=0,
            )
            val_acc = _eval_acc(model, val_dl, device=device)
            if val_acc > best_candidate_acc:
                best_candidate_acc = val_acc
                best_model = model

        if best_model is None:
            best_model = _ResMLP(
                input_dim=input_dim,
                num_classes=num_classes,
                hidden_dim=512,
                num_blocks=3,
                dropout=dropout,
                feat_mean=mu,
                feat_std=sigma,
            )

        _train(
            best_model,
            train_dl,
            val_dl,
            device=device,
            epochs=140,
            lr=2.4e-3,
            weight_decay=1.2e-2,
            mixup_alpha=0.20,
            mixup_prob=0.45,
            label_smoothing=0.06,
            noise_std=0.006,
            patience=28,
        )

        best_model.to(device=torch.device("cpu"))
        best_model.eval()

        if _count_trainable_params(best_model) > param_limit:
            for p in best_model.parameters():
                p.requires_grad_(False)

        return best_model
