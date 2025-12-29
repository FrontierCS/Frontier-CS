import math
import copy
import random
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim


def set_seed(seed: int = 42):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)


class Standardize(nn.Module):
    def __init__(self, dim: int, eps: float = 1e-8):
        super().__init__()
        self.eps = eps
        self.register_buffer("mean", torch.zeros(dim))
        self.register_buffer("invstd", torch.ones(dim))

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return (x - self.mean) * self.invstd

    @torch.no_grad()
    def update(self, mean: torch.Tensor, std: torch.Tensor):
        std = std.clone()
        std[std < self.eps] = 1.0
        self.mean.copy_(mean.to(self.mean.dtype))
        self.invstd.copy_((1.0 / std).to(self.invstd.dtype))


class ResBlock(nn.Module):
    def __init__(self, dim: int, dropout: float = 0.1):
        super().__init__()
        self.ln = nn.LayerNorm(dim)
        self.fc = nn.Linear(dim, dim)
        self.act = nn.GELU()
        self.drop = nn.Dropout(dropout)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        z = self.ln(x)
        z = self.fc(z)
        z = self.act(z)
        z = self.drop(z)
        return x + z


class MLPResNet(nn.Module):
    def __init__(self, in_dim: int, num_classes: int, width: int, nblocks: int, dropout: float = 0.1):
        super().__init__()
        self.std = Standardize(in_dim)
        self.in_proj = nn.Linear(in_dim, width)
        self.blocks = nn.ModuleList([ResBlock(width, dropout=dropout) for _ in range(nblocks)])
        self.out_norm = nn.LayerNorm(width)
        self.out_drop = nn.Dropout(dropout)
        self.head = nn.Linear(width, num_classes)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self.std(x)
        x = self.in_proj(x)
        for blk in self.blocks:
            x = blk(x)
        x = self.out_norm(x)
        x = self.out_drop(x)
        x = self.head(x)
        return x


def count_trainable_params(model: nn.Module) -> int:
    return sum(p.numel() for p in model.parameters() if p.requires_grad)


def compute_feature_stats(loader, device: str = "cpu"):
    # Compute per-feature mean and std across the training set
    first_batch = True
    n_total = 0
    sum_vec = None
    sum_sq_vec = None
    for inputs, _ in loader:
        x = inputs.to("cpu")
        if first_batch:
            d = x.shape[1]
            sum_vec = torch.zeros(d, dtype=torch.float64)
            sum_sq_vec = torch.zeros(d, dtype=torch.float64)
            first_batch = False
        sum_vec += x.to(torch.float64).sum(dim=0)
        sum_sq_vec += (x.to(torch.float64) ** 2).sum(dim=0)
        n_total += x.size(0)
    mean = (sum_vec / max(1, n_total)).to(torch.float32)
    var = (sum_sq_vec / max(1, n_total) - (mean.to(torch.float64) ** 2)).clamp_min_(1e-8).to(torch.float32)
    std = torch.sqrt(var)
    return mean, std


def get_param_groups(model: nn.Module, weight_decay: float):
    decay_params = []
    no_decay_params = []
    for module_name, module in model.named_modules():
        for param_name, param in module.named_parameters(recurse=False):
            if not param.requires_grad:
                continue
            full_name = f"{module_name}.{param_name}" if module_name else param_name
            if isinstance(module, (nn.LayerNorm, nn.BatchNorm1d)) or param_name.endswith("bias"):
                no_decay_params.append(param)
            else:
                decay_params.append(param)
    return [
        {"params": decay_params, "weight_decay": weight_decay},
        {"params": no_decay_params, "weight_decay": 0.0},
    ]


