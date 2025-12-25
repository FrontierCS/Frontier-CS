import math
import random
from copy import deepcopy
from typing import Optional, Tuple

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F


class ModelEma:
    def __init__(self, model: nn.Module, decay: float = 0.997, device: Optional[torch.device] = None):
        self.decay = decay
        self.ema = deepcopy(model).to(device if device is not None else next(model.parameters()).device)
        self.ema.eval()
        for p in self.ema.parameters():
            p.requires_grad_(False)

    @torch.no_grad()
    def update(self, model: nn.Module):
        d = self.decay
        msd = model.state_dict()
        for k, v_ema in self.ema.state_dict().items():
            v = msd[k]
            if torch.is_floating_point(v_ema):
                v_ema.mul_(d).add_(v, alpha=1.0 - d)
            else:
                v_ema.copy_(v)


class ResFFNBlock(nn.Module):
    def __init__(
        self,
        dim: int,
        hidden_dim: int,
        dropout: float = 0.1,
        layerscale_init: float = 1e-3,
        gating_ratio: Optional[int] = None,
    ):
        super().__init__()
        self.norm = nn.LayerNorm(dim)
        self.fc1 = nn.Linear(dim, hidden_dim)
        self.fc2 = nn.Linear(hidden_dim, dim)
        self.act = nn.GELU()
        self.drop1 = nn.Dropout(dropout)
        self.drop2 = nn.Dropout(dropout)
        self.gamma = nn.Parameter(torch.ones(dim) * layerscale_init)

        self.se = None
        if gating_ratio is not None and gating_ratio > 0:
            gdim = max(1, dim // gating_ratio)
            self.se = nn.Sequential(
                nn.LayerNorm(dim),
                nn.Linear(dim, gdim),
                nn.SiLU(),
                nn.Linear(gdim, dim),
                nn.Sigmoid(),
            )

        self._init_weights()

    def _init_weights(self):
        nn.init.kaiming_uniform_(self.fc1.weight, a=math.sqrt(5))
        nn.init.zeros_(self.fc1.bias)
        nn.init.xavier_uniform_(self.fc2.weight)
        nn.init.zeros_(self.fc2.bias)

        if self.se is not None:
            for m in self.se:
                if isinstance(m, nn.Linear):
                    nn.init.xavier_uniform_(m.weight)
                    nn.init.zeros_(m.bias)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        residual = x
        out = self.norm(x)
        out = self.fc1(out)
        out = self.act(out)
        out = self.drop1(out)
        out = self.fc2(out)
        out = self.drop2(out)
        if self.se is not None:
            gate = self.se(residual)
            out = out * gate
        return residual + self.gamma * out


class ResMLPClassifier(nn.Module):
    def __init__(
        self,
        input_dim: int,
        num_classes: int,
        hidden_dim: int,
        dropout: float = 0.1,
        gating_ratio: Optional[int] = None,
        layerscale_init: float = 1e-3,
        head_dropout: float = 0.1,
    ):
        super().__init__()
        self.block = ResFFNBlock(
            dim=input_dim,
            hidden_dim=hidden_dim,
            dropout=dropout,
            layerscale_init=layerscale_init,
            gating_ratio=gating_ratio,
        )
        self.norm_out = nn.LayerNorm(input_dim)
        self.head_drop = nn.Dropout(head_dropout)
        self.head = nn.Linear(input_dim, num_classes)
        self._init_weights()

    def _init_weights(self):
        nn.init.xavier_uniform_(self.head.weight)
        nn.init.zeros_(self.head.bias)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self.block(x)
        x = self.norm_out(x)
        x = self.head_drop(x)
        x = self.head(x)
        return x


def set_seed(seed: int = 42):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)


def count_trainable_params(model: nn.Module) -> int:
    return sum(p.numel() for p in model.parameters() if p.requires_grad)


def build_param_groups(model: nn.Module, weight_decay: float = 1e-2):
    decay, no_decay = [], []
    for name, p in model.named_parameters():
        if not p.requires_grad:
            continue
        if p.ndim == 1 or name.endswith(".bias"):
            no_decay.append(p)
        else:
            decay.append(p)
    return [
        {"params": decay, "weight_decay": weight_decay},
        {"params": no_decay, "weight_decay": 0.0},
    ]


def mixup_data(x: torch.Tensor, y: torch.Tensor, alpha: float = 0.2) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor, float]:
    if alpha <= 0:
        return x, y, y, 1.0
    lam = np.random.beta(alpha, alpha)
    batch_size = x.size(0)
    index = torch.randperm(batch_size, device=x.device)
    mixed_x = lam * x + (1 - lam) * x[index, :]
    y_a, y_b = y, y[index]
    return mixed_x, y_a, y_b, float(lam)


