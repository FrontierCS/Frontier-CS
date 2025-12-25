import os
import math
import copy
from typing import Optional, Tuple, List

import torch
import torch.nn as nn
import torch.nn.functional as F


def _set_cpu_threads():
    try:
        n = os.cpu_count() or 8
        torch.set_num_threads(min(8, n))
    except Exception:
        pass


def _loader_to_tensors(loader, device: torch.device) -> Tuple[torch.Tensor, torch.Tensor]:
    xs = []
    ys = []
    for batch in loader:
        if isinstance(batch, (list, tuple)) and len(batch) >= 2:
            x, y = batch[0], batch[1]
        else:
            raise ValueError("Expected DataLoader to yield (inputs, targets).")
        x = torch.as_tensor(x)
        y = torch.as_tensor(y)
        if x.dtype != torch.float32:
            x = x.float()
        if y.dtype != torch.long:
            y = y.long()
        xs.append(x)
        ys.append(y)
    X = torch.cat(xs, dim=0).to(device)
    Y = torch.cat(ys, dim=0).to(device)
    return X.contiguous(), Y.contiguous()


def _param_count(model: nn.Module) -> int:
    return sum(p.numel() for p in model.parameters() if p.requires_grad)


class CosineHead(nn.Module):
    def __init__(self, in_dim: int, num_classes: int, init_scale: float = 10.0):
        super().__init__()
        self.weight = nn.Parameter(torch.empty(num_classes, in_dim))
        nn.init.normal_(self.weight, mean=0.0, std=0.02)
        self.log_scale = nn.Parameter(torch.tensor(float(math.log(max(1e-6, init_scale))), dtype=torch.float32))

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = F.normalize(x, dim=1)
        w = F.normalize(self.weight, dim=1)
        scale = torch.exp(self.log_scale).clamp(1.0, 100.0)
        return scale * (x @ w.t())


class ResMLPClassifier(nn.Module):
    def __init__(
        self,
        input_dim: int,
        num_classes: int,
        width: int,
        num_blocks: int,
        dropout: float,
        x_mean: torch.Tensor,
        x_std: torch.Tensor,
    ):
        super().__init__()
        self.input_dim = int(input_dim)
        self.num_classes = int(num_classes)
        self.width = int(width)
        self.num_blocks = int(num_blocks)
        self.dropout_p = float(dropout)

        self.register_buffer("x_mean", x_mean.detach().clone().view(1, -1))
        invstd = 1.0 / x_std.detach().clone().clamp_min(1e-6).view(1, -1)
        self.register_buffer("x_invstd", invstd)

        self.ln_in = nn.LayerNorm(self.input_dim)
        self.fc_in = nn.Linear(self.input_dim, self.width)

        self.block_lns = nn.ModuleList([nn.LayerNorm(self.width) for _ in range(self.num_blocks)])
        self.block_fcs = nn.ModuleList([nn.Linear(self.width, self.width) for _ in range(self.num_blocks)])
        self.block_gates = nn.Parameter(torch.ones(self.num_blocks, dtype=torch.float32) * 0.35)

        self.ln_out = nn.LayerNorm(self.width)
        self.head = CosineHead(self.width, self.num_classes, init_scale=12.0)
        self.drop = nn.Dropout(self.dropout_p)

        self.register_buffer("proto", torch.empty(0), persistent=False)
        self.register_buffer("proto_temp", torch.tensor(10.0, dtype=torch.float32), persistent=False)
        self.register_buffer("blend_alpha", torch.tensor(1.0, dtype=torch.float32), persistent=False)
        self.mode = 0  # 0=linear, 1=proto, 2=blend

    def forward_features(self, x: torch.Tensor) -> torch.Tensor:
        x = (x - self.x_mean) * self.x_invstd
        x = self.ln_in(x)
        x = self.fc_in(x)
        x = F.gelu(x, approximate="tanh")
        x = self.drop(x)
        for gate, ln, fc in zip(self.block_gates, self.block_lns, self.block_fcs):
            h = ln(x)
            h = fc(h)
            h = F.gelu(h, approximate="tanh")
            h = self.drop(h)
            x = x + gate * h
        x = self.ln_out(x)
        return x

    def _proto_logits(self, feats: torch.Tensor) -> torch.Tensor:
        if self.proto.numel() == 0:
            return torch.zeros(feats.shape[0], self.num_classes, device=feats.device, dtype=feats.dtype)
        feats = F.normalize(feats, dim=1)
        temp = float(self.proto_temp.item()) if isinstance(self.proto_temp, torch.Tensor) else float(self.proto_temp)
        return (feats @ self.proto.t()) * temp

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        feats = self.forward_features(x)
        if self.mode == 0:
            return self.head(feats)
        elif self.mode == 1:
            return self._proto_logits(feats)
        else:
            alpha = float(self.blend_alpha.item()) if isinstance(self.blend_alpha, torch.Tensor) else float(self.blend_alpha)
            return self.head(feats) + alpha * self._proto_logits(feats)

    def set_prototypes(self, proto: torch.Tensor, temp: float, mode: int = 1, blend_alpha: float = 1.0):
        if proto is None or proto.numel() == 0:
            self.proto = torch.empty(0, device=self.x_mean.device)
            self.mode = 0
            return
        self.proto = proto.detach()
        self.proto_temp = torch.tensor(float(temp), device=self.x_mean.device, dtype=torch.float32)
        self.blend_alpha = torch.tensor(float(blend_alpha), device=self.x_mean.device, dtype=torch.float32)
        self.mode = int(mode)