class WarmupCosineLR(optim.lr_scheduler._LRScheduler):
    def __init__(self, optimizer, warmup_steps: int, total_steps: int, last_epoch: int = -1):
        self.warmup_steps = max(1, warmup_steps)
        self.total_steps = max(self.warmup_steps + 1, total_steps)
        super().__init__(optimizer, last_epoch)

    def get_lr(self):
        step = self.last_epoch + 1
        lrs = []
        for base_lr in self.base_lrs:
            if step <= self.warmup_steps:
                scale = step / float(self.warmup_steps)
            else:
                progress = (step - self.warmup_steps) / float(max(1, self.total_steps - self.warmup_steps))
                scale = 0.5 * (1.0 + math.cos(math.pi * progress))
            lrs.append(base_lr * scale)
        return lrs


def evaluate(model: nn.Module, loader, device: str = "cpu"):
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
    acc = correct / max(1, total)
    return acc


class Solution:
    def solve(self, train_loader, val_loader, metadata: dict = None) -> torch.nn.Module:
        set_seed(42)
        device = metadata.get("device", "cpu") if metadata is not None else "cpu"
        input_dim = int(metadata.get("input_dim", 384)) if metadata is not None else 384
        num_classes = int(metadata.get("num_classes", 128)) if metadata is not None else 128
        param_limit = int(metadata.get("param_limit", 200_000)) if metadata is not None else 200_000

        # Search for a strong architecture under parameter budget
        best_model = None
        best_params = -1
        chosen_width, chosen_blocks = None, None
        # Prefer wider models (fewer blocks) for this budget
        candidate_blocks = [2, 3]
        for blocks in candidate_blocks:
            for width in range(320, 95, -1):
                model = MLPResNet(input_dim, num_classes, width, blocks, dropout=0.10)
                params = count_trainable_params(model)
                if params <= param_limit and params > best_params:
                    best_params = params
                    best_model = model
                    chosen_width, chosen_blocks = width, blocks
        if best_model is None:
            # Fallback safe small model
            chosen_width, chosen_blocks = 160, 2
            best_model = MLPResNet(input_dim, num_classes, chosen_width, chosen_blocks, dropout=0.10)
            best_params = count_trainable_params(best_model)

        # Compute and set feature standardization from train set
        mean, std = compute_feature_stats(train_loader, device="cpu")
        best_model.std.update(mean, std)

        model = best_model.to(device)

        # Training setup
        lr = 0.0025
        weight_decay = 1e-4
        max_epochs = 120
        patience = 20
        criterion = nn.CrossEntropyLoss(label_smoothing=0.05)

        param_groups = get_param_groups(model, weight_decay)
        optimizer = optim.AdamW(param_groups, lr=lr, betas=(0.9, 0.999))

        steps_per_epoch = max(1, len(train_loader))
        total_steps = max_epochs * steps_per_epoch
        warmup_steps = max(10, int(0.05 * total_steps))
        scheduler = WarmupCosineLR(optimizer, warmup_steps=warmup_steps, total_steps=total_steps)

        best_state = copy.deepcopy(model.state_dict())
        best_val_acc = 0.0
        epochs_no_improve = 0
        global_step = 0

        for epoch in range(max_epochs):
            model.train()
            for inputs, targets in train_loader:
                inputs = inputs.to(device)
                targets = targets.to(device)

                optimizer.zero_grad(set_to_none=True)
                outputs = model(inputs)
                loss = criterion(outputs, targets)
                loss.backward()
                torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
                optimizer.step()
                scheduler.step()
                global_step += 1

            # Validation
            val_acc = evaluate(model, val_loader, device=device)
            if val_acc > best_val_acc + 1e-6:
                best_val_acc = val_acc
                best_state = copy.deepcopy(model.state_dict())
                epochs_no_improve = 0
            else:
                epochs_no_improve += 1
                if epochs_no_improve >= patience:
                    break

        # Load best weights
        model.load_state_dict(best_state)

        # Final check to ensure we adhere to parameter limit
        model = model.to("cpu" if device == "cpu" else device)
        assert count_trainable_params(model) <= param_limit, "Model exceeds parameter limit"

        return model