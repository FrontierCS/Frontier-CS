import os
import math
import copy
import time
from typing import Tuple, Optional, Dict, Any

import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import DataLoader, TensorDataset


def _set_torch_threads():
    try:
        n = os.cpu_count() or 1
        torch.set_num_threads(min(8, n))
    except Exception:
        pass
    try:
        torch.set_num_interop_threads(1)
    except Exception:
        pass


def _collect_from_loader(loader: DataLoader) -> Tuple[torch.Tensor, torch.Tensor]:
    xs = []
    ys = []
    for batch in loader:
        if isinstance(batch, (tuple, list)) and len(batch) >= 2:
            x, y = batch[0], batch[1]
        else:
            x, y = batch
        if not torch.is_tensor(x):
            x = torch.as_tensor(x)
        if not torch.is_tensor(y):
            y = torch.as_tensor(y)
        x = x.detach().cpu()
        y = y.detach().cpu()
        x = x.view(x.size(0), -1).to(torch.float32)
        y = y.to(torch.long)
        xs.append(x)
        ys.append(y)
    if len(xs) == 0:
        return torch.empty(0, 0, dtype=torch.float32), torch.empty(0, dtype=torch.long)
    return torch.cat(xs, dim=0), torch.cat(ys, dim=0)


@torch.inference_mode()
def _acc_logits(model: nn.Module, x: torch.Tensor, y: torch.Tensor, batch_size: int = 1024) -> float:
    model.eval()
    n = y.numel()
    if n == 0:
        return 0.0
    correct = 0
    for i in range(0, n, batch_size):
        xb = x[i:i + batch_size]
        yb = y[i:i + batch_size]
        logits = model(xb)
        pred = logits.argmax(dim=1)
        correct += (pred == yb).sum().item()
    return correct / n


class _LDAModel(nn.Module):
    def __init__(self, mean: torch.Tensor, std: torch.Tensor, W: torch.Tensor, b: torch.Tensor):
        super().__init__()
        self.register_buffer("mean", mean.to(torch.float32))
        self.register_buffer("std", std.to(torch.float32))
        self.register_buffer("W", W.to(torch.float32))
        self.register_buffer("b", b.to(torch.float32))

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = x.view(x.size(0), -1).to(self.W.dtype)
        x = (x - self.mean) / self.std
        return x.matmul(self.W) + self.b


class _ResMLP(nn.Module):
    def __init__(self, input_dim: int, num_classes: int, mean: torch.Tensor, std: torch.Tensor,
                 hidden: int = 896, dropout: float = 0.10, blocks: int = 2):
        super().__init__()
        self.register_buffer("mean", mean.to(torch.float32))
        self.register_buffer("std", std.to(torch.float32))

        self.fc_in = nn.Linear(input_dim, hidden)
        self.ln_in = nn.LayerNorm(hidden)
        self.act = nn.GELU()
        self.drop = nn.Dropout(dropout)

        self.blocks = nn.ModuleList([])
        for _ in range(blocks):
            self.blocks.append(nn.Sequential(
                nn.Linear(hidden, hidden),
                nn.GELU(),
                nn.Dropout(dropout),
                nn.LayerNorm(hidden),
            ))

        self.fc_out = nn.Linear(hidden, num_classes)

        self._init_weights()

    def _init_weights(self):
        for m in self.modules():
            if isinstance(m, nn.Linear):
                nn.init.kaiming_normal_(m.weight, nonlinearity="relu")
                if m.bias is not None:
                    nn.init.zeros_(m.bias)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = x.view(x.size(0), -1).to(torch.float32)
        x = (x - self.mean) / self.std
        h = self.fc_in(x)
        h = self.act(h)
        h = self.drop(h)
        h = self.ln_in(h)
        for blk in self.blocks:
            h = h + blk(h)
        return self.fc_out(h)


