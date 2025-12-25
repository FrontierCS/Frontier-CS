import math
import random
import copy
from typing import List

import torch
import torch.nn as nn
import torch.optim as optim


def set_seed(seed: int = 42):
    random.seed(seed)
    torch.manual_seed(seed)


def count_parameters(model: nn.Module) -> int:
    return sum(p.numel() for p in model.parameters() if p.requires_grad)


class InputStandardizer(nn.Module):
    def __init__(self, mean: torch.Tensor, inv_std: torch.Tensor):
        super().__init__()
        self.register_buffer("mean", mean.view(1, -1))
        self.register_buffer("inv_std", inv_std.view(1, -1))

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return (x - self.mean) * self.inv_std


class MLPNet(nn.Module):
    def __init__(self, input_dim: int, num_classes: int, hidden_widths: List[int], dropout: float,
                 mean: torch.Tensor, inv_std: torch.Tensor):
        super().__init__()
        self.pre = InputStandardizer(mean, inv_std)
        dims = [input_dim] + hidden_widths + [num_classes]
        layers = []
        for i in range(len(dims) - 1):
            layers.append(nn.Linear(dims[i], dims[i + 1]))
            if i < len(dims) - 2:
                layers.append(nn.GELU())
                layers.append(nn.Dropout(dropout))
        self.net = nn.Sequential(*layers)
        self._init_weights()

    def _init_weights(self):
        for m in self.modules():
            if isinstance(m, nn.Linear):
                nn.init.kaiming_uniform_(m.weight, a=math.sqrt(5))
                if m.bias is not None:
                    nn.init.zeros_(m.bias)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self.pre(x)
        return self.net(x)


class EMA:
    def __init__(self, model: nn.Module, decay: float = 0.995):
        self.decay = decay
        self.shadow = {}
        self.backup = None
        for name, param in model.named_parameters():
            if param.requires_grad:
                self.shadow[name] = param.data.clone()

    @torch.no_grad()
    def update(self, model: nn.Module):
        for name, param in model.named_parameters():
            if param.requires_grad:
                self.shadow[name].mul_(self.decay).add_(param.data, alpha=1.0 - self.decay)

    def apply_to(self, model: nn.Module):
        self.backup = {}
        for name, param in model.named_parameters():
            if param.requires_grad:
                self.backup[name] = param.data.clone()
                param.data.copy_(self.shadow[name])

    def restore(self, model: nn.Module):
        if self.backup is None:
            return
        for name, param in model.named_parameters():
            if param.requires_grad and name in self.backup:
                param.data.copy_(self.backup[name])
        self.backup = None


def compute_input_stats(train_loader, device: torch.device, input_dim: int):
    total = 0
    sum_vec = torch.zeros(input_dim, dtype=torch.float64)
    sq_sum_vec = torch.zeros(input_dim, dtype=torch.float64)
    for inputs, _ in train_loader:
        x = inputs.to("cpu", non_blocking=False).to(torch.float64)
        sum_vec += x.sum(dim=0)
        sq_sum_vec += (x * x).sum(dim=0)
        total += x.size(0)
    mean = (sum_vec / max(1, total))
    var = (sq_sum_vec / max(1, total)) - (mean * mean)
    var = torch.clamp(var, min=1e-6)
    std = torch.sqrt(var).to(torch.float32)
    mean = mean.to(torch.float32)
    inv_std = 1.0 / std
    return mean, inv_std


def param_count_for_config(input_dim: int, widths: List[int], out_dim: int) -> int:
    dims = [input_dim] + widths + [out_dim]
    params = 0
    for i in range(len(dims) - 1):
        params += dims[i] * dims[i + 1] + dims[i + 1]
    return params


def choose_widths(input_dim: int, num_classes: int, param_limit: int) -> List[int]:
    candidates = [
        [256, 192, 160],
        [256, 192, 144],
        [256, 192, 128],
        [256, 160],
        [224, 192, 160],
        [256, 128],
        [192, 160],
        [256],
        [192],
        [160],
        [128],
        []
    ]
    for widths in candidates:
        if param_count_for_config(input_dim, widths, num_classes) <= param_limit:
            return widths
    # Fallback minimal configuration
    return []