def _compute_arch_params(input_dim: int, num_classes: int, width: int, blocks: int) -> int:
    # Linear in: input_dim*width + width
    # Each block: width*width + width
    # LN: ln_in (2*input_dim), block lns (blocks*2*width), ln_out (2*width)
    # Gates: blocks
    # Head (Cosine): num_classes*width + log_scale (1)
    count = 0
    count += input_dim * width + width
    count += blocks * (width * width + width)
    count += 2 * input_dim
    count += blocks * (2 * width)
    count += 2 * width
    count += blocks
    count += num_classes * width + 1
    return int(count)


def _pick_arch(input_dim: int, num_classes: int, param_limit: int) -> Tuple[int, int]:
    margin = 8000
    limit = max(1, param_limit - margin)

    preferred_blocks = [3, 4, 2, 5, 1]
    max_w = 2048
    min_w = 128
    step = 16

    for blocks in preferred_blocks:
        best_w = None
        for w in range(max_w, min_w - 1, -step):
            if _compute_arch_params(input_dim, num_classes, w, blocks) <= limit:
                best_w = w
                break
        if best_w is not None:
            return best_w, blocks

    # Fallback: smallest width / 1 block
    w = min_w
    b = 1
    while _compute_arch_params(input_dim, num_classes, w, b) > limit and w > 32:
        w -= 8
    return max(32, w), b


def _accuracy(model: nn.Module, X: torch.Tensor, y: torch.Tensor, batch_size: int = 512) -> float:
    model.eval()
    correct = 0
    total = int(y.numel())
    with torch.inference_mode():
        for i in range(0, total, batch_size):
            xb = X[i : i + batch_size]
            yb = y[i : i + batch_size]
            logits = model(xb)
            pred = logits.argmax(dim=1)
            correct += int((pred == yb).sum().item())
    return float(correct) / float(total) if total > 0 else 0.0


def _build_prototypes(model: ResMLPClassifier, X: torch.Tensor, y: torch.Tensor) -> torch.Tensor:
    model.eval()
    num_classes = model.num_classes
    with torch.inference_mode():
        feats = model.forward_features(X)
        feats = F.normalize(feats, dim=1)
        proto = torch.zeros(num_classes, feats.shape[1], device=feats.device, dtype=feats.dtype)
        counts = torch.zeros(num_classes, device=feats.device, dtype=torch.float32)
        for c in range(num_classes):
            mask = (y == c)
            if mask.any():
                fc = feats[mask]
                proto[c] = fc.mean(dim=0)
                counts[c] = float(mask.sum().item())
        proto = F.normalize(proto, dim=1)
    return proto


