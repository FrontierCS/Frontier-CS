import math
import random
import copy
from typing import Optional, Tuple

import torch
import torch.nn as nn
import torch.nn.functional as F


def set_seed(seed: int = 42):
    random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)


def count_trainable_parameters(model: nn.Module) -> int:
    return sum(p.numel() for p in model.parameters() if p.requires_grad)


class SoftCrossEntropyLoss(nn.Module):
    def __init__(self, reduction: str = "mean"):
        super().__init__()
        self.reduction = reduction

    def forward(self, logits: torch.Tensor, soft_targets: torch.Tensor) -> torch.Tensor:
        log_probs = F.log_softmax(logits, dim=1)
        loss = -(soft_targets * log_probs).sum(dim=1)
        if self.reduction == "mean":
            return loss.mean()
        elif self.reduction == "sum":
            return loss.sum()
        else:
            return loss


class EMA:
    def __init__(self, model: nn.Module, decay: float = 0.995, device: Optional[torch.device] = None):
        self.decay = decay
        self.device = device
        self.ema_model = copy.deepcopy(model).to(device if device is not None else next(model.parameters()).device)
        for p in self.ema_model.parameters():
            p.requires_grad_(False)

    @torch.no_grad()
    def update(self, model: nn.Module):
        msd = model.state_dict()
        for k, v in self.ema_model.state_dict().items():
            if k.endswith("num_batches_tracked"):
                self.ema_model.state_dict()[k].copy_(msd[k])
            else:
                self.ema_model.state_dict()[k].mul_(self.decay).add_(msd[k].detach(), alpha=1.0 - self.decay)

    def state_dict(self):
        return self.ema_model.state_dict()


class MLPResNet(nn.Module):
    def __init__(self, input_dim: int, hidden_dim: int, num_classes: int, dropout: float = 0.15, use_bn3: bool = True):
        super().__init__()
        self.fc1 = nn.Linear(input_dim, hidden_dim, bias=True)
        self.bn1 = nn.BatchNorm1d(hidden_dim)
        self.fc2 = nn.Linear(hidden_dim, hidden_dim, bias=True)
        self.bn2 = nn.BatchNorm1d(hidden_dim)
        self.use_bn3 = use_bn3
        if use_bn3:
            self.bn3 = nn.BatchNorm1d(hidden_dim)
        self.head = nn.Linear(hidden_dim, num_classes, bias=True)
        self.act = nn.SiLU()
        self.drop1 = nn.Dropout(dropout)
        self.drop2 = nn.Dropout(dropout)
        if use_bn3:
            self.drop3 = nn.Dropout(dropout)
        self._init_weights()

    def _init_weights(self):
        for m in self.modules():
            if isinstance(m, nn.Linear):
                nn.init.kaiming_normal_(m.weight, nonlinearity="relu")
                if m.bias is not None:
                    nn.init.zeros_(m.bias)
            elif isinstance(m, nn.BatchNorm1d):
                nn.init.ones_(m.weight)
                nn.init.zeros_(m.bias)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        if x.dim() > 2:
            x = x.view(x.size(0), -1)
        h1 = self.fc1(x)
        h1 = self.bn1(h1)
        h1 = self.act(h1)
        h1 = self.drop1(h1)

        h2 = self.fc2(h1)
        h2 = self.bn2(h2)
        h2 = self.act(h2)
        h2 = self.drop2(h2)

        y = h1 + h2

        if self.use_bn3:
            y = self.bn3(y)
            y = self.act(y)
            y = self.drop3(y)

        logits = self.head(y)
        return logits


def compute_params_with_bn_layers(in_dim: int, hidden: int, out_dim: int, bn_layers: int) -> int:
    # Linear layers: in*hidden + hidden (b) + hidden*hidden + hidden (b) + hidden*out + out (b)
    linear_params = in_dim * hidden + hidden + hidden * hidden + hidden + hidden * out_dim + out_dim
    # BN layers: 2*hidden trainable params per BN
    bn_params = bn_layers * 2 * hidden
    return linear_params + bn_params


