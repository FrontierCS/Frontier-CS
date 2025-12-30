import math
import random
import time
from typing import Optional, Tuple

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F


def set_seed(seed: int = 1337):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)


def count_parameters(model: nn.Module) -> int:
    return sum(p.numel() for p in model.parameters() if p.requires_grad)


class DropPath(nn.Module):
    def __init__(self, drop_prob: float = 0.0):
        super().__init__()
        self.drop_prob = float(drop_prob)

    def forward(self, x):
        if self.drop_prob == 0.0 or not self.training:
            return x
        keep_prob = 1.0 - self.drop_prob
        shape = (x.shape[0],) + (1,) * (x.ndim - 1)
        random_tensor = x.new_empty(shape).bernoulli_(keep_prob)
        output = x / keep_prob * random_tensor
        return output


class ResidualBottleneckMLP(nn.Module):
    def __init__(self, dim: int, bottleneck_dim: int, drop: float = 0.1, drop_path: float = 0.0):
        super().__init__()
        self.norm = nn.LayerNorm(dim)
        self.fc1 = nn.Linear(dim, bottleneck_dim)
        self.act = nn.GELU()
        self.fc2 = nn.Linear(bottleneck_dim, dim)
        self.drop1 = nn.Dropout(drop)
        self.drop2 = nn.Dropout(drop)
        self.drop_path = DropPath(drop_path) if drop_path > 0.0 else nn.Identity()

    def forward(self, x):
        y = self.norm(x)
        y = self.fc1(y)
        y = self.act(y)
        y = self.drop1(y)
        y = self.fc2(y)
        y = self.drop2(y)
        y = self.drop_path(y)
        return x + y


class ResMLPNet(nn.Module):
    def __init__(
        self,
        input_dim: int,
        num_classes: int,
        hidden_dim: int = 256,
        bottleneck_dim: int = 128,
        num_blocks: int = 1,
        drop: float = 0.1,
        drop_path_rate: float = 0.0,
    ):
        super().__init__()
        self.embed = nn.Linear(input_dim, hidden_dim)
        dpr = [x.item() for x in torch.linspace(0, drop_path_rate, num_blocks)]
        blocks = []
        for i in range(num_blocks):
            blocks.append(ResidualBottleneckMLP(hidden_dim, bottleneck_dim, drop=drop, drop_path=dpr[i]))
        self.blocks = nn.ModuleList(blocks)
        self.head_norm = nn.LayerNorm(hidden_dim)
        self.head_drop = nn.Dropout(drop)
        self.classifier = nn.Linear(hidden_dim, num_classes)

    def forward(self, x):
        x = self.embed(x)
        for blk in self.blocks:
            x = blk(x)
        x = self.head_norm(x)
        x = self.head_drop(x)
        logits = self.classifier(x)
        return logits


class ModelEmaV2:
    def __init__(self, model: nn.Module, decay: float = 0.999):
        self.decay = decay
        self.ema_model = self.clone_model(model)
        self.ema_model.eval()

    def clone_model(self, model: nn.Module) -> nn.Module:
        ema_model = ResMLPNet(
            input_dim=model.embed.in_features,
            num_classes=model.classifier.out_features,
            hidden_dim=model.embed.out_features,
            bottleneck_dim=model.blocks[0].fc1.out_features if len(model.blocks) > 0 else model.embed.out_features // 2,
            num_blocks=len(model.blocks),
            drop=0.0,
            drop_path_rate=0.0,
        )
        ema_model.load_state_dict(model.state_dict(), strict=True)
        for p in ema_model.parameters():
            p.requires_grad_(False)
        return ema_model

    @torch.no_grad()
    def update(self, model: nn.Module):
        msd = model.state_dict()
        esd = self.ema_model.state_dict()
        for k in esd.keys():
            if esd[k].dtype.is_floating_point:
                esd[k].mul_(self.decay).add_(msd[k], alpha=(1.0 - self.decay))
            else:
                esd[k].copy_(msd[k])


def mixup_data(x, y, alpha: float):
    if alpha <= 0.0:
        lam = 1.0
        index = torch.arange(x.size(0), device=x.device)
        return x, y, y, lam, index
    lam = np.random.beta(alpha, alpha)
    index = torch.randperm(x.size(0), device=x.device)
    mixed_x = lam * x + (1 - lam) * x[index]
    y_a, y_b = y, y[index]
    return mixed_x, y_a, y_b, lam, index


class WarmupCosineLRScheduler:
    def __init__(self, optimizer, warmup_steps: int, total_steps: int, min_lr: float = 1e-5):
        self.optimizer = optimizer
        self.warmup_steps = max(1, int(warmup_steps))
        self.total_steps = max(1, int(total_steps))
        self.min_lr = min_lr
        self.base_lrs = [group['lr'] for group in optimizer.param_groups]
        self.step_num = 0

    def step(self):
        self.step_num += 1
        for i, param_group in enumerate(self.optimizer.param_groups):
            base_lr = self.base_lrs[i]
            if self.step_num <= self.warmup_steps:
                lr = base_lr * self.step_num / self.warmup_steps
            else:
                progress = (self.step_num - self.warmup_steps) / max(1, self.total_steps - self.warmup_steps)
                cosine = 0.5 * (1.0 + math.cos(math.pi * progress))
                lr = self.min_lr + (base_lr - self.min_lr) * cosine
            param_group['lr'] = lr


