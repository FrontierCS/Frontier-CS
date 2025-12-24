import math
import os
import random
from dataclasses import dataclass
from typing import Dict, Optional, Tuple

import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import DataLoader, TensorDataset


def _set_torch_threads():
    try:
        n = os.cpu_count() or 8
        torch.set_num_threads(min(8, max(1, n)))
        torch.set_num_interop_threads(min(8, max(1, n)))
    except Exception:
        pass


def _to_tensor(x, dtype=None, device=None):
    if torch.is_tensor(x):
        t = x
        if dtype is not None and t.dtype != dtype:
            t = t.to(dtype=dtype)
        if device is not None and t.device != torch.device(device):
            t = t.to(device=device)
        return t
    t = torch.as_tensor(x, dtype=dtype)
    if device is not None:
        t = t.to(device=device)
    return t


def _gather_from_loader(loader: DataLoader, device: str = "cpu") -> Tuple[torch.Tensor, torch.Tensor]:
    xs = []
    ys = []
    for batch in loader:
        if isinstance(batch, (list, tuple)) and len(batch) >= 2:
            x, y = batch[0], batch[1]
        else:
            raise ValueError("Expected loader to yield (inputs, targets).")
        x = _to_tensor(x, dtype=torch.float32, device=device)
        y = _to_tensor(y, dtype=torch.long, device=device)
        xs.append(x)
        ys.append(y)
    x_all = torch.cat(xs, dim=0) if xs else torch.empty((0,), dtype=torch.float32, device=device)
    y_all = torch.cat(ys, dim=0) if ys else torch.empty((0,), dtype=torch.long, device=device)
    return x_all, y_all


def _param_count_trainable(model: nn.Module) -> int:
    return sum(p.numel() for p in model.parameters() if p.requires_grad)


def _choose_hidden_dims(input_dim: int, num_classes: int, param_limit: int) -> Tuple[int, int]:
    best = None
    best_params = -1

    h_min = 128
    h_max = 1024
    step = 16

    def count_params(h1: int, h2: int) -> int:
        # Linear params
        p = (input_dim * h1 + h1) + (h1 * h2 + h2) + (h2 * num_classes + num_classes)
        # LayerNorm params (weight+bias)
        p += 2 * h1 + 2 * h2
        return p

    # Prefer reasonable shapes for CPU GEMM
    for h1 in range(h_max, h_min - 1, -step):
        for h2 in range(h_max, h_min - 1, -step):
            p = count_params(h1, h2)
            if p <= param_limit and p > best_params:
                best_params = p
                best = (h1, h2)

    if best is None:
        # Fallback: tiny dims
        best = (h_min, h_min)
    return best


