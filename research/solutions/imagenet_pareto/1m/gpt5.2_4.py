import os
import math
import copy
from typing import Tuple, Optional, Dict

import torch
import torch.nn as nn


class _StdMLP(nn.Module):
    def __init__(
        self,
        input_dim: int,
        num_classes: int,
        dims: Tuple[int, ...],
        mean: torch.Tensor,
        std: torch.Tensor,
        dropout: float = 0.10,
    ):
        super().__init__()
        self.register_buffer("mean", mean.view(1, -1).contiguous())
        self.register_buffer("std", std.view(1, -1).contiguous())

        layers = []
        prev = input_dim
        for d in dims:
            layers.append(nn.Linear(prev, d, bias=True))
            layers.append(nn.GELU())
            layers.append(nn.LayerNorm(d, elementwise_affine=True))
            if dropout and dropout > 0:
                layers.append(nn.Dropout(dropout))
            prev = d
        self.backbone = nn.Sequential(*layers)
        self.head = nn.Linear(prev, num_classes, bias=True)

        self._init_weights()

    def _init_weights(self):
        for m in self.modules():
            if isinstance(m, nn.Linear):
                nn.init.trunc_normal_(m.weight, std=0.02)
                if m.bias is not None:
                    nn.init.zeros_(m.bias)
            elif isinstance(m, nn.LayerNorm):
                nn.init.ones_(m.weight)
                nn.init.zeros_(m.bias)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = x.float()
        x = (x - self.mean) / self.std
        x = self.backbone(x)
        x = self.head(x)
        return x


def _count_trainable_params(model: nn.Module) -> int:
    return sum(p.numel() for p in model.parameters() if p.requires_grad)


def _loader_to_tensors(loader, device: torch.device) -> Tuple[torch.Tensor, torch.Tensor]:
    xs = []
    ys = []
    for xb, yb in loader:
        xs.append(xb.detach().to(device, non_blocking=True))
        ys.append(yb.detach().to(device, non_blocking=True))
    x = torch.cat(xs, dim=0).contiguous()
    y = torch.cat(ys, dim=0).long().contiguous()
    return x, y


@torch.no_grad()
def _accuracy(model: nn.Module, x: torch.Tensor, y: torch.Tensor, batch_size: int = 1024) -> float:
    model.eval()
    correct = 0
    n = y.numel()
    for i in range(0, n, batch_size):
        xb = x[i : i + batch_size]
        yb = y[i : i + batch_size]
        logits = model(xb)
        pred = logits.argmax(dim=1)
        correct += (pred == yb).sum().item()
    return correct / max(1, n)


def _pick_dims_3hidden(input_dim: int, num_classes: int, param_limit: int) -> Optional[Tuple[int, int, int]]:
    # Model: Linear+GELU+LN(+Dropout) x3, then Linear head. Params independent of dropout.
    # Params = in*d1 + d1*d2 + d2*d3 + d3*C + biases(d1+d2+d3+C) + LN(2*(d1+d2+d3))
    #       = in*d1 + d1*d2 + d2*d3 + d3*C + 3*(d1+d2+d3) + C
    best = None
    best_params = -1

    # search space tuned for 1M constraint
    d1_candidates = list(range(640, 1409, 32))
    for d1 in d1_candidates:
        # d2 not necessarily <= d1, but keep sensible
        for d2 in range(256, min(d1, 1024) + 1, 32):
            for d3 in range(128, min(d2, 768) + 1, 32):
                params = (
                    input_dim * d1
                    + d1 * d2
                    + d2 * d3
                    + d3 * num_classes
                    + 3 * (d1 + d2 + d3)
                    + num_classes
                )
                if params <= param_limit and params > best_params:
                    best_params = params
                    best = (d1, d2, d3)
    return best


def _pick_dims_2hidden(input_dim: int, num_classes: int, param_limit: int) -> Tuple[int, int]:
    # Params = in*d1 + d1*d2 + d2*C + biases(d1+d2+C) + LN(2*(d1+d2))
    #       = in*d1 + d1*d2 + d2*C + 3*(d1+d2) + C
    best = (512, 256)
    best_params = -1
    for d1 in range(512, 1537, 32):
        for d2 in range(256, min(d1, 1024) + 1, 16):
            params = input_dim * d1 + d1 * d2 + d2 * num_classes + 3 * (d1 + d2) + num_classes
            if params <= param_limit and params > best_params:
                best_params = params
                best = (d1, d2)
    return best


