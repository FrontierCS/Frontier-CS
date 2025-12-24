import math
import random
import copy
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F


def set_seed(seed: int = 42):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)


def count_params(model: nn.Module) -> int:
    return sum(p.numel() for p in model.parameters() if p.requires_grad)


class ResidualMLP(nn.Module):
    def __init__(self, input_dim: int, hidden_dim: int, num_classes: int, dropout: float = 0.1):
        super().__init__()
        self.bn0 = nn.BatchNorm1d(input_dim)
        self.fc1 = nn.Linear(input_dim, hidden_dim, bias=True)
        self.bn1 = nn.BatchNorm1d(hidden_dim)
        self.fc_res = nn.Linear(hidden_dim, hidden_dim, bias=True)
        self.bn2 = nn.BatchNorm1d(hidden_dim)
        self.fc_out = nn.Linear(hidden_dim, num_classes, bias=True)
        self.drop = nn.Dropout(dropout)
        self.res_scale = nn.Parameter(torch.tensor(0.1, dtype=torch.float32))

        self.reset_parameters()

    def reset_parameters(self):
        for m in self.modules():
            if isinstance(m, nn.Linear):
                nn.init.kaiming_normal_(m.weight, nonlinearity='relu')
                if m.bias is not None:
                    nn.init.zeros_(m.bias)
            elif isinstance(m, nn.BatchNorm1d):
                nn.init.ones_(m.weight)
                nn.init.zeros_(m.bias)

    def forward(self, x):
        x = x.float()
        x = self.bn0(x)
        x = self.fc1(x)
        x = self.bn1(x)
        x = F.gelu(x)
        x = self.drop(x)

        res = self.fc_res(x)
        res = self.bn2(res)
        res = F.gelu(res)
        res = self.drop(res)

        x = x + self.res_scale * res
        out = self.fc_out(x)
        return out


