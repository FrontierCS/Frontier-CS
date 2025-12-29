import os
import math
import copy
from typing import Dict, Tuple, Optional, List

import torch
import torch.nn as nn
import torch.nn.functional as F


class _ResBlock(nn.Module):
    def __init__(self, width: int, bottleneck: int, dropout: float):
        super().__init__()
        self.fc1 = nn.Linear(width, bottleneck, bias=True)
        self.ln1 = nn.LayerNorm(bottleneck, elementwise_affine=True)
        self.fc2 = nn.Linear(bottleneck, width, bias=True)
        self.ln2 = nn.LayerNorm(width, elementwise_affine=True)
        self.drop = nn.Dropout(dropout)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        r = x
        x = self.fc1(x)
        x = self.ln1(x)
        x = F.gelu(x)
        x = self.drop(x)
        x = self.fc2(x)
        x = self.ln2(x)
        x = x + r
        x = F.gelu(x)
        return x


class _TabResMLP(nn.Module):
    def __init__(
        self,
        input_dim: int,
        num_classes: int,
        width: int,
        bottleneck: int,
        blocks: int,
        dropout: float,
        mu: torch.Tensor,
        sigma: torch.Tensor,
    ):
        super().__init__()
        self.register_buffer("mu", mu)
        self.register_buffer("sigma", sigma)

        self.fc_in = nn.Linear(input_dim, width, bias=True)
        self.ln0 = nn.LayerNorm(width, elementwise_affine=True)
        self.blocks = nn.ModuleList([_ResBlock(width, bottleneck, dropout) for _ in range(blocks)])
        self.drop = nn.Dropout(dropout)
        self.fc_out = nn.Linear(width, num_classes, bias=True)

        self._init_weights()

    def _init_weights(self):
        for m in self.modules():
            if isinstance(m, nn.Linear):
                nn.init.kaiming_normal_(m.weight, a=math.sqrt(5))
                if m.bias is not None:
                    nn.init.zeros_(m.bias)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        if x.dtype != torch.float32:
            x = x.float()
        x = (x - self.mu) / self.sigma
        x = self.fc_in(x)
        x = self.ln0(x)
        x = F.gelu(x)
        for blk in self.blocks:
            x = blk(x)
        x = self.drop(x)
        x = self.fc_out(x)
        return x


def _collect_loader(loader) -> Tuple[torch.Tensor, torch.Tensor]:
    xs = []
    ys = []
    for xb, yb in loader:
        xs.append(xb.detach().cpu())
        ys.append(yb.detach().cpu())
    x = torch.cat(xs, dim=0)
    y = torch.cat(ys, dim=0)
    return x, y


@torch.inference_mode()
def _accuracy(model: nn.Module, x: torch.Tensor, y: torch.Tensor, batch_size: int = 512) -> float:
    model.eval()
    n = x.shape[0]
    correct = 0
    for i in range(0, n, batch_size):
        xb = x[i : i + batch_size]
        yb = y[i : i + batch_size]
        logits = model(xb)
        pred = logits.argmax(dim=1)
        correct += (pred == yb).sum().item()
    return correct / max(1, n)


def _estimate_params(input_dim: int, num_classes: int, width: int, bottleneck: int, blocks: int) -> int:
    # input linear: input_dim*width + width
    # ln0: 2*width
    # each block:
    #   fc1: width*bottleneck + bottleneck
    #   ln1: 2*bottleneck
    #   fc2: bottleneck*width + width
    #   ln2: 2*width
    # output: width*num_classes + num_classes
    total = 0
    total += input_dim * width + width
    total += 2 * width
    per_block = (width * bottleneck + bottleneck) + (2 * bottleneck) + (bottleneck * width + width) + (2 * width)
    total += blocks * per_block
    total += width * num_classes + num_classes
    return int(total)