def _fit_lda_shrinkage(
    X_train_std: torch.Tensor,
    y_train: torch.Tensor,
    X_val_std: torch.Tensor,
    y_val: torch.Tensor,
    num_classes: int,
) -> Tuple[_LDAModel, float]:
    Xtr = X_train_std.to(torch.float64)
    ytr = y_train.to(torch.long)
    Xv = X_val_std.to(torch.float64)
    yv = y_val.to(torch.long)

    N, D = Xtr.shape
    C = num_classes

    counts = torch.bincount(ytr, minlength=C).to(torch.float64)
    counts = torch.clamp(counts, min=1.0)
    priors = counts / counts.sum()
    log_priors = torch.log(priors)

    mu = torch.zeros(C, D, dtype=torch.float64)
    mu.index_add_(0, ytr, Xtr)
    mu = mu / counts.unsqueeze(1)

    mu_y = mu[ytr]
    centered = Xtr - mu_y
    denom = max(1, int(N - C))
    cov = (centered.t().matmul(centered)) / float(denom)
    diag = torch.diag(torch.diag(cov))
    I = torch.eye(D, dtype=torch.float64)

    alphas = [0.0, 0.05, 0.15, 0.35, 0.65, 0.90]
    eps_scales = [1e-4, 5e-4, 2e-3, 1e-2, 5e-2]

    best_acc = -1.0
    best_W = None
    best_b = None

    mean_diag = float(torch.mean(torch.diag(cov)).item())
    if not math.isfinite(mean_diag) or mean_diag <= 0.0:
        mean_diag = 1.0

    for a in alphas:
        base = (1.0 - a) * cov + a * diag
        for es in eps_scales:
            eps = es * mean_diag
            Sigma = base + eps * I
            try:
                L = torch.linalg.cholesky(Sigma)
                W = torch.cholesky_solve(mu.t(), L)  # D x C
                b = -0.5 * torch.sum(mu * W.t(), dim=1) + log_priors  # C

                logits = Xv.matmul(W) + b
                pred = logits.argmax(dim=1)
                acc = (pred == yv).to(torch.float64).mean().item()
                if acc > best_acc:
                    best_acc = acc
                    best_W = W
                    best_b = b
            except Exception:
                continue

    if best_W is None:
        Sigma = cov + 1e-2 * mean_diag * I
        L = torch.linalg.cholesky(Sigma)
        best_W = torch.cholesky_solve(mu.t(), L)
        best_b = -0.5 * torch.sum(mu * best_W.t(), dim=1) + log_priors
        logits = Xv.matmul(best_W) + best_b
        pred = logits.argmax(dim=1)
        best_acc = (pred == yv).to(torch.float64).mean().item()

    dummy_mean = torch.zeros(D, dtype=torch.float32)
    dummy_std = torch.ones(D, dtype=torch.float32)
    model = _LDAModel(dummy_mean, dummy_std, best_W.to(torch.float32), best_b.to(torch.float32))
    return model, float(best_acc)


class Solution:
    def solve(self, train_loader, val_loader, metadata: dict = None) -> torch.nn.Module:
        _set_torch_threads()
        torch.manual_seed(0)

        if metadata is None:
            metadata = {}
        input_dim = int(metadata.get("input_dim", 384))
        num_classes = int(metadata.get("num_classes", 128))
        param_limit = int(metadata.get("param_limit", 2_500_000))

        X_train, y_train = _collect_from_loader(train_loader)
        X_val, y_val = _collect_from_loader(val_loader)

        if X_train.numel() == 0:
            model = nn.Linear(input_dim, num_classes)
            return model

        mean = X_train.mean(dim=0)
        std = X_train.std(dim=0, unbiased=False).clamp_min(1e-6)

        X_train_std = (X_train - mean) / std
        X_val_std = (X_val - mean) / std

        lda_model_std, lda_val_acc = _fit_lda_shrinkage(X_train_std, y_train, X_val_std, y_val, num_classes)
        lda_model = _LDAModel(mean, std, lda_model_std.W.detach(), lda_model_std.b.detach())
        best_model = lda_model
        best_val_acc = lda_val_acc

        # Train MLP and pick the better validation model
        train_ds = TensorDataset(X_train, y_train)
        val_ds = TensorDataset(X_val, y_val)
        bs = 256
        train_dl = DataLoader(train_ds, batch_size=bs, shuffle=True, num_workers=0, drop_last=False)
        val_x = X_val
        val_y = y_val

        mlp = _ResMLP(input_dim=input_dim, num_classes=num_classes, mean=mean, std=std, hidden=896, dropout=0.10, blocks=2)

        param_count = sum(p.numel() for p in mlp.parameters() if p.requires_grad)
        if param_count <= param_limit:
            criterion = nn.CrossEntropyLoss(label_smoothing=0.10)
            optimizer = torch.optim.AdamW(mlp.parameters(), lr=2.5e-3, weight_decay=2e-4)
            max_epochs = 120
            warmup_epochs = 6

            def lr_lambda(epoch: int):
                if epoch < warmup_epochs:
                    return float(epoch + 1) / float(max(1, warmup_epochs))
                t = (epoch - warmup_epochs) / float(max(1, max_epochs - warmup_epochs))
                return 0.5 * (1.0 + math.cos(math.pi * t))

            scheduler = torch.optim.lr_scheduler.LambdaLR(optimizer, lr_lambda=lr_lambda)

            best_state = None
            best_mlp_val = -1.0
            patience = 18
            bad = 0

            for epoch in range(max_epochs):
                mlp.train()
                for xb, yb in train_dl:
                    xb = xb.view(xb.size(0), -1).to(torch.float32)
                    yb = yb.to(torch.long)

                    optimizer.zero_grad(set_to_none=True)
                    logits = mlp(xb)
                    loss = criterion(logits, yb)
                    loss.backward()
                    torch.nn.utils.clip_grad_norm_(mlp.parameters(), 1.0)
                    optimizer.step()

                scheduler.step()

                val_acc = _acc_logits(mlp, val_x, val_y, batch_size=1024)
                if val_acc > best_mlp_val + 1e-4:
                    best_mlp_val = val_acc
                    best_state = copy.deepcopy(mlp.state_dict())
                    bad = 0
                else:
                    bad += 1
                    if bad >= patience:
                        break

            if best_state is not None:
                mlp.load_state_dict(best_state)

            mlp_val_acc = _acc_logits(mlp, val_x, val_y, batch_size=1024)
            if mlp_val_acc > best_val_acc + 1e-4:
                best_model = mlp
                best_val_acc = mlp_val_acc

        best_model.eval()
        return best_model
