import math
import copy
from typing import Dict, Optional

import torch
import torch.nn as nn
import torch.nn.functional as F


def set_seed(seed: int = 42):
    try:
        import random
        random.seed(seed)
    except Exception:
        pass
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def count_trainable_params(model: nn.Module) -> int:
    return sum(p.numel() for p in model.parameters() if p.requires_grad)


class BottleneckResBlock(nn.Module):
    def __init__(self, width: int, bottleneck: int, p_dropout: float = 0.1):
        super().__init__()
        self.bn1 = nn.BatchNorm1d(width)
        self.fc1 = nn.Linear(width, bottleneck)
        self.bn2 = nn.BatchNorm1d(bottleneck)
        self.fc2 = nn.Linear(bottleneck, width)
        self.act = nn.GELU()
        self.dropout = nn.Dropout(p_dropout)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        identity = x
        out = self.bn1(x)
        out = self.act(out)
        out = self.fc1(out)
        out = self.bn2(out)
        out = self.act(out)
        out = self.dropout(out)
        out = self.fc2(out)
        out = out + identity
        return out


class MLPResNet(nn.Module):
    def __init__(
        self,
        input_dim: int,
        num_classes: int,
        width: int = 256,
        bottleneck: int = 128,
        use_bn_in: bool = True,
        use_bn_pre_logits: bool = True,
        p_dropout: float = 0.10,
    ):
        super().__init__()
        self.fc_in = nn.Linear(input_dim, width)
        self.use_bn_in = use_bn_in
        self.use_bn_pre_logits = use_bn_pre_logits
        if use_bn_in:
            self.bn_in = nn.BatchNorm1d(width)
        self.block = BottleneckResBlock(width, bottleneck, p_dropout=p_dropout)
        if use_bn_pre_logits:
            self.bn_pre = nn.BatchNorm1d(width)
        self.act = nn.GELU()
        self.head_drop = nn.Dropout(p_dropout)
        self.fc_out = nn.Linear(width, num_classes)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self.fc_in(x)
        if self.use_bn_in:
            x = self.bn_in(x)
        x = self.act(x)
        x = self.block(x)
        if self.use_bn_pre_logits:
            x = self.bn_pre(x)
        x = self.act(x)
        x = self.head_drop(x)
        x = self.fc_out(x)
        return x


