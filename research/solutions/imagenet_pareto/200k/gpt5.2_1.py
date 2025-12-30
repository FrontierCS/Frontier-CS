import math
import os
import random
from typing import Optional, Tuple, List, Dict

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import DataLoader, TensorDataset


def _seed_all(seed: int = 0) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)


def _count_trainable_params(model: nn.Module) -> int:
    return sum(p.numel() for p in model.parameters() if p.requires_grad)


def _unpack_batch(batch):
    if isinstance(batch, (tuple, list)) and len(batch) >= 2:
        return batch[0], batch[1]
    raise ValueError("Unexpected batch format")


def _collect_loader(loader) -> Tuple[torch.Tensor, torch.Tensor]:
    xs = []
    ys = []
    for batch in loader:
        x, y = _unpack_batch(batch)
        if not torch.is_tensor(x):
            x = torch.as_tensor(x)
        if not torch.is_tensor(y):
            y = torch.as_tensor(y)
        xs.append(x.detach().cpu())
        ys.append(y.detach().cpu())
    X = torch.cat(xs, dim=0).to(dtype=torch.float32, copy=False)
    y = torch.cat(ys, dim=0).to(dtype=torch.long, copy=False)
    return X, y


def _make_mean_std(X: torch.Tensor, eps: float = 1e-6) -> Tuple[torch.Tensor, torch.Tensor]:
    mean = X.mean(dim=0)
    var = X.var(dim=0, unbiased=False)
    std = torch.sqrt(var + eps)
    std = std.clamp_min(eps)
    return mean, std


def _normalize_l2(X: torch.Tensor, mean: torch.Tensor, std: torch.Tensor, eps: float = 1e-6) -> torch.Tensor:
    Xn = (X - mean) / std
    denom = Xn.norm(dim=1, keepdim=True).clamp_min(eps)
    Xn = Xn / denom
    return Xn


def _compute_prototypes(Xn: torch.Tensor, y: torch.Tensor, num_classes: int, eps: float = 1e-6) -> torch.Tensor:
    d = Xn.shape[1]
    sums = torch.zeros(num_classes, d, dtype=torch.float32)
    counts = torch.zeros(num_classes, dtype=torch.float32)
    sums.index_add_(0, y, Xn)
    ones = torch.ones_like(y, dtype=torch.float32)
    counts.index_add_(0, y, ones)
    protos = sums / counts.clamp_min(1.0).unsqueeze(1)
    protos = protos / protos.norm(dim=1, keepdim=True).clamp_min(eps)
    return protos


@torch.inference_mode()
def _eval_accuracy(model: nn.Module, loader: DataLoader, device: str = "cpu") -> float:
    model.eval()
    correct = 0
    total = 0
    for batch in loader:
        x, y = _unpack_batch(batch)
        x = x.to(device=device, dtype=torch.float32, non_blocking=False)
        y = y.to(device=device, dtype=torch.long, non_blocking=False)
        logits = model(x)
        pred = logits.argmax(dim=1)
        correct += (pred == y).sum().item()
        total += y.numel()
    return float(correct) / float(max(1, total))


class _EMA:
    def __init__(self, model: nn.Module, decay: float = 0.995):
        self.decay = float(decay)
        self.shadow: Dict[str, torch.Tensor] = {}
        for name, p in model.named_parameters():
            if p.requires_grad:
                self.shadow[name] = p.detach().clone()

        self._backup: Optional[Dict[str, torch.Tensor]] = None

    @torch.no_grad()
    def update(self, model: nn.Module):
        d = self.decay
        for name, p in model.named_parameters():
            if not p.requires_grad:
                continue
            sp = self.shadow[name]
            sp.mul_(d).add_(p.detach(), alpha=(1.0 - d))

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

    def state_dict(self):
        return {k: v.clone() for k, v in self.shadow.items()}

    @torch.no_grad()
    def load_state_dict(self, state: Dict[str, torch.Tensor]):
        self.shadow = {k: v.clone() for k, v in state.items()}


class _PreprocessMixin:
    def _preprocess(self, x: torch.Tensor) -> torch.Tensor:
        x = x.to(dtype=torch.float32)
        x = (x - self.mean) / self.std
        if self.training and getattr(self, "noise_std", 0.0) > 0.0:
            x = x + torch.randn_like(x) * float(self.noise_std)
        x = x / x.norm(dim=1, keepdim=True).clamp_min(1e-6)
        return x