def max_hidden_dim(input_dim: int, num_classes: int, param_limit: int) -> int:
    # Parameter formula:
    # p(h) = h^2 + h*(input_dim + num_classes + 6) + (num_classes + 2*input_dim + 1)
    a = 1
    b = input_dim + num_classes + 6
    c = (num_classes + 2 * input_dim + 1) - param_limit
    disc = b * b - 4 * a * c
    if disc < 0:
        # In practice this should not happen; fall back to minimal hidden
        return 32
    h_float = (-b + math.sqrt(disc)) / (2 * a)
    # Round down to nearest multiple of 8 for efficiency
    h = max(16, int(h_float) // 8 * 8)
    return h


class WarmupCosineScheduler:
    def __init__(self, optimizer, total_steps: int, warmup_steps: int, max_lr: float, final_lr: float):
        self.optimizer = optimizer
        self.total_steps = max(1, total_steps)
        self.warmup_steps = max(1, warmup_steps)
        self.max_lr = max_lr
        self.final_lr = final_lr
        self.step_count = 0

    def get_lr_at_step(self, step: int) -> float:
        if step < self.warmup_steps:
            return self.max_lr * (step + 1) / self.warmup_steps
        progress = (step - self.warmup_steps) / max(1, self.total_steps - self.warmup_steps)
        cosine_decay = 0.5 * (1 + math.cos(math.pi * progress))
        lr = self.final_lr + (self.max_lr - self.final_lr) * cosine_decay
        return lr

    def step(self):
        lr = self.get_lr_at_step(self.step_count)
        for pg in self.optimizer.param_groups:
            pg['lr'] = lr
        self.step_count += 1


def evaluate(model: nn.Module, data_loader, device) -> float:
    model.eval()
    correct = 0
    total = 0
    with torch.no_grad():
        for inputs, targets in data_loader:
            inputs = inputs.to(device)
            targets = targets.to(device, dtype=torch.long)
            outputs = model(inputs)
            preds = outputs.argmax(dim=1)
            correct += (preds == targets).sum().item()
            total += targets.numel()
    return (correct / total) if total > 0 else 0.0


def mixup(inputs, targets, alpha: float = 0.2):
    if alpha <= 0.0:
        return inputs, targets, targets, 1.0
    lam = np.random.beta(alpha, alpha)
    batch_size = inputs.size(0)
    index = torch.randperm(batch_size, device=inputs.device)
    mixed_inputs = lam * inputs + (1 - lam) * inputs[index]
    targets_a = targets
    targets_b = targets[index]
    return mixed_inputs, targets_a, targets_b, lam


class Solution:
    def solve(self, train_loader, val_loader, metadata: dict = None) -> torch.nn.Module:
        set_seed(42)
        if metadata is None:
            metadata = {}
        input_dim = int(metadata.get("input_dim", 384))
        num_classes = int(metadata.get("num_classes", 128))
        param_limit = int(metadata.get("param_limit", 200000))
        device = metadata.get("device", "cpu")

        # Determine hidden dimension within parameter budget
        h_max = max_hidden_dim(input_dim, num_classes, param_limit)
        # Prefer 256 if budget allows, otherwise use computed max
        preferred = 256
        def param_count_for_h(h):
            # exact parameter count for our architecture
            return h * h + h * (input_dim + num_classes + 6) + (num_classes + 2 * input_dim + 1)
        if param_count_for_h(preferred) <= param_limit:
            hidden_dim = preferred
        else:
            # ensure not exceeding limit
            # step down by 8 until within limit
            hidden_dim = h_max
            while hidden_dim > 16 and param_count_for_h(hidden_dim) > param_limit:
                hidden_dim -= 8

        model = ResidualMLP(input_dim=input_dim, hidden_dim=hidden_dim, num_classes=num_classes, dropout=0.1)
        # Safety check: ensure parameter count under limit
        if count_params(model) > param_limit:
            # As a fallback, reduce hidden_dim more aggressively
            hd = hidden_dim
            while hd > 16 and count_params(ResidualMLP(input_dim, hd, num_classes, dropout=0.1)) > param_limit:
                hd -= 8
            hidden_dim = max(16, hd)
            model = ResidualMLP(input_dim=input_dim, hidden_dim=hidden_dim, num_classes=num_classes, dropout=0.1)

        model.to(device)

        # Optimizer and loss
        base_lr = 3e-3
        final_lr = 2e-4
        weight_decay = 4e-4
        optimizer = torch.optim.AdamW(model.parameters(), lr=base_lr, weight_decay=weight_decay, betas=(0.9, 0.999))
        # Label smoothing helps with synthetic noise
        criterion = nn.CrossEntropyLoss(label_smoothing=0.03)

        # Scheduler
        max_epochs = 140
        try:
            num_train_steps = max_epochs * len(train_loader)
        except TypeError:
            num_train_steps = max_epochs * 1
        warmup_steps = max(10, int(0.1 * num_train_steps))
        scheduler = WarmupCosineScheduler(optimizer, total_steps=num_train_steps, warmup_steps=warmup_steps, max_lr=base_lr, final_lr=final_lr)

        # Early stopping setup
        patience = 20
        best_val_acc = -1.0
        best_state = None
        epochs_no_improve = 0

        mixup_alpha = 0.2
        mixup_prob = 0.6

        for epoch in range(max_epochs):
            model.train()
            for inputs, targets in train_loader:
                inputs = inputs.to(device)
                targets = targets.to(device, dtype=torch.long)

                if mixup_alpha > 0 and random.random() < mixup_prob:
                    mixed_inputs, targets_a, targets_b, lam = mixup(inputs, targets, alpha=mixup_alpha)
                    outputs = model(mixed_inputs)
                    loss = lam * criterion(outputs, targets_a) + (1.0 - lam) * criterion(outputs, targets_b)
                else:
                    outputs = model(inputs)
                    loss = criterion(outputs, targets)

                optimizer.zero_grad()
                loss.backward()
                torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
                optimizer.step()
                scheduler.step()

            # Validation
            if val_loader is not None:
                val_acc = evaluate(model, val_loader, device)
            else:
                # If no validation loader is provided, evaluate on training data
                val_acc = evaluate(model, train_loader, device)

            if val_acc > best_val_acc:
                best_val_acc = val_acc
                best_state = copy.deepcopy({k: v.detach().cpu() for k, v in model.state_dict().items()})
                epochs_no_improve = 0
            else:
                epochs_no_improve += 1

            if epochs_no_improve >= patience:
                break

        if best_state is not None:
            model.load_state_dict(best_state, strict=True)

        model.eval()
        model.to("cpu")
        return model