def soft_cross_entropy(logits: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
    log_probs = F.log_softmax(logits, dim=-1)
    loss = -(targets * log_probs).sum(dim=-1).mean()
    return loss


def cross_entropy_label_smoothing(
    logits: torch.Tensor, targets: torch.Tensor, num_classes: int, smoothing: float = 0.1
) -> torch.Tensor:
    with torch.no_grad():
        true_dist = torch.zeros_like(logits)
        true_dist.fill_(smoothing / (num_classes - 1))
        true_dist.scatter_(1, targets.view(-1, 1), 1.0 - smoothing)
    return soft_cross_entropy(logits, true_dist)


def evaluate(model: nn.Module, data_loader, device: torch.device) -> float:
    model.eval()
    correct = 0
    total = 0
    with torch.no_grad():
        for xb, yb in data_loader:
            xb = xb.to(device=device, dtype=torch.float32, non_blocking=False)
            yb = yb.to(device=device, non_blocking=False)
            logits = model(xb)
            preds = logits.argmax(dim=1)
            correct += (preds == yb).sum().item()
            total += yb.numel()
    return (correct / total) if total > 0 else 0.0


class EMA:
    def __init__(self, model: nn.Module, decay: float = 0.995):
        self.ema = copy.deepcopy(model)
        self.ema.eval()
        for p in self.ema.parameters():
            p.requires_grad_(False)
        self.decay = decay

    @torch.no_grad()
    def update(self, model: nn.Module):
        ema_params = dict(self.ema.named_parameters())
        model_params = dict(model.named_parameters())
        for name in ema_params.keys():
            ema_params[name].mul_(self.decay).add_(model_params[name], alpha=1.0 - self.decay)
        # Update buffers (e.g., BatchNorm running stats) to keep EMA consistent
        for ema_buf, model_buf in zip(self.ema.buffers(), model.buffers()):
            ema_buf.copy_(model_buf)


class Solution:
    def _build_model_under_budget(
        self,
        input_dim: int,
        num_classes: int,
        param_limit: int,
    ) -> nn.Module:
        # Start with a strong architecture and adjust if over budget
        configs = []
        # Preferred config
        configs.append(dict(width=256, bottleneck=128, use_bn_in=True, use_bn_pre_logits=True, p_dropout=0.10))
        # Slightly cheaper: drop pre-logits BN
        configs.append(dict(width=256, bottleneck=128, use_bn_in=True, use_bn_pre_logits=False, p_dropout=0.10))
        # Slightly cheaper: drop input BN
        configs.append(dict(width=256, bottleneck=128, use_bn_in=False, use_bn_pre_logits=False, p_dropout=0.10))
        # Reduce bottleneck
        configs.append(dict(width=256, bottleneck=112, use_bn_in=True, use_bn_pre_logits=True, p_dropout=0.10))
        configs.append(dict(width=256, bottleneck=96, use_bn_in=True, use_bn_pre_logits=True, p_dropout=0.10))
        # Reduce width
        configs.append(dict(width=224, bottleneck=112, use_bn_in=True, use_bn_pre_logits=True, p_dropout=0.10))
        configs.append(dict(width=192, bottleneck=96, use_bn_in=True, use_bn_pre_logits=True, p_dropout=0.10))
        configs.append(dict(width=192, bottleneck=96, use_bn_in=True, use_bn_pre_logits=False, p_dropout=0.10))
        # Fallback plain MLP if necessary
        for cfg in configs:
            model = MLPResNet(input_dim, num_classes, **cfg)
            if count_trainable_params(model) <= param_limit:
                return model
        # Worst-case minimal model
        model = nn.Sequential(
            nn.Linear(input_dim, 192),
            nn.GELU(),
            nn.BatchNorm1d(192),
            nn.Linear(192, 128),
            nn.GELU(),
            nn.Linear(128, num_classes),
        )
        return model

    def solve(self, train_loader, val_loader, metadata: dict = None) -> torch.nn.Module:
        set_seed(42)
        metadata = metadata or {}
        input_dim = int(metadata.get("input_dim", 384))
        num_classes = int(metadata.get("num_classes", 128))
        param_limit = int(metadata.get("param_limit", 200000))
        device_str = metadata.get("device", "cpu")
        device = torch.device(device_str)

        model = self._build_model_under_budget(input_dim, num_classes, param_limit)
        assert count_trainable_params(model) <= param_limit, "Parameter budget exceeded"
        model.to(device)

        # Training hyperparameters
        train_samples = int(metadata.get("train_samples", 2048))
        max_epochs = 160
        # If very small dataset, reduce epochs to avoid overfitting/training time
        if train_samples < 1500:
            max_epochs = 140
        elif train_samples > 3000:
            max_epochs = 180

        base_lr = 3e-3
        min_lr = 3e-4
        weight_decay = 1e-4
        grad_clip = 1.0
        label_smoothing = 0.05

        optimizer = torch.optim.AdamW(model.parameters(), lr=base_lr, weight_decay=weight_decay)
        ema = EMA(model, decay=0.995)

        # Cosine LR with warmup, stepped per-iteration
        steps_per_epoch = max(1, len(train_loader))
        total_steps = max_epochs * steps_per_epoch
        warmup_steps = max(10, int(0.05 * total_steps))

        def adjust_lr(step: int):
            if step < warmup_steps:
                lr = base_lr * float(step + 1) / float(warmup_steps)
            else:
                t = (step - warmup_steps) / max(1, (total_steps - warmup_steps))
                lr = min_lr + 0.5 * (base_lr - min_lr) * (1.0 + math.cos(math.pi * t))
            for pg in optimizer.param_groups:
                pg["lr"] = lr

        # Mixup settings
        mixup_alpha = 0.3
        mixup_active_epochs = int(0.6 * max_epochs)
        beta_dist = torch.distributions.Beta(mixup_alpha, mixup_alpha)

        best_acc = 0.0
        best_state: Optional[Dict[str, torch.Tensor]] = None
        best_from = "model"
        patience = 25
        epochs_no_improve = 0

        global_step = 0
        for epoch in range(max_epochs):
            model.train()
            for xb, yb in train_loader:
                xb = xb.to(device=device, dtype=torch.float32, non_blocking=False)
                yb = yb.to(device=device, non_blocking=False)

                use_mixup = (epoch < mixup_active_epochs) and (mixup_alpha > 0.0) and (xb.size(0) > 1)
                if use_mixup:
                    lam = float(beta_dist.sample())
                    lam = max(lam, 1.0 - lam)  # balanced
                    idx = torch.randperm(xb.size(0), device=xb.device)
                    x_shuffled = xb[idx]
                    y_shuffled = yb[idx]
                    x_mix = lam * xb + (1.0 - lam) * x_shuffled

                    y_one = F.one_hot(yb, num_classes=num_classes).float()
                    y_two = F.one_hot(y_shuffled, num_classes=num_classes).float()
                    y_mix = lam * y_one + (1.0 - lam) * y_two

                    adjust_lr(global_step)
                    optimizer.zero_grad(set_to_none=True)
                    logits = model(x_mix)
                    loss = soft_cross_entropy(logits, y_mix)
                else:
                    adjust_lr(global_step)
                    optimizer.zero_grad(set_to_none=True)
                    logits = model(xb)
                    loss = cross_entropy_label_smoothing(logits, yb, num_classes=num_classes, smoothing=label_smoothing)

                loss.backward()
                if grad_clip is not None and grad_clip > 0:
                    torch.nn.utils.clip_grad_norm_(model.parameters(), grad_clip)
                optimizer.step()
                ema.update(model)

                global_step += 1

            # Validation on both model and EMA to select best
            val_acc_model = evaluate(model, val_loader, device)
            val_acc_ema = evaluate(ema.ema, val_loader, device)
            if val_acc_model >= val_acc_ema:
                curr_acc = val_acc_model
                curr_state = copy.deepcopy(model.state_dict())
                curr_from = "model"
            else:
                curr_acc = val_acc_ema
                curr_state = copy.deepcopy(ema.ema.state_dict())
                curr_from = "ema"

            if curr_acc > best_acc + 1e-4:
                best_acc = curr_acc
                best_state = curr_state
                best_from = curr_from
                epochs_no_improve = 0
            else:
                epochs_no_improve += 1

            if epochs_no_improve >= patience:
                break

        # Load best weights into model and return
        if best_state is not None:
            model.load_state_dict(best_state)
        else:
            # Fallback to EMA if exists
            model.load_state_dict(ema.ema.state_dict())

        model.to(device)
        model.eval()
        return model
