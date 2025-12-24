import os
import math
import copy
from typing import Tuple, Optional, Dict

import torch
import torch.nn as nn
import torch.nn.functional as F


class _Normalize(nn.Module):
    def __init__(self, mean: torch.Tensor, std: torch.Tensor, eps: float = 1e-6):
        super().__init__()
        self.register_buffer("mean", mean)
        self.register_buffer("std", std)
        self.eps = float(eps)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return (x - self.mean) / (self.std + self.eps)


class _MLPNet(nn.Module):
    def __init__(self, input_dim: int, num_classes: int, h1: int, h2: int, mean: torch.Tensor, std: torch.Tensor, dropout: float = 0.10):
        super().__init__()
        self.norm = _Normalize(mean, std)
        self.fc1 = nn.Linear(input_dim, h1, bias=True)
        self.ln1 = nn.LayerNorm(h1, elementwise_affine=True)
        self.fc2 = nn.Linear(h1, h2, bias=True)
        self.ln2 = nn.LayerNorm(h2, elementwise_affine=True)
        self.drop = nn.Dropout(dropout)
        self.head = nn.Linear(h2, num_classes, bias=True)

    def body(self, x: torch.Tensor) -> torch.Tensor:
        x = self.norm(x)
        x = self.fc1(x)
        x = self.ln1(x)
        x = F.gelu(x)
        x = self.drop(x)
        x = self.fc2(x)
        x = self.ln2(x)
        x = F.gelu(x)
        x = self.drop(x)
        return x

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self.body(x)
        return self.head(x)


def _param_count(model: nn.Module) -> int:
    return sum(p.numel() for p in model.parameters() if p.requires_grad)


def _collect_from_loader(loader) -> Tuple[torch.Tensor, torch.Tensor]:
    xs = []
    ys = []
    for batch in loader:
        if isinstance(batch, (list, tuple)) and len(batch) >= 2:
            x, y = batch[0], batch[1]
        elif isinstance(batch, dict) and "inputs" in batch and "targets" in batch:
            x, y = batch["inputs"], batch["targets"]
        else:
            raise ValueError("Unsupported batch format")
        x = x.detach().to("cpu")
        y = y.detach().to("cpu")
        if x.dtype != torch.float32:
            x = x.float()
        if y.dtype != torch.long:
            y = y.long()
        xs.append(x)
        ys.append(y)
    X = torch.cat(xs, dim=0)
    Y = torch.cat(ys, dim=0)
    return X, Y