class KNNClassifier(nn.Module, _PreprocessMixin):
    def __init__(
        self,
        mean: torch.Tensor,
        std: torch.Tensor,
        mem_features: torch.Tensor,
        mem_labels: torch.Tensor,
        num_classes: int,
        k: int = 7,
        tau: float = 0.2,
        logit_scale: float = 20.0,
    ):
        super().__init__()
        self.register_buffer("mean", mean.clone().to(dtype=torch.float32), persistent=True)
        self.register_buffer("std", std.clone().to(dtype=torch.float32), persistent=True)
        self.register_buffer("mem_features", mem_features.clone().to(dtype=torch.float32), persistent=True)
        self.register_buffer("mem_labels", mem_labels.clone().to(dtype=torch.long), persistent=True)
        self.num_classes = int(num_classes)
        self.k = int(k)
        self.tau = float(tau)
        self.logit_scale = float(logit_scale)
        self.noise_std = 0.0

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self._preprocess(x)
        sims = x @ self.mem_features.t()
        top_sims, top_idx = sims.topk(self.k, dim=1, largest=True, sorted=False)
        top_lbl = self.mem_labels[top_idx]
        weights = F.softmax(top_sims / max(1e-6, self.tau), dim=1)
        logits = x.new_zeros((x.shape[0], self.num_classes))
        logits.scatter_add_(1, top_lbl, weights)
        return logits * self.logit_scale


class ProtoClassifier(nn.Module, _PreprocessMixin):
    def __init__(
        self,
        mean: torch.Tensor,
        std: torch.Tensor,
        prototypes: torch.Tensor,
        logit_scale: float = 20.0,
    ):
        super().__init__()
        self.register_buffer("mean", mean.clone().to(dtype=torch.float32), persistent=True)
        self.register_buffer("std", std.clone().to(dtype=torch.float32), persistent=True)
        self.register_buffer("prototypes", prototypes.clone().to(dtype=torch.float32), persistent=True)
        self.logit_scale = float(logit_scale)
        self.noise_std = 0.0

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self._preprocess(x)
        return (x @ self.prototypes.t()) * self.logit_scale


class _ResMLP(nn.Module):
    def __init__(self, input_dim: int, hidden_dim: int, num_blocks: int, dropout: float = 0.10):
        super().__init__()
        self.fc_in = nn.Linear(input_dim, hidden_dim, bias=True)
        self.ln_in = nn.LayerNorm(hidden_dim, elementwise_affine=True)
        self.blocks = nn.ModuleList([])
        for _ in range(num_blocks):
            self.blocks.append(nn.Linear(hidden_dim, hidden_dim, bias=True))
            self.blocks.append(nn.LayerNorm(hidden_dim, elementwise_affine=True))
        self.ln_out = nn.LayerNorm(hidden_dim, elementwise_affine=True)
        self.dropout = nn.Dropout(p=float(dropout))

        for m in self.modules():
            if isinstance(m, nn.Linear):
                nn.init.kaiming_normal_(m.weight, nonlinearity="relu")
                if m.bias is not None:
                    nn.init.zeros_(m.bias)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self.fc_in(x)
        x = self.ln_in(x)
        x = F.gelu(x)
        x = self.dropout(x)
        for i in range(0, len(self.blocks), 2):
            fc = self.blocks[i]
            ln = self.blocks[i + 1]
            y = fc(x)
            y = ln(y)
            y = F.gelu(y)
            y = self.dropout(y)
            x = x + y
        x = self.ln_out(x)
        return x