class _NormalizedMLP(nn.Module):
    def __init__(self, input_dim: int, num_classes: int, h1: int, h2: int, dropout: float):
        super().__init__()
        self.input_dim = input_dim
        self.num_classes = num_classes
        self.h1 = h1
        self.h2 = h2

        self.register_buffer("mean", torch.zeros(input_dim, dtype=torch.float32))
        self.register_buffer("inv_std", torch.ones(input_dim, dtype=torch.float32))

        self.fc1 = nn.Linear(input_dim, h1, bias=True)
        self.ln1 = nn.LayerNorm(h1, elementwise_affine=True)
        self.fc2 = nn.Linear(h1, h2, bias=True)
        self.ln2 = nn.LayerNorm(h2, elementwise_affine=True)
        self.fc3 = nn.Linear(h2, num_classes, bias=True)

        self.drop = nn.Dropout(p=float(dropout))
        self.act = nn.GELU()

        self._init_weights()

    def _init_weights(self):
        for m in self.modules():
            if isinstance(m, nn.Linear):
                nn.init.kaiming_normal_(m.weight, nonlinearity="relu")
                if m.bias is not None:
                    nn.init.zeros_(m.bias)
            elif isinstance(m, nn.LayerNorm):
                nn.init.ones_(m.weight)
                nn.init.zeros_(m.bias)

    def set_normalization(self, mean: torch.Tensor, std: torch.Tensor, eps: float = 1e-6):
        mean = mean.detach().to(dtype=torch.float32, device=self.mean.device)
        std = std.detach().to(dtype=torch.float32, device=self.mean.device)
        inv_std = 1.0 / torch.clamp(std, min=eps)
        if mean.numel() != self.mean.numel():
            raise ValueError("Mean has wrong shape.")
        self.mean.copy_(mean)
        self.inv_std.copy_(inv_std)

    def normalize(self, x: torch.Tensor) -> torch.Tensor:
        return (x - self.mean) * self.inv_std

    def embed(self, x: torch.Tensor) -> torch.Tensor:
        x = self.normalize(x)
        x = self.fc1(x)
        x = self.ln1(x)
        x = self.act(x)
        x = self.drop(x)
        x = self.fc2(x)
        x = self.ln2(x)
        x = self.act(x)
        x = self.drop(x)
        return x

    def forward_with_embed(self, x: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        e = self.embed(x)
        logits = self.fc3(e)
        return logits, e

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        e = self.embed(x)
        return self.fc3(e)


class _HybridProtoModel(nn.Module):
    def __init__(
        self,
        base: _NormalizedMLP,
        centroids: torch.Tensor,
        centroids_norm: torch.Tensor,
        centroids_sq: torch.Tensor,
        metric: str,
        beta: float,
        scale: float,
        gamma: float,
    ):
        super().__init__()
        self.base = base

        self.register_buffer("centroids", centroids)
        self.register_buffer("centroids_norm", centroids_norm)
        self.register_buffer("centroids_sq", centroids_sq)

        self.metric = metric
        self.register_buffer("beta", torch.tensor(float(beta), dtype=torch.float32))
        self.register_buffer("scale", torch.tensor(float(scale), dtype=torch.float32))
        self.register_buffer("gamma", torch.tensor(float(gamma), dtype=torch.float32))

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        logits, emb = self.base.forward_with_embed(x)
        logits = logits * self.gamma

        if float(self.beta.item()) == 0.0:
            return logits

        if self.metric == "cosine":
            emb_n = F.normalize(emb, dim=1)
            proto = (emb_n @ self.centroids_norm.t()) * self.scale
        elif self.metric == "sqdist":
            # -||e-c||^2 = 2 e·c - ||c||^2 - ||e||^2 ; drop ||e||^2 (constant across classes)
            proto = (2.0 * (emb @ self.centroids.t()) - self.centroids_sq.unsqueeze(0)) / torch.clamp(self.scale, min=1e-6)
        else:  # "dot"
            proto = (emb @ self.centroids.t()) / torch.clamp(self.scale, min=1e-6)

        return logits + self.beta * proto


@dataclass
class _TrainConfig:
    batch_size: int = 128
    max_epochs: int = 160
    patience: int = 25
    lr: float = 2.5e-3
    weight_decay: float = 1.5e-2
    label_smoothing: float = 0.05
    dropout: float = 0.08
    mixup_alpha: float = 0.2
    mixup_prob: float = 0.65
    grad_clip: float = 1.0
    warmup_frac: float = 0.08


class Solution:
    def solve(self, train_loader, val_loader, metadata: dict = None) -> torch.nn.Module:
        _set_torch_threads()

        metadata = metadata or {}
        device = metadata.get("device", "cpu")
        input_dim = int(metadata.get("input_dim", 384))
        num_classes = int(metadata.get("num_classes", 128))
        param_limit = int(metadata.get("param_limit", 500000))

        train_x, train_y = _gather_from_loader(train_loader, device=device)
        if train_x.ndim != 2:
            train_x = train_x.view(train_x.shape[0], -1)
        train_x = train_x.to(dtype=torch.float32)
        train_y = train_y.to(dtype=torch.long)

        if val_loader is not None:
            val_x, val_y = _gather_from_loader(val_loader, device=device)
            if val_x.ndim != 2:
                val_x = val_x.view(val_x.shape[0], -1)
            val_x = val_x.to(dtype=torch.float32)
            val_y = val_y.to(dtype=torch.long)
        else:
            val_x, val_y = train_x, train_y

        if metadata.get("input_dim") is None:
            input_dim = int(train_x.shape[1])

        # Normalization stats
        mean = train_x.mean(dim=0)
        std = train_x.std(dim=0, unbiased=False)

        cfg = _TrainConfig()
        cfg.batch_size = int(min(max(32, cfg.batch_size), max(32, train_x.shape[0])))

        h1, h2 = _choose_hidden_dims(input_dim, num_classes, param_limit)
        base = _NormalizedMLP(input_dim=input_dim, num_classes=num_classes, h1=h1, h2=h2, dropout=cfg.dropout).to(device)
        base.set_normalization(mean, std)

        # Verify parameter budget
        pc = _param_count_trainable(base)
        if pc > param_limit:
            # Fallback to smaller dims
            h1, h2 = 256, 256
            base = _NormalizedMLP(input_dim=input_dim, num_classes=num_classes, h1=h1, h2=h2, dropout=cfg.dropout).to(device)
            base.set_normalization(mean, std)
            pc = _param_count_trainable(base)
            if pc > param_limit:
                # Extreme fallback: linear classifier
                base = _NormalizedMLP(input_dim=input_dim, num_classes=num_classes, h1=128, h2=128, dropout=0.0).to(device)
                base.set_normalization(mean, std)

        train_ds = TensorDataset(train_x, train_y)
        train_dl = DataLoader(train_ds, batch_size=cfg.batch_size, shuffle=True, num_workers=0, drop_last=False)

        val_ds = TensorDataset(val_x, val_y)
        val_dl = DataLoader(val_ds, batch_size=512, shuffle=False, num_workers=0, drop_last=False)

        optimizer = torch.optim.AdamW(base.parameters(), lr=cfg.lr, weight_decay=cfg.weight_decay, betas=(0.9, 0.95))

        total_steps = cfg.max_epochs * max(1, len(train_dl))
        warmup_steps = max(1, int(cfg.warmup_frac * total_steps))

        def lr_at(step: int) -> float:
            if step < warmup_steps:
                return cfg.lr * float(step + 1) / float(warmup_steps)
            t = float(step - warmup_steps) / float(max(1, total_steps - warmup_steps))
            return cfg.lr * 0.5 * (1.0 + math.cos(math.pi * min(1.0, max(0.0, t))))

        def eval_acc(model: nn.Module) -> float:
            model.eval()
            correct = 0
            total = 0
            with torch.inference_mode():
                for xb, yb in val_dl:
                    logits = model(xb)
                    pred = logits.argmax(dim=1)
                    correct += (pred == yb).sum().item()
                    total += yb.numel()
            return float(correct) / float(max(1, total))

        def mixup_batch(xb: torch.Tensor, yb: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor, float]:
            if cfg.mixup_alpha <= 0:
                return xb, yb, yb, 1.0
            lam = float(torch.distributions.Beta(cfg.mixup_alpha, cfg.mixup_alpha).sample().item())
            idx = torch.randperm(xb.shape[0], device=xb.device)
            mixed = lam * xb + (1.0 - lam) * xb[idx]
            return mixed, yb, yb[idx], lam

        best_acc = -1.0
        best_state = None
        bad_epochs = 0
        step = 0

        for epoch in range(cfg.max_epochs):
            base.train()
            for xb, yb in train_dl:
                xb = xb.to(dtype=torch.float32)
                yb = yb.to(dtype=torch.long)

                lr = lr_at(step)
                for pg in optimizer.param_groups:
                    pg["lr"] = lr

                do_mix = (cfg.mixup_prob > 0.0) and (random.random() < cfg.mixup_prob) and (xb.shape[0] >= 2)
                optimizer.zero_grad(set_to_none=True)

                if do_mix:
                    xm, ya, yb2, lam = mixup_batch(xb, yb)
                    logits = base(xm)
                    loss = lam * F.cross_entropy(logits, ya, label_smoothing=cfg.label_smoothing) + (1.0 - lam) * F.cross_entropy(
                        logits, yb2, label_smoothing=cfg.label_smoothing
                    )
                else:
                    logits = base(xb)
                    loss = F.cross_entropy(logits, yb, label_smoothing=cfg.label_smoothing)

                loss.backward()
                if cfg.grad_clip is not None and cfg.grad_clip > 0:
                    torch.nn.utils.clip_grad_norm_(base.parameters(), max_norm=cfg.grad_clip)
                optimizer.step()

                step += 1

            acc = eval_acc(base)
            if acc > best_acc + 1e-5:
                best_acc = acc
                best_state = {k: v.detach().clone() for k, v in base.state_dict().items()}
                bad_epochs = 0
            else:
                bad_epochs += 1

            if best_acc >= 0.995:
                break
            if bad_epochs >= cfg.patience:
                break

        if best_state is not None:
            base.load_state_dict(best_state)

        # Build prototypical centroids from embedding space using train set
        base.eval()
        with torch.inference_mode():
            _, emb_train = base.forward_with_embed(train_x)
        centroids = torch.zeros((num_classes, emb_train.shape[1]), device=device, dtype=torch.float32)
        counts = torch.zeros((num_classes,), device=device, dtype=torch.float32)
        centroids.index_add_(0, train_y, emb_train)
        ones = torch.ones((train_y.shape[0],), device=device, dtype=torch.float32)
        counts.index_add_(0, train_y, ones)
        centroids = centroids / torch.clamp(counts.unsqueeze(1), min=1.0)

        centroids_norm = F.normalize(centroids, dim=1)
        centroids_sq = (centroids * centroids).sum(dim=1)

        # Tune blending on validation (fast grid with reuse)
        base.eval()
        with torch.inference_mode():
            logits_val, emb_val = base.forward_with_embed(val_x)
            emb_val_n = F.normalize(emb_val, dim=1)
            sim_cos = emb_val_n @ centroids_norm.t()
            sim_dot = emb_val @ centroids.t()
            sim_sq = 2.0 * sim_dot - centroids_sq.unsqueeze(0)

        betas = [0.0, 0.25, 0.5, 1.0, 2.0, 4.0]
        gammas = [1.0, 0.85, 1.15]
        scales_cos = [1.0, 2.0, 4.0, 8.0, 16.0]
        scales_other = [0.5, 1.0, 2.0, 4.0, 8.0]

        best = ("cosine", 0.0, 1.0, 1.0, best_acc)
        yv = val_y

        def acc_from_logits(lg: torch.Tensor) -> float:
            pred = lg.argmax(dim=1)
            return float((pred == yv).float().mean().item())

        # cosine metric
        for gamma in gammas:
            lg0 = logits_val * gamma
            for scale in scales_cos:
                proto = sim_cos * scale
                for beta in betas:
                    lg = lg0 if beta == 0.0 else (lg0 + beta * proto)
                    a = acc_from_logits(lg)
                    if a > best[4] + 1e-6:
                        best = ("cosine", beta, scale, gamma, a)

        # sqdist metric
        for gamma in gammas:
            lg0 = logits_val * gamma
            for scale in scales_other:
                proto = sim_sq / max(1e-6, scale)
                for beta in betas:
                    lg = lg0 if beta == 0.0 else (lg0 + beta * proto)
                    a = acc_from_logits(lg)
                    if a > best[4] + 1e-6:
                        best = ("sqdist", beta, scale, gamma, a)

        metric, beta, scale, gamma, _ = best

        model = _HybridProtoModel(
            base=base,
            centroids=centroids,
            centroids_norm=centroids_norm,
            centroids_sq=centroids_sq,
            metric=metric,
            beta=float(beta),
            scale=float(scale),
            gamma=float(gamma),
        ).to(device)

        # Final safety: ensure trainable params within limit
        if _param_count_trainable(model) > param_limit:
            # Return base only (should never happen)
            base.eval()
            return base

        model.eval()
        return model