class Solution:
    def solve(self, train_loader, val_loader, metadata: dict = None) -> torch.nn.Module:
        if metadata is None:
            metadata = {}
        input_dim = int(metadata.get("input_dim", 384))
        num_classes = int(metadata.get("num_classes", 128))
        param_limit = int(metadata.get("param_limit", 1_000_000))
        device_str = metadata.get("device", "cpu")
        device = torch.device(device_str)

        try:
            torch.set_num_threads(min(8, os.cpu_count() or 8))
        except Exception:
            pass

        torch.manual_seed(0)

        x_train, y_train = _loader_to_tensors(train_loader, device)
        x_val, y_val = _loader_to_tensors(val_loader, device)

        x_train = x_train.float().contiguous()
        x_val = x_val.float().contiguous()

        mean = x_train.mean(dim=0)
        std = x_train.std(dim=0, unbiased=False).clamp_min(1e-6)

        dims3 = _pick_dims_3hidden(input_dim, num_classes, param_limit)
        if dims3 is not None:
            dims = dims3
        else:
            d1, d2 = _pick_dims_2hidden(input_dim, num_classes, param_limit)
            dims = (d1, d2)

        dropout = 0.10
        model = _StdMLP(input_dim, num_classes, dims, mean, std, dropout=dropout).to(device)

        if _count_trainable_params(model) > param_limit:
            # Conservative fallback
            d1, d2 = _pick_dims_2hidden(input_dim, num_classes, param_limit - 4096)
            model = _StdMLP(input_dim, num_classes, (d1, d2), mean, std, dropout=dropout).to(device)

        if _count_trainable_params(model) > param_limit:
            # Last resort
            model = _StdMLP(input_dim, num_classes, (512, 256), mean, std, dropout=dropout).to(device)

        max_epochs = 160
        min_epochs = 25
        batch_size = 256 if x_train.size(0) >= 256 else int(x_train.size(0))
        steps_per_epoch = max(1, math.ceil(x_train.size(0) / batch_size))
        total_steps = max_epochs * steps_per_epoch

        lr = 3e-3
        wd = 2e-2
        optimizer = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=wd, betas=(0.9, 0.98), eps=1e-8)
        scheduler = torch.optim.lr_scheduler.OneCycleLR(
            optimizer,
            max_lr=lr,
            total_steps=total_steps,
            pct_start=0.12,
            anneal_strategy="cos",
            div_factor=12.0,
            final_div_factor=120.0,
        )

        criterion = nn.CrossEntropyLoss(label_smoothing=0.05)

        ema_model = copy.deepcopy(model).to(device)
        for p in ema_model.parameters():
            p.requires_grad_(False)
        ema_decay = 0.995

        best_acc = -1.0
        best_state: Optional[Dict[str, torch.Tensor]] = None
        patience = 22
        bad_epochs = 0
        input_noise = 0.01

        n_train = x_train.size(0)

        for epoch in range(max_epochs):
            model.train()
            perm = torch.randperm(n_train, device=device)

            for step in range(steps_per_epoch):
                idx = perm[step * batch_size : (step + 1) * batch_size]
                xb = x_train.index_select(0, idx)
                yb = y_train.index_select(0, idx)

                if input_noise and input_noise > 0:
                    xb = xb + torch.randn_like(xb) * input_noise

                optimizer.zero_grad(set_to_none=True)
                logits = model(xb)
                loss = criterion(logits, yb)
                loss.backward()
                torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
                optimizer.step()
                scheduler.step()

                with torch.no_grad():
                    for p_ema, p in zip(ema_model.parameters(), model.parameters()):
                        p_ema.mul_(ema_decay).add_(p.detach(), alpha=1.0 - ema_decay)

            val_acc = _accuracy(ema_model, x_val, y_val, batch_size=1024)

            if val_acc > best_acc + 1e-4:
                best_acc = val_acc
                best_state = {k: v.detach().clone() for k, v in ema_model.state_dict().items()}
                bad_epochs = 0
            else:
                bad_epochs += 1

            if epoch + 1 >= min_epochs and bad_epochs >= patience:
                break

        if best_state is not None:
            model.load_state_dict(best_state, strict=True)
        else:
            model.load_state_dict(ema_model.state_dict(), strict=True)

        model.eval()
        return model