class Solution:
    def solve(self, train_loader, val_loader, metadata: dict = None) -> torch.nn.Module:
        set_seed(42)

        if metadata is None:
            metadata = {}
        input_dim = int(metadata.get("input_dim", 384))
        num_classes = int(metadata.get("num_classes", 128))
        param_limit = int(metadata.get("param_limit", 500_000))
        device_str = metadata.get("device", "cpu")
        device = torch.device(device_str if torch.cuda.is_available() and device_str.startswith("cuda") else "cpu")

        # Search best architecture under parameter budget
        candidate_ratios = [16, 12, 24, 8, 32, None]  # Prefer moderate gating first
        candidate_multiples = list(range(640, 191, -32))  # Hidden sizes to try
        best_model_cfg = None
        best_params = -1

        for gr in candidate_ratios:
            for hidden_dim in candidate_multiples:
                model = ResMLPClassifier(
                    input_dim=input_dim,
                    num_classes=num_classes,
                    hidden_dim=hidden_dim,
                    dropout=0.15,
                    gating_ratio=gr if gr is not None else None,
                    layerscale_init=1e-3,
                    head_dropout=0.10,
                )
                pcount = count_trainable_params(model)
                if pcount <= param_limit and pcount > best_params:
                    best_params = pcount
                    best_model_cfg = (hidden_dim, gr)

                # early exit if very close to limit
                if 0 <= param_limit - pcount <= 1_000:
                    break
            if best_params >= param_limit - 1_000:
                break

        if best_model_cfg is None:
            # Fallback to safe baseline
            best_model_cfg = (512, None)

        hidden_dim, gating_ratio = best_model_cfg

        model = ResMLPClassifier(
            input_dim=input_dim,
            num_classes=num_classes,
            hidden_dim=hidden_dim,
            dropout=0.15,
            gating_ratio=gating_ratio if gating_ratio is not None else None,
            layerscale_init=1e-3,
            head_dropout=0.10,
        ).to(device)

        # Ensure under budget strictly
        if count_trainable_params(model) > param_limit:
            # Decrease hidden dim until within budget
            hd = hidden_dim
            while hd > 128:
                hd -= 16
                model = ResMLPClassifier(
                    input_dim=input_dim,
                    num_classes=num_classes,
                    hidden_dim=hd,
                    dropout=0.15,
                    gating_ratio=gating_ratio if gating_ratio is not None else None,
                    layerscale_init=1e-3,
                    head_dropout=0.10,
                ).to(device)
                if count_trainable_params(model) <= param_limit:
                    break

        # Optimizer and scheduler
        base_lr = 3e-3
        weight_decay = 1e-2
        param_groups = build_param_groups(model, weight_decay=weight_decay)
        optimizer = torch.optim.AdamW(param_groups, lr=base_lr, betas=(0.9, 0.999), eps=1e-8)

        # Learning rate schedule with warmup + cosine
        steps_per_epoch = max(1, len(train_loader))
        epochs = 200
        total_steps = steps_per_epoch * epochs
        warmup_steps = max(10, int(0.10 * total_steps))

        def lr_lambda(step):
            if step < warmup_steps:
                return float(step) / float(max(1, warmup_steps))
            progress = (step - warmup_steps) / float(max(1, total_steps - warmup_steps))
            return 0.5 * (1.0 + math.cos(math.pi * progress))

        scheduler = torch.optim.lr_scheduler.LambdaLR(optimizer, lr_lambda=lr_lambda)

        # Losses
        criterion = nn.CrossEntropyLoss(label_smoothing=0.05)
        criterion_nomix = nn.CrossEntropyLoss()

        # EMA
        ema = ModelEma(model, decay=0.997, device=device)

        # Training loop with early stopping on val accuracy
        best_state = None
        best_ema_state = None
        best_val_acc = -1.0
        best_ema_val_acc = -1.0
        patience = 60
        no_improve = 0
        global_step = 0

        mixup_alpha = 0.2
        mixup_prob = 0.5

        for epoch in range(epochs):
            model.train()
            for batch in train_loader:
                if isinstance(batch, (list, tuple)) and len(batch) == 2:
                    inputs, targets = batch
                else:
                    inputs, targets = batch[0], batch[1]
                inputs = inputs.to(device, non_blocking=False).float()
                targets = targets.to(device, non_blocking=False).long()

                use_mix = mixup_alpha > 0 and random.random() < mixup_prob
                if use_mix:
                    inputs, y_a, y_b, lam = mixup_data(inputs, targets, alpha=mixup_alpha)

                optimizer.zero_grad(set_to_none=True)
                outputs = model(inputs)

                if use_mix:
                    loss = lam * criterion_nomix(outputs, y_a) + (1.0 - lam) * criterion_nomix(outputs, y_b)
                else:
                    loss = criterion(outputs, targets)

                loss.backward()
                torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
                optimizer.step()
                scheduler.step()
                ema.update(model)
                global_step += 1

            # Validation on EMA model for stability
            with torch.no_grad():
                model.eval()
                ema.ema.eval()

                def eval_model(m: nn.Module):
                    correct = 0
                    total = 0
                    for vb in val_loader:
                        vi, vt = vb
                        vi = vi.to(device).float()
                        vt = vt.to(device).long()
                        logits = m(vi)
                        pred = logits.argmax(dim=1)
                        correct += (pred == vt).sum().item()
                        total += vt.numel()
                    return correct / max(1, total)

                ema_val_acc = eval_model(ema.ema)
                raw_val_acc = eval_model(model)

                improved = False
                if ema_val_acc > best_ema_val_acc:
                    best_ema_val_acc = ema_val_acc
                    best_ema_state = deepcopy(ema.ema.state_dict())
                    improved = True
                if raw_val_acc > best_val_acc:
                    best_val_acc = raw_val_acc
                    best_state = deepcopy(model.state_dict())
                    improved = True

                if improved:
                    no_improve = 0
                else:
                    no_improve += 1

            if no_improve >= patience:
                break

        # Load best EMA weights if better, else best raw weights
        final_state = best_ema_state if (best_ema_state is not None and best_ema_val_acc >= best_val_acc) else best_state
        if final_state is not None:
            model.load_state_dict(final_state)

        model.eval()
        return model
