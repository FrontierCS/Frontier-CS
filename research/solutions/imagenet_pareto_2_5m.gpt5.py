import os
import math
import random
from copy import deepcopy
import torch
import torch.nn as nn
import torch.nn.functional as F


def set_seed(seed: int = 42):
    random.seed(seed)
    torch.manual_seed(seed)
    try:
        import numpy as np
        np.random.seed(seed)
    except Exception:
        pass


def soft_cross_entropy(logits: torch.Tensor, target_probs: torch.Tensor) -> torch.Tensor:
    log_probs = F.log_softmax(logits, dim=-1)
    loss = -(target_probs * log_probs).sum(dim=-1).mean()
    return loss


def one_hot_smooth(labels: torch.Tensor, num_classes: int, smoothing: float = 0.0) -> torch.Tensor:
    with torch.no_grad():
        y = F.one_hot(labels, num_classes=num_classes).float()
        if smoothing > 0.0:
            y = y * (1.0 - smoothing) + smoothing / num_classes
    return y


def mixup_data(x, y, num_classes, alpha=0.4):
    if alpha <= 0.0:
        return x, F.one_hot(y, num_classes=num_classes).float(), 1.0
    lam = torch._sample_dirichlet(torch.tensor([alpha, alpha], dtype=x.dtype, device=x.device))[0].item()
    lam = max(lam, 1.0 - lam)
    index = torch.randperm(x.size(0), device=x.device)
    x_mix = lam * x + (1.0 - lam) * x[index]
    y1 = F.one_hot(y, num_classes=num_classes).float()
    y2 = y1[index]
    y_mix = lam * y1 + (1.0 - lam) * y2
    return x_mix, y_mix, lam


def count_trainable_params(model: nn.Module) -> int:
    return sum(p.numel() for p in model.parameters() if p.requires_grad)


class EMA:
    def __init__(self, model: nn.Module, decay: float = 0.995):
        self.decay = decay
        self.shadow = {}
        self.backup = {}
        for name, param in model.named_parameters():
            if param.requires_grad:
                self.shadow[name] = param.detach().clone()

    @torch.no_grad()
    def update(self, model: nn.Module):
        for name, param in model.named_parameters():
            if param.requires_grad:
                assert name in self.shadow
                new_average = (1.0 - self.decay) * param.detach() + self.decay * self.shadow[name]
                self.shadow[name] = new_average.clone()

    def apply_shadow(self, model: nn.Module):
        self.backup = {}
        for name, param in model.named_parameters():
            if param.requires_grad and name in self.shadow:
                self.backup[name] = param.detach().clone()
                param.data.copy_(self.shadow[name].data)

    def restore(self, model: nn.Module):
        for name, param in model.named_parameters():
            if param.requires_grad and name in self.backup:
                param.data.copy_(self.backup[name].data)
        self.backup = {}


class MLPNet(nn.Module):
    def __init__(self, input_dim: int, num_classes: int, hidden_dims, dropout=0.15, gated_first=True):
        super().__init__()
        self.input_dim = input_dim
        self.num_classes = num_classes
        self.hidden_dims = list(hidden_dims)
        self.gated_first = gated_first

        self.in_norm = nn.LayerNorm(input_dim)
        self.act = nn.SiLU()
        self.dropout = nn.Dropout(dropout)

        if self.gated_first:
            self.fc1 = nn.Linear(input_dim, self.hidden_dims[0])
            self.fc1_gate = nn.Linear(input_dim, self.hidden_dims[0])
        else:
            self.fc1 = nn.Linear(input_dim, self.hidden_dims[0])
            self.fc1_gate = None
        self.norm1 = nn.LayerNorm(self.hidden_dims[0])

        self.layers = nn.ModuleList()
        self.norms = nn.ModuleList()
        for i in range(len(self.hidden_dims) - 1):
            self.layers.append(nn.Linear(self.hidden_dims[i], self.hidden_dims[i + 1]))
            self.norms.append(nn.LayerNorm(self.hidden_dims[i + 1]))

        self.out = nn.Linear(self.hidden_dims[-1], num_classes)

        # Kaiming init for linear layers
        for m in self.modules():
            if isinstance(m, nn.Linear):
                nn.init.kaiming_normal_(m.weight, a=0.0, mode='fan_in', nonlinearity='relu')
                if m.bias is not None:
                    nn.init.zeros_(m.bias)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self.in_norm(x)
        if self.fc1_gate is not None:
            a = self.fc1(x)
            g = torch.sigmoid(self.fc1_gate(x))
            x = self.act(a) * g
        else:
            x = self.act(self.fc1(x))
        x = self.dropout(x)
        x = self.norm1(x)

        for lin, norm in zip(self.layers, self.norms):
            x = self.act(lin(x))
            x = self.dropout(x)
            x = norm(x)

        logits = self.out(x)
        return logits