def evaluate(model: nn.Module, loader, device: torch.device, criterion=None):
    model.eval()
    total = 0
    correct = 0
    running_loss = 0.0
    with torch.no_grad():
        for inputs, targets in loader:
            inputs = inputs.to(device, non_blocking=False).float()
            targets = targets.to(device, non_blocking=False).long()
            outputs = model(inputs)
            if criterion is not None:
                running_loss += criterion(outputs, targets).item() * targets.size(0)
            preds = outputs.argmax(dim=1)
            correct += (preds == targets).sum().item()
            total += targets.size(0)
    acc = correct / max(1, total)
    avg_loss = running_loss / max(1, total) if criterion is not None else 0.0
    return avg_loss, acc


class Solution:
    def solve(self, train_loader, val_loader, metadata: dict = None) -> torch.nn.Module:
        set_seed(42)
        device = torch.device((metadata or {}).get("device", "cpu"))
        input_dim = int((metadata or {}).get("input_dim", 384))
        num_classes = int((metadata or {}).get("num_classes", 128))
        param_limit = int((metadata or {}).get("param_limit", 200000))

        # Compute dataset statistics for input normalization
        mean, inv_std = compute_input_stats(train_loader, device, input_dim)

        # Choose architecture under parameter limit
        widths = choose_widths(input_dim, num_classes, param_limit)
        model = MLPNet(input_dim, num_classes, widths, dropout=0.10, mean=mean, inv_std=inv_std).to(device)

        # Safety check for parameter limit
        if count_parameters(model) > param_limit:
            # As a last resort, use a very small network
            widths = []
            model = MLPNet(input_dim, num_classes, widths, dropout=0.10, mean=mean, inv_std=inv_std).to(device)

        # Training setup
        base_lr = 0.0025
        weight_decay = 1e-4
        max_epochs = 180
        warmup_epochs = 8
        min_lr_ratio = 0.05
        patience = 28
        mixup_alpha = 0.2
        mixup_prob = 0.35

        criterion = nn.CrossEntropyLoss(label_smoothing=0.05)
        optimizer = optim.AdamW(model.parameters(), lr=base_lr, weight_decay=weight_decay, betas=(0.9, 0.99))

        def lr_lambda(epoch):
            if epoch < warmup_epochs:
                return float(epoch + 1) / float(max(1, warmup_epochs))
            t = (epoch - warmup_epochs) / float(max(1, max_epochs - warmup_epochs))
            cosine = 0.5 * (1.0 + math.cos(math.pi * t))
            return min_lr_ratio + (1.0 - min_lr_ratio) * cosine

        scheduler = optim.lr_scheduler.LambdaLR(optimizer, lr_lambda=lr_lambda)
        ema = EMA(model, decay=0.995)

        best_val_acc = -1.0
        best_state = None
        epochs_no_improve = 0

        for epoch in range(max_epochs):
            model.train()
            for inputs, targets in train_loader:
                inputs = inputs.to(device, non_blocking=False).float()
                targets = targets.to(device, non_blocking=False).long()

                use_mixup = (random.random() < mixup_prob)
                if use_mixup and inputs.size(0) > 1:
                    lam = random.betavariate(mixup_alpha, mixup_alpha)
                    index = torch.randperm(inputs.size(0), device=device)
                    mixed_x = lam * inputs + (1.0 - lam) * inputs[index, :]
                    y_a, y_b = targets, targets[index]
                    outputs = model(mixed_x)
                    loss = lam * criterion(outputs, y_a) + (1.0 - lam) * criterion(outputs, y_b)
                else:
                    outputs = model(inputs)
                    loss = criterion(outputs, targets)

                optimizer.zero_grad()
                loss.backward()
                nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
                optimizer.step()
                ema.update(model)

            scheduler.step()

            # Validation with EMA weights
            ema.apply_to(model)
            _, val_acc = evaluate(model, val_loader, device, criterion=None)
            ema.restore(model)

            if val_acc > best_val_acc + 1e-6:
                best_val_acc = val_acc
                # Save EMA weights as best snapshot
                ema.apply_to(model)
                best_state = {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}
                ema.restore(model)
                epochs_no_improve = 0
            else:
                epochs_no_improve += 1

            if epochs_no_improve >= patience:
                break

        if best_state is not None:
            model.load_state_dict(best_state, strict=True)
        else:
            ema.apply_to(model)

        model.to(device)
        model.eval()
        return model