def find_max_hidden_under_limit(in_dim: int, out_dim: int, param_limit: int, prefer_bn3: bool = True) -> Tuple[int, int]:
    # Try with 3 BN layers first if prefer_bn3, else 2.
    # Return (hidden, bn_layers)
    for bn_layers in ([3, 2] if prefer_bn3 else [2, 3]):
        # Solve h^2 + (in+out+2 + 2*bn_layers)*h + out <= param_limit
        A = 1
        B = in_dim + out_dim + 2 + 2 * bn_layers
        C = out_dim - param_limit
        # h = floor(-B + sqrt(B^2 - 4AC)) / 2
        disc = B * B - 4 * A * C
        if disc <= 0:
            continue
        h_est = int((math.isqrt(disc) - B) // 2)
        # Adjust to exact valid h
        h = max(1, h_est)
        while compute_params_with_bn_layers(in_dim, h, out_dim, bn_layers) > param_limit and h > 1:
            h -= 1
        if compute_params_with_bn_layers(in_dim, h, out_dim, bn_layers) <= param_limit:
            return h, bn_layers
    # Fallback minimal
    return 64, 2


def mixup_batch(inputs: torch.Tensor, targets: torch.Tensor, num_classes: int, alpha: float) -> Tuple[torch.Tensor, torch.Tensor]:
    if alpha <= 0.0 or inputs.size(0) == 1:
        # Return smoothed one-hot if no mixup; smoothing handled separately
        onehot = F.one_hot(targets, num_classes=num_classes).to(dtype=inputs.dtype)
        return inputs, onehot
    beta = torch.distributions.Beta(alpha, alpha)
    lam = beta.sample().to(inputs.device)
    index = torch.randperm(inputs.size(0), device=inputs.device)
    mixed_inputs = lam * inputs + (1.0 - lam) * inputs[index]
    y1 = F.one_hot(targets, num_classes=num_classes).to(dtype=inputs.dtype)
    y2 = F.one_hot(targets[index], num_classes=num_classes).to(dtype=inputs.dtype)
    mixed_targets = lam * y1 + (1.0 - lam) * y2
    return mixed_inputs, mixed_targets


@torch.no_grad()
def evaluate_accuracy(model: nn.Module, data_loader, device: torch.device) -> float:
    model.eval()
    correct = 0
    total = 0
    for inputs, targets in data_loader:
        inputs = inputs.to(device)
        targets = targets.to(device)
        outputs = model(inputs)
        preds = outputs.argmax(dim=1)
        correct += (preds == targets).sum().item()
        total += targets.numel()
    return correct / max(1, total)


class Solution:
    def solve(self, train_loader, val_loader, metadata: dict = None) -> torch.nn.Module:
        set_seed(42)
        if metadata is None:
            metadata = {}
        input_dim = int(metadata.get("input_dim", 384))
        num_classes = int(metadata.get("num_classes", 128))
        param_limit = int(metadata.get("param_limit", 200000))
        device_str = metadata.get("device", "cpu")
        device = torch.device(device_str if torch.cuda.is_available() and device_str != "cpu" else "cpu")

        # Determine max hidden width under parameter budget
        hidden_dim, bn_layers = find_max_hidden_under_limit(input_dim, num_classes, param_limit, prefer_bn3=True)
        use_bn3 = bn_layers >= 3

        # Build model
        model = MLPResNet(
            input_dim=input_dim,
            hidden_dim=hidden_dim,
            num_classes=num_classes,
            dropout=0.15,
            use_bn3=use_bn3,
        ).to(device)

        # Ensure parameter constraint
        total_params = count_trainable_parameters(model)
        if total_params > param_limit:
            # Fallback to ensure constraint
            hidden_dim, bn_layers = find_max_hidden_under_limit(input_dim, num_classes, param_limit, prefer_bn3=False)
            use_bn3 = bn_layers >= 3
            model = MLPResNet(
                input_dim=input_dim,
                hidden_dim=hidden_dim,
                num_classes=num_classes,
                dropout=0.15,
                use_bn3=use_bn3,
            ).to(device)
            total_params = count_trainable_parameters(model)
        # Safety: clamp if still above
        assert total_params <= param_limit, f"Parameter limit exceeded: {total_params} > {param_limit}"

        # Training configs
        epochs = 200
        lr = 0.0025
        weight_decay = 0.02
        grad_clip_norm = 2.0
        smoothing = 0.05
        mixup_alpha = 0.4
        mixup_epochs = int(0.6 * epochs)
        mixup_prob = 0.7

        optimizer = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=weight_decay, betas=(0.9, 0.999))
        steps_per_epoch = max(1, len(train_loader))
        total_steps = epochs * steps_per_epoch
        try:
            scheduler = torch.optim.lr_scheduler.OneCycleLR(
                optimizer,
                max_lr=lr,
                total_steps=total_steps,
                pct_start=0.25,
                anneal_strategy="cos",
                div_factor=10.0,
                final_div_factor=100.0,
                three_phase=False,
            )
            use_scheduler = True
        except Exception:
            scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=epochs, eta_min=lr * 0.01)
            use_scheduler = False

        criterion_soft = SoftCrossEntropyLoss()
        ema = EMA(model, decay=0.995, device=device)

        best_acc = -1.0
        best_state = None
        patience = 40
        no_improve_epochs = 0

        for epoch in range(epochs):
            model.train()
            epoch_mixup = (epoch < mixup_epochs)
            for inputs, targets in train_loader:
                inputs = inputs.to(device, non_blocking=False)
                targets = targets.to(device, non_blocking=False)

                use_mix = epoch_mixup and (random.random() < mixup_prob)
                if use_mix:
                    inputs_mixed, soft_targets = mixup_batch(inputs, targets, num_classes, alpha=mixup_alpha)
                    logits = model(inputs_mixed)
                    loss = criterion_soft(logits, soft_targets)
                else:
                    logits = model(inputs)
                    # Label smoothing with soft CE
                    one_hot = F.one_hot(targets, num_classes=num_classes).to(dtype=logits.dtype)
                    soft_targets = one_hot * (1.0 - smoothing) + smoothing / num_classes
                    loss = criterion_soft(logits, soft_targets)

                optimizer.zero_grad(set_to_none=True)
                loss.backward()
                if grad_clip_norm is not None and grad_clip_norm > 0:
                    torch.nn.utils.clip_grad_norm_(model.parameters(), grad_clip_norm)
                optimizer.step()
                ema.update(model)
                if use_scheduler and scheduler is not None:
                    scheduler.step()
            if not use_scheduler and scheduler is not None:
                scheduler.step()

            # Evaluate EMA model
            ema_model = ema.ema_model
            val_acc = evaluate_accuracy(ema_model, val_loader, device)
            if val_acc > best_acc:
                best_acc = val_acc
                best_state = copy.deepcopy(ema_model.state_dict())
                no_improve_epochs = 0
            else:
                no_improve_epochs += 1
            if no_improve_epochs >= patience:
                break

        # Load best weights into model and return
        if best_state is not None:
            model.load_state_dict(best_state, strict=True)
        model.to("cpu")
        model.eval()
        return model