def estimate_params(input_dim: int, hidden_dims, num_classes: int, gated_first: bool = True) -> int:
    total = 0
    # input layer norm
    total += 2 * input_dim
    # first layer
    if gated_first:
        total += 2 * (input_dim * hidden_dims[0] + hidden_dims[0])  # gate + value
    else:
        total += input_dim * hidden_dims[0] + hidden_dims[0]
    # norm after first
    total += 2 * hidden_dims[0]
    # hidden transitions
    for i in range(len(hidden_dims) - 1):
        total += hidden_dims[i] * hidden_dims[i + 1] + hidden_dims[i + 1]  # linear + bias
        total += 2 * hidden_dims[i + 1]  # layernorm
    # output
    total += hidden_dims[-1] * num_classes + num_classes
    return total


def build_model_within_budget(input_dim: int, num_classes: int, param_limit: int):
    # Base hidden configuration
    base_hidden = [1152, 768, 512, 256]
    gated_first = True

    # Try scaling up or down to fit best under limit
    candidates = []
    for mult in [1.40, 1.35, 1.30, 1.25, 1.20, 1.15, 1.10, 1.05, 1.00, 0.95, 0.90, 0.85, 0.80]:
        hidden = []
        for h in base_hidden:
            hh = max(64, int(round(h * mult / 32)) * 32)
            hidden.append(hh)
        params = estimate_params(input_dim, hidden, num_classes, gated_first=gated_first)
        if params <= param_limit:
            candidates.append((params, hidden, gated_first))
    # If no candidate found, try without gating
    if not candidates:
        gated_first = False
        for mult in [1.60, 1.50, 1.40, 1.30, 1.25, 1.20, 1.15, 1.10, 1.05, 1.00, 0.95, 0.90, 0.85, 0.80]:
            hidden = []
            for h in base_hidden:
                hh = max(64, int(round(h * mult / 32)) * 32)
                hidden.append(hh)
            params = estimate_params(input_dim, hidden, num_classes, gated_first=gated_first)
            if params <= param_limit:
                candidates.append((params, hidden, gated_first))
    # As a final fallback, baseline 384->1024->1024->num_classes (no gating)
    if not candidates:
        hidden = [1024, 1024]
        gated_first = False
        params = estimate_params(input_dim, hidden, num_classes, gated_first=gated_first)
        if params <= param_limit:
            candidates.append((params, hidden, gated_first))
        else:
            # Scale down until fit
            h = 896
            while h >= 128:
                hidden = [h, h]
                params = estimate_params(input_dim, hidden, num_classes, gated_first=gated_first)
                if params <= param_limit:
                    candidates.append((params, hidden, gated_first))
                    break
                h -= 64

    # Choose the candidate with max params under budget
    if not candidates:
        # Extreme fallback tiny model
        hidden = [512, 256]
        gated_first = False
        model = MLPNet(input_dim, num_classes, hidden, dropout=0.15, gated_first=gated_first)
        return model

    candidates.sort(key=lambda x: x[0], reverse=True)
    _, best_hidden, best_gated = candidates[0]
    model = MLPNet(input_dim, num_classes, best_hidden, dropout=0.15, gated_first=best_gated)
    return model


def evaluate_accuracy(model: nn.Module, loader, device: torch.device) -> float:
    model.eval()
    correct = 0
    total = 0
    with torch.no_grad():
        for inputs, targets in loader:
            inputs = inputs.to(device)
            targets = targets.to(device)
            outputs = model(inputs)
            preds = outputs.argmax(dim=1)
            correct += (preds == targets).sum().item()
            total += targets.numel()
    return correct / total if total > 0 else 0.0