class ProtoResMLP(nn.Module, _PreprocessMixin):
    def __init__(
        self,
        mean: torch.Tensor,
        std: torch.Tensor,
        prototypes: torch.Tensor,
        input_dim: int,
        hidden_dim: int,
        num_blocks: int,
        num_classes: int,
        dropout: float = 0.10,
        noise_std: float = 0.02,
    ):
        super().__init__()
        self.register_buffer("mean", mean.clone().to(dtype=torch.float32), persistent=True)
        self.register_buffer("std", std.clone().to(dtype=torch.float32), persistent=True)
        self.register_buffer("prototypes", prototypes.clone().to(dtype=torch.float32), persistent=True)

        self.noise_std = float(noise_std)
        self.mlp = _ResMLP(input_dim=input_dim, hidden_dim=hidden_dim, num_blocks=num_blocks, dropout=dropout)
        self.head = nn.Linear(hidden_dim, num_classes, bias=True)

        self.alpha = nn.Parameter(torch.tensor(0.5, dtype=torch.float32))
        self.logit_scale = nn.Parameter(torch.tensor(math.log(15.0), dtype=torch.float32))

        nn.init.zeros_(self.head.bias)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self._preprocess(x)
        h = self.mlp(x)
        mlp_logits = self.head(h)
        scale = self.logit_scale.exp().clamp(1.0, 100.0)
        proto_logits = (x @ self.prototypes.t()) * scale
        return mlp_logits + self.alpha * proto_logits


class ProtoRFF(nn.Module, _PreprocessMixin):
    def __init__(
        self,
        mean: torch.Tensor,
        std: torch.Tensor,
        prototypes: torch.Tensor,
        input_dim: int,
        rff_dim: int,
        num_classes: int,
        sigma: float = 1.0,
        dropout: float = 0.05,
        noise_std: float = 0.02,
    ):
        super().__init__()
        self.register_buffer("mean", mean.clone().to(dtype=torch.float32), persistent=True)
        self.register_buffer("std", std.clone().to(dtype=torch.float32), persistent=True)
        self.register_buffer("prototypes", prototypes.clone().to(dtype=torch.float32), persistent=True)

        self.noise_std = float(noise_std)
        self.rff_dim = int(rff_dim)

        W = torch.randn(self.rff_dim, input_dim, dtype=torch.float32) / max(1e-6, float(sigma))
        b = torch.rand(self.rff_dim, dtype=torch.float32) * (2.0 * math.pi)
        self.register_buffer("W", W, persistent=True)
        self.register_buffer("b", b, persistent=True)
        self.register_buffer("rff_scale", torch.tensor(math.sqrt(2.0 / float(self.rff_dim)), dtype=torch.float32), persistent=True)

        self.norm = nn.LayerNorm(self.rff_dim, elementwise_affine=False)
        self.dropout = nn.Dropout(p=float(dropout))
        self.head = nn.Linear(self.rff_dim, num_classes, bias=True)

        self.alpha = nn.Parameter(torch.tensor(0.5, dtype=torch.float32))
        self.logit_scale = nn.Parameter(torch.tensor(math.log(15.0), dtype=torch.float32))

        nn.init.zeros_(self.head.bias)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self._preprocess(x)
        z = F.linear(x, self.W, self.b)
        z = torch.cos(z) * self.rff_scale
        z = self.norm(z)
        z = self.dropout(z)
        logits = self.head(z)
        scale = self.logit_scale.exp().clamp(1.0, 100.0)
        proto_logits = (x @ self.prototypes.t()) * scale
        return logits + self.alpha * proto_logits