def _pick_arch(input_dim: int, num_classes: int, param_limit: int) -> Tuple[int, int, int]:
    # Search for a good width/bottleneck/blocks under param_limit.
    # Prefer high parameter usage; tie-breaker prefers more blocks then larger width.
    block_choices = [3, 2, 1]
    ratio_choices = [0.50, 0.40, 0.333, 0.25]
    best = None  # (params, blocks, width, bottleneck)
    for blocks in block_choices:
        for ratio in ratio_choices:
            for width in range(1024, 127, -16):
                bneck = int(width * ratio)
                bneck = max(32, min(width, (bneck // 8) * 8))
                params = _estimate_params(input_dim, num_classes, width, bneck, blocks)
                if params <= param_limit:
                    cand = (params, blocks, width, bneck)
                    if best is None or cand > best:
                        best = cand
                    break
    if best is None:
        # Minimal fallback
        width = 128
        blocks = 1
        bneck = 64
        params = _estimate_params(input_dim, num_classes, width, bneck, blocks)
        if params > param_limit:
            width = 64
            bneck = 32
            blocks = 1
        return width, bneck, blocks
    return best[2], best[3], best[1]


class Solution:
    def solve(self, train_loader, val_loader, metadata: dict = None) -> torch.nn.Module:
        if metadata is None:
            metadata = {}

        device_str = metadata.get("device", "cpu")
        device = torch.device(device_str)

        try:
            cpu_count = os.cpu_count() or 8
            torch.set_num_threads(max(1, min(8, cpu_count)))
        except Exception:
            pass

        torch.manual_seed(0)

        train_x_cpu, train_y_cpu = _collect_loader(train_loader)
        if val_loader is not None:
            val_x_cpu, val_y_cpu = _collect_loader(val_loader)
        else:
            val_x_cpu, val_y_cpu = train_x_cpu.clone(), train_y_cpu.clone()

        if "input_dim" in metadata:
            input_dim = int(metadata["input_dim"])
        else:
            input_dim = int(train_x_cpu.shape[1])

        if "num_classes" in metadata:
            num_classes = int(metadata["num_classes"])
        else:
            num_classes = int(train_y_cpu.max().item() + 1)

        param_limit = int(metadata.get("param_limit", 1_000_000))

        train_x = train_x_cpu.to(device=device, dtype=torch.float32, non_blocking=False)
        train_y = train_y_cpu.to(device=device, dtype=torch.long, non_blocking=False)
        val_x = val_x_cpu.to(device=device, dtype=torch.float32, non_blocking=False)
        val_y = val_y_cpu.to(device=device, dtype=torch.long, non_blocking=False)

        mu = train_x.mean(dim=0, keepdim=True)
        sigma = train_x.std(dim=0, keepdim=True).clamp_min(1e-6)

        width, bottleneck, blocks = _pick_arch(input_dim, num_classes, param_limit)

        dropout = 0.10
        model = _TabResMLP(
            input_dim=input_dim,
            num_classes=num_classes,
            width=width,
            bottleneck=bottleneck,
            blocks=blocks,
            dropout=dropout,
            mu=mu,
            sigma=sigma,
        ).to(device)

        trainable_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
        if trainable_params > param_limit:
            # Emergency shrink (should not happen with estimator, but keep safe)
            width = max(64, width // 2)
            bottleneck = max(32, min(width, bottleneck // 2))
            blocks = max(1, min(blocks, 2))
            model = _TabResMLP(
                input_dim=input_dim,
                num_classes=num_classes,
                width=width,
                bottleneck=bottleneck,
                blocks=blocks,
                dropout=dropout,
                mu=mu,
                sigma=sigma,
            ).to(device)

        n_train = train_x.shape[0]
        batch_size = 256 if n_train >= 256 else n_train
        steps_per_epoch = max(1, math.ceil(n_train / batch_size))

        max_epochs = 80
        lr = 3e-3
        weight_decay = 1e-2
        label_smoothing = 0.05
        mixup_alpha = 0.2
        mixup_prob = 0.6
        grad_clip = 1.0

        optimizer = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=weight_decay, betas=(0.9, 0.99))
        scheduler = torch.optim.lr_scheduler.OneCycleLR(
            optimizer,
            max_lr=lr,
            total_steps=max_epochs * steps_per_epoch,
            pct_start=0.15,
            anneal_strategy="cos",
            div_factor=12.0,
            final_div_factor=50.0,
        )

        def ce_loss(logits: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
            return F.cross_entropy(logits, targets, label_smoothing=label_smoothing)

        params_list: List[torch.Tensor] = [p for p in model.parameters() if p.requires_grad]
        ema_list: List[torch.Tensor] = [p.detach().clone() for p in params_list]
        ema_decay = 0.995

        def ema_update():
            for e, p in zip(ema_list, params_list):
                e.mul_(ema_decay).add_(p.detach(), alpha=(1.0 - ema_decay))

        def apply_ema() -> List[torch.Tensor]:
            backup = [p.detach().clone() for p in params_list]
            for p, e in zip(params_list, ema_list):
                p.data.copy_(e)
            return backup

        def restore_params(backup: List[torch.Tensor]):
            for p, b in zip(params_list, backup):
                p.data.copy_(b)

        best_acc = -1.0
        best_state = None
        patience = 20
        bad_epochs = 0

        model.train()
        for epoch in range(max_epochs):
            model.train()
            perm = torch.randperm(n_train, device=device)
            for si in range(0, n_train, batch_size):
                idx = perm[si : si + batch_size]
                xb = train_x.index_select(0, idx)
                yb = train_y.index_select(0, idx)

                if mixup_alpha > 0 and torch.rand((), device=device).item() < mixup_prob:
                    lam = torch.distributions.Beta(mixup_alpha, mixup_alpha).sample().to(device)
                    lam = torch.maximum(lam, 1.0 - lam)
                    perm2 = torch.randperm(xb.shape[0], device=device)
                    xb2 = xb[perm2]
                    yb2 = yb[perm2]
                    xb = lam * xb + (1.0 - lam) * xb2
                    logits = model(xb)
                    loss = lam * ce_loss(logits, yb) + (1.0 - lam) * ce_loss(logits, yb2)
                else:
                    logits = model(xb)
                    loss = ce_loss(logits, yb)

                optimizer.zero_grad(set_to_none=True)
                loss.backward()
                if grad_clip is not None and grad_clip > 0:
                    torch.nn.utils.clip_grad_norm_(model.parameters(), grad_clip)
                optimizer.step()
                scheduler.step()
                ema_update()

            backup = apply_ema()
            acc = _accuracy(model, val_x, val_y, batch_size=512)
            if acc > best_acc + 1e-6:
                best_acc = acc
                best_state = {k: v.detach().clone() for k, v in model.state_dict().items()}
                bad_epochs = 0
            else:
                bad_epochs += 1
            restore_params(backup)

            if bad_epochs >= patience:
                break

        if best_state is not None:
            model.load_state_dict(best_state, strict=True)
        else:
            backup = apply_ema()
            best_state = {k: v.detach().clone() for k, v in model.state_dict().items()}
            restore_params(backup)
            model.load_state_dict(best_state, strict=True)

        model.eval()
        return model