class Solution:
    def solve(self, train_loader, val_loader, metadata: dict = None) -> torch.nn.Module:
        set_seed(42)
        try:
            torch.set_num_threads(min(8, os.cpu_count() or 8))
        except Exception:
            pass

        if metadata is None:
            metadata = {}
        input_dim = int(metadata.get("input_dim", 384))
        num_classes = int(metadata.get("num_classes", 128))
        param_limit = int(metadata.get("param_limit", 2_500_000))
        device_str = metadata.get("device", "cpu")
        device = torch.device(device_str if device_str in ["cpu", "cuda"] and torch.cuda.is_available() else "cpu")
        baseline_acc = float(metadata.get("baseline_accuracy", 0.85))

        model = build_model_within_budget(input_dim, num_classes, param_limit)
        model.to(device)

        # Verify parameter constraint
        params = count_trainable_params(model)
        if params > param_limit:
            # Reduce to safe baseline
            model = MLPNet(input_dim, num_classes, [1024, 1024], dropout=0.15, gated_first=False).to(device)

        # Optimizer with decoupled weight decay
        weight_decay = 0.03
        lr_base = 0.003
        batch_size = getattr(train_loader, "batch_size", 128) or 128
        lr = float(lr_base * max(0.5, min(1.5, math.sqrt(batch_size / 128.0))))

        decay_params = []
        no_decay_params = []
        for n, p in model.named_parameters():
            if not p.requires_grad:
                continue
            if p.ndim == 1 or n.endswith(".bias") or "norm" in n.lower():
                no_decay_params.append(p)
            else:
                decay_params.append(p)
        optimizer = torch.optim.AdamW(
            [
                {"params": decay_params, "weight_decay": weight_decay},
                {"params": no_decay_params, "weight_decay": 0.0},
            ],
            lr=lr,
            betas=(0.9, 0.999),
        )

        # Training hyperparameters
        try:
            train_len = int(metadata.get("train_samples", None) or len(getattr(train_loader, "dataset", [])))
        except Exception:
            train_len = 2048
        epochs = 240 if train_len <= 4096 else 160
        min_epochs = max(60, epochs // 3)
        patience = 40

        steps_per_epoch = max(1, len(train_loader))
        total_steps = epochs * steps_per_epoch
        warmup_steps = max(10, int(0.05 * total_steps))
        final_lr = lr * 0.05

        def adjust_lr(step_idx: int):
            if step_idx < warmup_steps:
                lr_now = lr * float(step_idx + 1) / float(warmup_steps)
            else:
                t = (step_idx - warmup_steps) / float(max(1, total_steps - warmup_steps))
                lr_now = final_lr + 0.5 * (lr - final_lr) * (1.0 + math.cos(math.pi * t))
            for pg in optimizer.param_groups:
                pg["lr"] = lr_now

        label_smoothing = 0.05
        mixup_alpha = 0.4
        mixup_prob = 0.6

        ema = EMA(model, decay=0.995)

        best_val_acc = -1.0
        best_state = None
        epochs_no_improve = 0
        global_step = 0

        for epoch in range(epochs):
            model.train()
            for inputs, targets in train_loader:
                inputs = inputs.to(device)
                targets = targets.to(device)

                adjust_lr(global_step)

                use_mix = (random.random() < mixup_prob)
                if use_mix:
                    x_mix, y_mix, _ = mixup_data(inputs, targets, num_classes, alpha=mixup_alpha)
                    y_mix = y_mix * (1.0 - label_smoothing) + label_smoothing / num_classes
                    logits = model(x_mix)
                    loss = soft_cross_entropy(logits, y_mix)
                else:
                    y_smooth = one_hot_smooth(targets, num_classes, smoothing=label_smoothing)
                    logits = model(inputs)
                    loss = soft_cross_entropy(logits, y_smooth)

                optimizer.zero_grad(set_to_none=True)
                loss.backward()
                nn.utils.clip_grad_norm_(model.parameters(), max_norm=5.0)
                optimizer.step()
                ema.update(model)

                global_step += 1

            # Validation
            if val_loader is not None:
                ema.apply_shadow(model)
                val_acc = evaluate_accuracy(model, val_loader, device)
                if val_acc > best_val_acc:
                    best_val_acc = val_acc
                    best_state = deepcopy(model.state_dict())
                    epochs_no_improve = 0
                else:
                    epochs_no_improve += 1
                ema.restore(model)
            else:
                # If no val loader, track training accuracy roughly
                ema.apply_shadow(model)
                val_acc = evaluate_accuracy(model, train_loader, device)
                if val_acc > best_val_acc:
                    best_val_acc = val_acc
                    best_state = deepcopy(model.state_dict())
                    epochs_no_improve = 0
                else:
                    epochs_no_improve += 1
                ema.restore(model)

            if epoch + 1 >= min_epochs and epochs_no_improve >= patience:
                break

        # Load best EMA weights if available
        if best_state is not None:
            model.load_state_dict(best_state)
        else:
            # Apply EMA final weights
            ema.apply_shadow(model)
            ema.restore(model)  # keep EMA weights in model after apply+restore trick by copying
            # Actually apply_shadow then copy to best_state
            ema.apply_shadow(model)
            best_state = deepcopy(model.state_dict())
            ema.restore(model)
            model.load_state_dict(best_state)

        model.to(device)
        return model