def _train_model(
    model: nn.Module,
    train_loader: DataLoader,
    val_loader: Optional[DataLoader],
    device: str,
    max_epochs: int,
    base_lr: float,
    weight_decay: float,
    label_smoothing: float = 0.05,
    mixup_alpha: float = 0.2,
    mixup_prob: float = 0.5,
    grad_clip: float = 1.0,
    ema_decay: float = 0.995,
    patience: int = 15,
) -> Tuple[Dict[str, torch.Tensor], float]:
    model.to(device)
    criterion = nn.CrossEntropyLoss(label_smoothing=float(label_smoothing))

    opt = torch.optim.AdamW(model.parameters(), lr=float(base_lr), weight_decay=float(weight_decay))
    steps_per_epoch = max(1, len(train_loader))
    total_steps = max_epochs * steps_per_epoch
    warmup_steps = max(10, int(0.10 * total_steps))

    def lr_lambda(step: int) -> float:
        if total_steps <= 1:
            return 1.0
        if step < warmup_steps:
            return float(step + 1) / float(max(1, warmup_steps))
        denom = max(1, total_steps - warmup_steps)
        t = float(step - warmup_steps) / float(denom)
        return 0.5 * (1.0 + math.cos(math.pi * min(1.0, max(0.0, t))))

    sched = torch.optim.lr_scheduler.LambdaLR(opt, lr_lambda=lr_lambda)

    ema = _EMA(model, decay=ema_decay)

    best_acc = -1.0
    best_state = None
    bad = 0

    for epoch in range(max_epochs):
        model.train()
        for batch in train_loader:
            x, y = _unpack_batch(batch)
            x = x.to(device=device, dtype=torch.float32, non_blocking=False)
            y = y.to(device=device, dtype=torch.long, non_blocking=False)

            do_mix = (mixup_alpha > 0.0) and (mixup_prob > 0.0) and (np.random.rand() < mixup_prob) and (x.shape[0] > 1)
            if do_mix:
                lam = float(np.random.beta(mixup_alpha, mixup_alpha))
                perm = torch.randperm(x.shape[0], device=device)
                x2 = x[perm]
                y2 = y[perm]
                x_mix = x.mul(lam).add(x2, alpha=(1.0 - lam))
                logits = model(x_mix)
                loss = lam * criterion(logits, y) + (1.0 - lam) * criterion(logits, y2)
            else:
                logits = model(x)
                loss = criterion(logits, y)

            opt.zero_grad(set_to_none=True)
            loss.backward()
            if grad_clip is not None and grad_clip > 0.0:
                torch.nn.utils.clip_grad_norm_(model.parameters(), float(grad_clip))
            opt.step()
            sched.step()
            ema.update(model)

        if val_loader is not None:
            ema.apply_to(model)
            acc = _eval_accuracy(model, val_loader, device=device)
            ema.restore(model)

            if acc > best_acc + 1e-4:
                best_acc = acc
                best_state = ema.state_dict()
                bad = 0
            else:
                bad += 1
                if bad >= patience:
                    break

    if val_loader is None:
        best_state = ema.state_dict()
        best_acc = float("nan")
    elif best_state is None:
        best_state = ema.state_dict()

    return best_state, best_acc


def _apply_ema_state(model: nn.Module, ema_state: Dict[str, torch.Tensor]) -> None:
    with torch.no_grad():
        for name, p in model.named_parameters():
            if p.requires_grad and name in ema_state:
                p.copy_(ema_state[name])


def _max_hidden_for_resmlp(
    input_dim: int,
    num_classes: int,
    blocks: int,
    param_limit: int,
    extra_params: int = 2,
) -> int:
    # Params:
    # fc_in: in*h + h
    # blocks: B*(h*h + h)
    # head: h*num + num
    # layernorms: (B+2) * 2h
    # plus extras (alpha, logit_scale)
    B = int(blocks)

    def params(h: int) -> int:
        h = int(h)
        total = 0
        total += input_dim * h + h
        total += B * (h * h + h)
        total += h * num_classes + num_classes
        total += (B + 2) * (2 * h)
        total += extra_params
        return int(total)

    lo, hi = 16, 2048
    while params(hi) <= param_limit:
        hi *= 2
        if hi > 16384:
            break
    lo, hi = 16, hi
    best = lo
    while lo <= hi:
        mid = (lo + hi) // 2
        if params(mid) <= param_limit:
            best = mid
            lo = mid + 1
        else:
            hi = mid - 1
    return int(best)