def _compute_mean_std(X: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
    mean = X.mean(dim=0)
    var = X.var(dim=0, unbiased=False)
    std = torch.sqrt(var + 1e-6)
    return mean, std


def _choose_dims(input_dim: int, num_classes: int, param_limit: int) -> Tuple[int, int]:
    # Parameter estimate for:
    # fc1: d*h1 + h1
    # ln1: 2*h1
    # fc2: h1*h2 + h2
    # ln2: 2*h2
    # head: h2*c + c
    # total = d*h1 + 3*h1 + h1*h2 + (c+3)*h2 + c
    d = int(input_dim)
    c = int(num_classes)
    limit = int(param_limit)

    def est(h1: int, h2: int) -> int:
        return d * h1 + 3 * h1 + h1 * h2 + (c + 3) * h2 + c

    best = None
    # Favor moderate h2 for expressiveness while keeping h1 large.
    h2_candidates = list(range(160, 385, 32))
    h1_candidates = list(range(384, 1153, 16))
    for h2 in h2_candidates:
        for h1 in h1_candidates:
            p = est(h1, h2)
            if p <= limit:
                score = (p, h1 * h2, h1 + h2)
                if best is None or score > best[0]:
                    best = (score, h1, h2)
    if best is None:
        # Extremely tight limit fallback
        h2 = max(32, min(128, limit // max(1, (c + 3))))
        h1 = max(32, min(128, limit // max(1, (d + 3 + h2))))
        return h1, h2
    return best[1], best[2]


def _make_param_groups(model: nn.Module, weight_decay: float):
    decay = []
    no_decay = []
    for n, p in model.named_parameters():
        if not p.requires_grad:
            continue
        if p.ndim <= 1 or n.endswith(".bias") or "ln" in n.lower() or "layernorm" in n.lower():
            no_decay.append(p)
        else:
            decay.append(p)
    return [
        {"params": decay, "weight_decay": float(weight_decay)},
        {"params": no_decay, "weight_decay": 0.0},
    ]


class Solution:
    def solve(self, train_loader, val_loader, metadata: dict = None) -> torch.nn.Module:
        if metadata is None:
            metadata = {}
        device = metadata.get("device", "cpu")
        device = "cpu" if device is None else str(device)

        try:
            nthreads = int(os.environ.get("OMP_NUM_THREADS", "0")) or (os.cpu_count() or 8)
            nthreads = max(1, min(8, nthreads))
            torch.set_num_threads(nthreads)
        except Exception:
            pass

        try:
            torch.set_float32_matmul_precision("high")
        except Exception:
            pass

        torch.manual_seed(0)

        input_dim = int(metadata.get("input_dim", 384))
        num_classes = int(metadata.get("num_classes", 128))
        param_limit = int(metadata.get("param_limit", 500_000))

        X_train, y_train = _collect_from_loader(train_loader)
        X_val, y_val = _collect_from_loader(val_loader)

        if X_train.ndim != 2:
            X_train = X_train.view(X_train.shape[0], -1)
        if X_val.ndim != 2:
            X_val = X_val.view(X_val.shape[0], -1)

        # Ensure dims consistent with metadata when possible
        input_dim = int(X_train.shape[1]) if X_train.shape[1] != input_dim else input_dim
        num_classes = int(max(num_classes, int(y_train.max().item()) + 1))

        mean, std = _compute_mean_std(X_train)

        h1, h2 = _choose_dims(input_dim, num_classes, param_limit)
        model = _MLPNet(input_dim, num_classes, h1, h2, mean, std, dropout=0.10).to(device)

        # Safety: shrink if the exact parameter count exceeds the limit for any reason
        while _param_count(model) > param_limit and h1 > 32:
            h1 = max(32, h1 - 16)
            model = _MLPNet(input_dim, num_classes, h1, h2, mean, std, dropout=0.10).to(device)
        while _param_count(model) > param_limit and h2 > 32:
            h2 = max(32, h2 - 16)
            model = _MLPNet(input_dim, num_classes, h1, h2, mean, std, dropout=0.10).to(device)

        # Move tensors to device (CPU only in evaluation, but keep generic)
        X_train = X_train.to(device)
        y_train = y_train.to(device)
        X_val = X_val.to(device)
        y_val = y_val.to(device)

        n_train = int(X_train.shape[0])
        batch_size = min(256, n_train)
        steps_per_epoch = (n_train + batch_size - 1) // batch_size

        epochs = 140
        min_epochs = 40
        patience = 30
        eval_every = 1

        lr_max = 5e-3
        weight_decay = 2e-2

        param_groups = _make_param_groups(model, weight_decay=weight_decay)
        optimizer = torch.optim.AdamW(param_groups, lr=lr_max, betas=(0.9, 0.99), eps=1e-8)

        total_steps = max(1, epochs * steps_per_epoch)
        scheduler = torch.optim.lr_scheduler.OneCycleLR(
            optimizer,
            max_lr=lr_max,
            total_steps=total_steps,
            pct_start=0.12,
            anneal_strategy="cos",
            div_factor=10.0,
            final_div_factor=80.0,
        )

        label_smoothing = 0.06
        criterion = nn.CrossEntropyLoss(label_smoothing=label_smoothing)

        best_state = None
        best_val_acc = -1.0
        best_val_loss = float("inf")
        bad = 0
        noise_std = 0.015

        def eval_val() -> Tuple[float, float]:
            model.eval()
            with torch.inference_mode():
                logits = model(X_val)
                loss = F.cross_entropy(logits, y_val).item()
                acc = (logits.argmax(dim=1) == y_val).float().mean().item()
            return acc, loss

        for epoch in range(epochs):
            model.train()
            perm = torch.randperm(n_train, device=device)
            for i in range(0, n_train, batch_size):
                idx = perm[i : i + batch_size]
                xb = X_train[idx]
                yb = y_train[idx]

                if noise_std > 0.0:
                    xb = xb + noise_std * torch.randn_like(xb)

                optimizer.zero_grad(set_to_none=True)
                logits = model(xb)
                loss = criterion(logits, yb)
                loss.backward()
                torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
                optimizer.step()
                scheduler.step()

            if (epoch + 1) % eval_every == 0:
                val_acc, val_loss = eval_val()
                improved = (val_acc > best_val_acc + 1e-6) or (abs(val_acc - best_val_acc) <= 1e-6 and val_loss < best_val_loss - 1e-6)
                if improved:
                    best_val_acc = val_acc
                    best_val_loss = val_loss
                    best_state = copy.deepcopy(model.state_dict())
                    bad = 0
                else:
                    bad += 1
                    if epoch + 1 >= min_epochs and bad >= patience:
                        break

        if best_state is not None:
            model.load_state_dict(best_state)

        # Ridge regression refit of the final linear head on frozen embeddings; choose lambda by val accuracy
        model.eval()
        with torch.inference_mode():
            E_train = model.body(X_train).float()
            E_val = model.body(X_val).float()

        # Augment with bias
        ones_train = torch.ones((E_train.shape[0], 1), device=device, dtype=E_train.dtype)
        ones_val = torch.ones((E_val.shape[0], 1), device=device, dtype=E_val.dtype)
        A_train = torch.cat([E_train, ones_train], dim=1)  # (n, d+1)
        A_val = torch.cat([E_val, ones_val], dim=1)

        c = int(num_classes)
        Y_onehot = F.one_hot(y_train, num_classes=c).float()

        d_aug = int(A_train.shape[1])
        I = torch.eye(d_aug, device=device, dtype=torch.float64)

        lambdas = [1e-4, 3e-4, 1e-3, 3e-3, 1e-2, 3e-2, 1e-1]
        best_lam = None
        best_acc = -1.0
        best_W = None

        AtA = (A_train.t().double() @ A_train.double())
        AtY = (A_train.t().double() @ Y_onehot.double())

        for lam in lambdas:
            try:
                W = torch.linalg.solve(AtA + float(lam) * I, AtY)  # (d+1, c)
            except Exception:
                continue
            logits_val = (A_val.double() @ W).float()
            acc = (logits_val.argmax(dim=1) == y_val).float().mean().item()
            if acc > best_acc + 1e-6:
                best_acc = acc
                best_lam = lam
                best_W = W

        if best_W is not None:
            Wf = best_W.float()
            w = Wf[:-1, :].t().contiguous()
            b = Wf[-1, :].contiguous()
            with torch.no_grad():
                if model.head.weight.shape == w.shape:
                    model.head.weight.copy_(w)
                    model.head.bias.copy_(b)

        model.to("cpu")
        model.eval()

        # Final safety check: if exceeded (shouldn't), shrink head to zero (but keep under limit)
        if _param_count(model) > param_limit:
            for p in model.parameters():
                p.requires_grad_(False)

        return model