class Solution:
    def solve(self, train_loader, val_loader, metadata: dict = None) -> torch.nn.Module:
        _set_cpu_threads()

        if metadata is None:
            metadata = {}
        input_dim = int(metadata.get("input_dim", 384))
        num_classes = int(metadata.get("num_classes", 128))
        param_limit = int(metadata.get("param_limit", 1_000_000))
        device = torch.device(metadata.get("device", "cpu"))

        X_train, y_train = _loader_to_tensors(train_loader, device=device)
        X_val, y_val = _loader_to_tensors(val_loader, device=device)

        with torch.inference_mode():
            x_mean = X_train.mean(dim=0, keepdim=False).float()
            x_std = X_train.std(dim=0, unbiased=False, keepdim=False).float().clamp_min(1e-3)

        width, blocks = _pick_arch(input_dim, num_classes, param_limit)

        dropout = 0.10
        model = ResMLPClassifier(
            input_dim=input_dim,
            num_classes=num_classes,
            width=width,
            num_blocks=blocks,
            dropout=dropout,
            x_mean=x_mean.to(device),
            x_std=x_std.to(device),
        ).to(device)

        if _param_count(model) > param_limit:
            # Aggressive fallback if anything unexpected happens
            for b in [2, 1]:
                for w in range(max(64, width - 128), 63, -16):
                    tmp = ResMLPClassifier(
                        input_dim=input_dim,
                        num_classes=num_classes,
                        width=w,
                        num_blocks=b,
                        dropout=dropout,
                        x_mean=x_mean.to(device),
                        x_std=x_std.to(device),
                    ).to(device)
                    if _param_count(tmp) <= param_limit:
                        model = tmp
                        width, blocks = w, b
                        break
                if _param_count(model) <= param_limit:
                    break

        n_train = int(X_train.shape[0])
        batch_size = 256
        if n_train <= 256:
            batch_size = max(32, n_train)

        steps_per_epoch = max(1, (n_train + batch_size - 1) // batch_size)
        max_epochs = 80
        total_steps = max(steps_per_epoch * max_epochs, 1)

        optimizer = torch.optim.AdamW(model.parameters(), lr=3.5e-3, weight_decay=1.0e-2, betas=(0.9, 0.98))
        scheduler = torch.optim.lr_scheduler.OneCycleLR(
            optimizer,
            max_lr=3.5e-3,
            total_steps=total_steps,
            pct_start=0.12,
            anneal_strategy="cos",
            div_factor=20.0,
            final_div_factor=200.0,
        )

        criterion = nn.CrossEntropyLoss(label_smoothing=0.08)

        best_state = None
        best_acc = -1.0
        patience = 12
        bad = 0

        gen = torch.Generator(device=device)
        gen.manual_seed(12345)

        ema_decay = 0.995
        ema_params: Optional[List[torch.Tensor]] = None
        try:
            ema_params = [p.detach().clone() for p in model.parameters() if p.requires_grad]
        except Exception:
            ema_params = None

        step_idx = 0
        for epoch in range(max_epochs):
            model.train()
            perm = torch.randperm(n_train, generator=gen, device=device)
            for s in range(0, n_train, batch_size):
                idx = perm[s : s + batch_size]
                xb = X_train[idx]
                yb = y_train[idx]

                if model.dropout_p > 0.0:
                    noise = torch.randn_like(xb) * 0.015
                    xb = xb + noise

                logits = model(xb)
                loss = criterion(logits, yb)

                optimizer.zero_grad(set_to_none=True)
                loss.backward()
                nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
                optimizer.step()
                scheduler.step()

                if ema_params is not None:
                    j = 0
                    for p in model.parameters():
                        if not p.requires_grad:
                            continue
                        ema_params[j].mul_(ema_decay).add_(p.detach(), alpha=(1.0 - ema_decay))
                        j += 1

                step_idx += 1
                if step_idx >= total_steps:
                    break
            if step_idx >= total_steps:
                break

            val_acc = _accuracy(model, X_val, y_val, batch_size=512)

            if val_acc > best_acc + 1e-6:
                best_acc = val_acc
                best_state = copy.deepcopy(model.state_dict())
                bad = 0
            else:
                bad += 1
                if bad >= patience and epoch >= 12:
                    break

        if best_state is not None:
            model.load_state_dict(best_state, strict=True)

        # Optional: compare with EMA snapshot if available
        if ema_params is not None:
            backup = [p.detach().clone() for p in model.parameters() if p.requires_grad]
            with torch.no_grad():
                j = 0
                for p in model.parameters():
                    if not p.requires_grad:
                        continue
                    p.copy_(ema_params[j])
                    j += 1
            ema_acc = _accuracy(model, X_val, y_val, batch_size=512)
            cur_acc = _accuracy(model, X_val, y_val, batch_size=512)
            if ema_acc + 1e-6 < cur_acc:
                # restore backup
                with torch.no_grad():
                    j = 0
                    for p in model.parameters():
                        if not p.requires_grad:
                            continue
                        p.copy_(backup[j])
                        j += 1

        # Prototype / blend selection on validation
        proto = _build_prototypes(model, X_train, y_train)
        temps = [6.0, 10.0, 16.0, 24.0]
        alphas = [0.4, 0.7, 1.0, 1.4, 2.0]

        model.set_prototypes(proto=proto, temp=10.0, mode=0, blend_alpha=1.0)
        base_acc = _accuracy(model, X_val, y_val, batch_size=512)

        best_mode = 0
        best_t = 10.0
        best_a = 1.0
        best_val = base_acc

        for t in temps:
            model.set_prototypes(proto=proto, temp=t, mode=1, blend_alpha=1.0)
            acc = _accuracy(model, X_val, y_val, batch_size=512)
            if acc > best_val + 1e-6:
                best_val = acc
                best_mode = 1
                best_t = t
                best_a = 1.0

        for t in temps:
            for a in alphas:
                model.set_prototypes(proto=proto, temp=t, mode=2, blend_alpha=a)
                acc = _accuracy(model, X_val, y_val, batch_size=512)
                if acc > best_val + 1e-6:
                    best_val = acc
                    best_mode = 2
                    best_t = t
                    best_a = a

        model.set_prototypes(proto=proto, temp=best_t, mode=best_mode, blend_alpha=best_a)

        model.eval()
        model.to(torch.device("cpu"))
        return model