class Solution:
    def solve(self, train_loader, val_loader, metadata: dict = None) -> nn.Module:
        if metadata is None:
            metadata = {}
        device = str(metadata.get("device", "cpu"))
        input_dim = int(metadata.get("input_dim", 384))
        num_classes = int(metadata.get("num_classes", 128))
        param_limit = int(metadata.get("param_limit", 200_000))

        try:
            torch.set_num_threads(min(8, os.cpu_count() or 8))
        except Exception:
            pass

        _seed_all(0)

        X_tr, y_tr = _collect_loader(train_loader)
        X_va, y_va = _collect_loader(val_loader)

        X_all = torch.cat([X_tr, X_va], dim=0)
        mean, std = _make_mean_std(X_all)

        Xn_tr = _normalize_l2(X_tr, mean, std)
        Xn_va = _normalize_l2(X_va, mean, std)

        protos_tr = _compute_prototypes(Xn_tr, y_tr, num_classes=num_classes)

        train_ds = TensorDataset(X_tr, y_tr)
        val_ds = TensorDataset(X_va, y_va)
        bs = 256
        train_dl = DataLoader(train_ds, batch_size=min(bs, len(train_ds)), shuffle=True, num_workers=0)
        val_dl = DataLoader(val_ds, batch_size=min(512, len(val_ds)), shuffle=False, num_workers=0)

        # Baseline: prototype-only
        proto_model = ProtoClassifier(mean=mean, std=std, prototypes=protos_tr, logit_scale=20.0).to(device)
        proto_acc = _eval_accuracy(proto_model, val_dl, device=device)

        # kNN search (train-only memory for fair val selection)
        max_k = 7
        ks = [1, 3, 7]
        taus = [0.1, 0.2]
        best_knn_acc = -1.0
        best_knn_k = 3
        best_knn_tau = 0.2

        with torch.inference_mode():
            # pre-normalized features already in Xn_tr / Xn_va
            memF = Xn_tr.to(dtype=torch.float32)
            memY = y_tr.to(dtype=torch.long)

            total = 0
            correct = {(k, tau): 0 for k in ks for tau in taus}
            for i in range(0, Xn_va.shape[0], 256):
                xb = Xn_va[i : i + 256]
                yb = y_va[i : i + 256]
                sims = xb @ memF.t()
                top_sims, top_idx = sims.topk(max_k, dim=1, largest=True, sorted=False)
                top_lbl = memY[top_idx]  # [B, max_k]
                for k in ks:
                    lbl_k = top_lbl[:, :k]
                    sim_k = top_sims[:, :k]
                    for tau in taus:
                        w = F.softmax(sim_k / max(1e-6, float(tau)), dim=1)
                        logits = xb.new_zeros((xb.shape[0], num_classes))
                        logits.scatter_add_(1, lbl_k, w)
                        pred = logits.argmax(dim=1).cpu()
                        correct[(k, tau)] += int((pred == yb).sum().item())
                total += int(yb.numel())

            for k in ks:
                for tau in taus:
                    acc = float(correct[(k, tau)]) / float(max(1, total))
                    if acc > best_knn_acc:
                        best_knn_acc = acc
                        best_knn_k = k
                        best_knn_tau = tau

        if best_knn_acc >= 0.92:
            X_full = torch.cat([X_tr, X_va], dim=0)
            y_full = torch.cat([y_tr, y_va], dim=0)
            Xn_full = _normalize_l2(X_full, mean, std)
            knn_model = KNNClassifier(
                mean=mean,
                std=std,
                mem_features=Xn_full,
                mem_labels=y_full,
                num_classes=num_classes,
                k=best_knn_k,
                tau=best_knn_tau,
                logit_scale=25.0,
            ).to(device)
            return knn_model

        # Train candidates
        candidates: List[Tuple[str, nn.Module, int]] = []

        # ResMLP candidates: blocks 2 and 3
        for blocks in (2, 3):
            hidden = _max_hidden_for_resmlp(
                input_dim=input_dim,
                num_classes=num_classes,
                blocks=blocks,
                param_limit=param_limit,
                extra_params=2,
            )
            model = ProtoResMLP(
                mean=mean,
                std=std,
                prototypes=protos_tr,
                input_dim=input_dim,
                hidden_dim=hidden,
                num_blocks=blocks,
                num_classes=num_classes,
                dropout=0.10,
                noise_std=0.02,
            )
            pc = _count_trainable_params(model)
            if pc <= param_limit:
                candidates.append((f"resmlp_b{blocks}_h{hidden}", model, pc))

        # RFF candidate
        extra_params = 2  # alpha, logit_scale
        rff_dim = int((param_limit - num_classes - extra_params) // max(1, num_classes))
        rff_dim = max(256, min(1561, rff_dim))
        rff_model = ProtoRFF(
            mean=mean,
            std=std,
            prototypes=protos_tr,
            input_dim=input_dim,
            rff_dim=rff_dim,
            num_classes=num_classes,
            sigma=1.0,
            dropout=0.05,
            noise_std=0.02,
        )
        if _count_trainable_params(rff_model) <= param_limit:
            candidates.append((f"rff_d{rff_dim}", rff_model, _count_trainable_params(rff_model)))

        # Compare with kNN and proto on val
        best_name = "knn"
        best_val_acc = best_knn_acc
        best_model = None
        best_state = None

        # Train each parametric candidate briefly and select by val
        for name, model, pc in candidates:
            # Some safety margin for CPU-time; RFF slightly shorter
            sel_epochs = 90 if "resmlp" in name else 60
            base_lr = 2.5e-3 if "resmlp" in name else 3.5e-3
            wd = 1.0e-4 if "resmlp" in name else 2.0e-4
            state, acc = _train_model(
                model=model,
                train_loader=train_dl,
                val_loader=val_dl,
                device=device,
                max_epochs=sel_epochs,
                base_lr=base_lr,
                weight_decay=wd,
                label_smoothing=0.05,
                mixup_alpha=0.2,
                mixup_prob=0.5,
                grad_clip=1.0,
                ema_decay=0.995,
                patience=15,
            )
            if acc > best_val_acc:
                best_val_acc = acc
                best_name = name
                best_model = model
                best_state = state

        # Compare with proto-only as a fallback
        if proto_acc > best_val_acc:
            best_val_acc = proto_acc
            best_name = "proto"
            best_model = proto_model
            best_state = None

        if best_name == "knn":
            X_full = torch.cat([X_tr, X_va], dim=0)
            y_full = torch.cat([y_tr, y_va], dim=0)
            Xn_full = _normalize_l2(X_full, mean, std)
            knn_model = KNNClassifier(
                mean=mean,
                std=std,
                mem_features=Xn_full,
                mem_labels=y_full,
                num_classes=num_classes,
                k=best_knn_k,
                tau=best_knn_tau,
                logit_scale=25.0,
            ).to(device)
            return knn_model

        if best_name == "proto":
            # Upgrade prototypes using full data (train+val), keep same normalization
            X_full = torch.cat([X_tr, X_va], dim=0)
            y_full = torch.cat([y_tr, y_va], dim=0)
            Xn_full = _normalize_l2(X_full, mean, std)
            protos_full = _compute_prototypes(Xn_full, y_full, num_classes=num_classes)
            best_model.prototypes.copy_(protos_full)
            best_model.to(device)
            return best_model

        # Final finetune on full (train + val)
        assert best_model is not None
        if best_state is not None:
            _apply_ema_state(best_model, best_state)

        X_full = torch.cat([X_tr, X_va], dim=0)
        y_full = torch.cat([y_tr, y_va], dim=0)
        full_ds = TensorDataset(X_full, y_full)
        full_dl = DataLoader(full_ds, batch_size=min(bs, len(full_ds)), shuffle=True, num_workers=0)

        # Update prototypes with full data (buffers) before finetune
        Xn_full = _normalize_l2(X_full, mean, std)
        protos_full = _compute_prototypes(Xn_full, y_full, num_classes=num_classes)
        if hasattr(best_model, "prototypes"):
            best_model.prototypes.copy_(protos_full)

        # Reduce augmentation in finetune
        if hasattr(best_model, "noise_std"):
            best_model.noise_std = 0.01

        ft_state, _ = _train_model(
            model=best_model,
            train_loader=full_dl,
            val_loader=None,
            device=device,
            max_epochs=50,
            base_lr=7.5e-4,
            weight_decay=5.0e-5,
            label_smoothing=0.03,
            mixup_alpha=0.0,
            mixup_prob=0.0,
            grad_clip=1.0,
            ema_decay=0.997,
            patience=10,
        )
        _apply_ema_state(best_model, ft_state)

        # Ensure parameter limit
        if _count_trainable_params(best_model) > param_limit:
            # Hard fallback to kNN if somehow exceeded (shouldn't happen)
            Xn_full = _normalize_l2(X_full, mean, std)
            knn_model = KNNClassifier(
                mean=mean,
                std=std,
                mem_features=Xn_full,
                mem_labels=y_full,
                num_classes=num_classes,
                k=best_knn_k,
                tau=best_knn_tau,
                logit_scale=25.0,
            ).to(device)
            return knn_model

        best_model.to(device)
        best_model.eval()
        return best_model