def evaluate(model: nn.Module, loader, device: torch.device) -> Tuple[float, float]:
    model.eval()
    correct = 0
    total = 0
    loss_total = 0.0
    criterion = nn.CrossEntropyLoss()
    with torch.no_grad():
        for inputs, targets in loader:
            inputs = inputs.to(device).float()
            targets = targets.to(device).long()
            outputs = model(inputs)
            loss = criterion(outputs, targets)
            loss_total += loss.item() * targets.size(0)
            preds = outputs.argmax(dim=1)
            correct += (preds == targets).sum().item()
            total += targets.numel()
    acc = correct / max(1, total)
    avg_loss = loss_total / max(1, total)
    return acc, avg_loss


class Solution:
    def solve(self, train_loader, val_loader, metadata: dict = None) -> torch.nn.Module:
        set_seed(1337)
        device = torch.device(metadata.get("device", "cpu") if metadata is not None else "cpu")

        input_dim = int(metadata.get("input_dim", 384)) if metadata is not None else 384
        num_classes = int(metadata.get("num_classes", 128)) if metadata is not None else 128
        param_limit = int(metadata.get("param_limit", 200000)) if metadata is not None else 200000

        # Build model with parameter budget
        candidate_hidden = [288, 272, 256, 240, 224, 208, 192, 176, 160]
        model = None
        chosen_hidden = None
        chosen_bottleneck = None
        for h in candidate_hidden:
            b = max(32, h // 2)
            tmp = ResMLPNet(
                input_dim=input_dim,
                num_classes=num_classes,
                hidden_dim=h,
                bottleneck_dim=b,
                num_blocks=1,
                drop=0.1,
                drop_path_rate=0.05,
            )
            p = count_parameters(tmp)
            if p <= param_limit:
                model = tmp
                chosen_hidden = h
                chosen_bottleneck = b
                break
        if model is None:
            # Fallback minimal model
            h = 160
            b = 80
            model = ResMLPNet(
                input_dim=input_dim,
                num_classes=num_classes,
                hidden_dim=h,
                bottleneck_dim=b,
                num_blocks=1,
                drop=0.1,
                drop_path_rate=0.0,
            )
            # If still too large, reduce further by removing block entirely
            if count_parameters(model) > param_limit:
                model = nn.Sequential(
                    nn.Linear(input_dim, 128),
                    nn.ReLU(),
                    nn.Linear(128, num_classes),
                )
        model.to(device)

        # Safety check: ensure under parameter budget
        if count_parameters(model) > param_limit:
            # Last resort: shrink to a smaller two-layer MLP
            hidden_dim = 192
            while True:
                tmp = nn.Sequential(
                    nn.Linear(input_dim, hidden_dim),
                    nn.ReLU(),
                    nn.Linear(hidden_dim, num_classes),
                ).to(device)
                if count_parameters(tmp) <= param_limit or hidden_dim <= 64:
                    model = tmp
                    break
                hidden_dim -= 16

        # Training setup
        epochs = 300
        base_lr = 3e-3
        weight_decay = 0.05
        mixup_alpha = 0.3
        mixup_prob = 0.7
        label_smoothing = 0.1
        grad_clip = 1.0

        optimizer = torch.optim.AdamW(model.parameters(), lr=base_lr, weight_decay=weight_decay, betas=(0.9, 0.999))
        criterion = nn.CrossEntropyLoss(label_smoothing=label_smoothing)

        steps_per_epoch = max(1, len(train_loader))
        total_steps = epochs * steps_per_epoch
        warmup_steps = max(8, int(0.05 * total_steps))
        scheduler = WarmupCosineLRScheduler(optimizer, warmup_steps, total_steps, min_lr=5e-5)

        use_ema = True
        ema_decay = 0.999
        ema = ModelEmaV2(model, decay=ema_decay) if use_ema and isinstance(model, nn.Module) else None

        best_val_acc = -1.0
        best_state = None
        patience = 40
        bad_epochs = 0

        # Training loop
        global_step = 0
        for epoch in range(epochs):
            model.train()
            # Progressively reduce mixup usage over time
            mix_prob = mixup_prob * max(0.0, 1.0 - epoch / (epochs * 0.8))
            for inputs, targets in train_loader:
                inputs = inputs.to(device).float()
                targets = targets.to(device).long()

                do_mix = (np.random.rand() < mix_prob)
                if do_mix:
                    inputs, y_a, y_b, lam, _ = mixup_data(inputs, targets, alpha=mixup_alpha)
                else:
                    lam = 1.0
                    y_a, y_b = targets, targets

                outputs = model(inputs)
                if lam < 1.0:
                    loss = lam * criterion(outputs, y_a) + (1.0 - lam) * criterion(outputs, y_b)
                else:
                    loss = criterion(outputs, targets)

                optimizer.zero_grad()
                loss.backward()
                if grad_clip is not None and grad_clip > 0:
                    nn.utils.clip_grad_norm_(model.parameters(), grad_clip)
                optimizer.step()
                scheduler.step()
                if ema is not None:
                    ema.update(model)

                global_step += 1

            # Validation
            with torch.no_grad():
                val_model = ema.ema_model if ema is not None else model
                val_acc, _ = evaluate(val_model, val_loader, device)

            # Early stopping and best model tracking
            if val_acc > best_val_acc:
                best_val_acc = val_acc
                best_state = (ema.ema_model.state_dict() if ema is not None else model.state_dict())
                bad_epochs = 0
            else:
                bad_epochs += 1
                if bad_epochs >= patience:
                    break

        # Load best weights
        if best_state is not None:
            if isinstance(model, nn.Sequential):
                model.load_state_dict(best_state, strict=False)
            else:
                model.load_state_dict(best_state, strict=False)

        model.eval()
        model.to(device)
        return model