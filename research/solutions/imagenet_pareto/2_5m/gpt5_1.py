import math
import random
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F


def set_seed(seed: int = 42):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)


class Standardize(nn.Module):
    def __init__(self, mean: torch.Tensor, std: torch.Tensor, eps: float = 1e-5):
        super().__init__()
        self.register_buffer("mean", mean.view(1, -1))
        self.register_buffer("std", std.view(1, -1))
        self.eps = eps

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return (x - self.mean) / (self.std + self.eps)


class MLPClassifier(nn.Module):
    def __init__(self, input_dim: int, num_classes: int, hidden_dims, dropout: float = 0.1):
        super().__init__()
        layers = []
        bns = []
        dims = [input_dim] + list(hidden_dims)
        for i in range(len(hidden_dims)):
            layers.append(nn.Linear(dims[i], dims[i + 1], bias=True))
            bns.append(nn.BatchNorm1d(dims[i + 1]))
        self.layers = nn.ModuleList(layers)
        self.bns = nn.ModuleList(bns)
        self.act = nn.GELU()
        self.dropout = nn.Dropout(dropout)
        self.head = nn.Linear(hidden_dims[-1], num_classes, bias=True)
        self.norm = None  # will be set externally to a Standardize module

    def set_normalizer(self, norm: nn.Module):
        self.norm = norm

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        if self.norm is not None:
            x = self.norm(x)
        for lin, bn in zip(self.layers, self.bns):
            x = lin(x)
            x = bn(x)
            x = self.act(x)
            x = self.dropout(x)
        x = self.head(x)
        return x


class EMA:
    def __init__(self, model: nn.Module, decay: float = 0.999):
        self.decay = decay
        self.shadow = {}
        self.backup = {}

        for name, param in model.named_parameters():
            if param.requires_grad:
                self.shadow[name] = param.detach().clone()

    @torch.no_grad()
    def update(self, model: nn.Module):
        for name, param in model.named_parameters():
            if not param.requires_grad:
                continue
            assert name in self.shadow
            self.shadow[name].mul_(self.decay).add_(param.detach(), alpha=1.0 - self.decay)

    @torch.no_grad()
    def apply_shadow(self, model: nn.Module):
        self.backup = {}
        for name, param in model.named_parameters():
            if not param.requires_grad:
                continue
            self.backup[name] = param.detach().clone()
            param.data.copy_(self.shadow[name])

    @torch.no_grad()
    def restore(self, model: nn.Module):
        for name, param in model.named_parameters():
            if not param.requires_grad:
                continue
            param.data.copy_(self.backup[name])
        self.backup = {}


def count_trainable_params(model: nn.Module) -> int:
    return sum(p.numel() for p in model.parameters() if p.requires_grad)


def compute_dataset_stats(loader, device: torch.device, input_dim: int):
    n = 0
    mean_acc = torch.zeros(input_dim, device=device, dtype=torch.float32)
    m2_acc = torch.zeros(input_dim, device=device, dtype=torch.float32)
    for xb, yb in loader:
        xb = xb.to(device=device, dtype=torch.float32)
        batch_n = xb.shape[0]
        batch_mean = xb.mean(dim=0)
        batch_var = xb.var(dim=0, unbiased=False)
        if n == 0:
            mean_acc = batch_mean
            m2_acc = batch_var * batch_n
            n = batch_n
        else:
            total_n = n + batch_n
            delta = batch_mean - mean_acc
            new_mean = mean_acc + delta * (batch_n / total_n)
            m2_acc = m2_acc + batch_var * batch_n + (delta.pow(2) * n * batch_n) / total_n
            mean_acc = new_mean
            n = total_n
    variance = m2_acc / max(n, 1)
    std = torch.sqrt(variance + 1e-6)
    std = torch.clamp(std, min=1e-6)
    return mean_acc.detach().cpu(), std.detach().cpu()


def accuracy_from_logits(logits: torch.Tensor, targets: torch.Tensor) -> float:
    preds = logits.argmax(dim=1)
    return (preds == targets).float().mean().item()


def adjust_lr(optimizer, step: int, total_steps: int, base_lr: float, warmup_ratio: float = 0.06, min_lr_ratio: float = 0.05):
    warmup_steps = max(1, int(total_steps * warmup_ratio))
    if step < warmup_steps:
        lr = base_lr * (step + 1) / warmup_steps
    else:
        progress = (step - warmup_steps) / max(1, (total_steps - warmup_steps))
        cosine = 0.5 * (1.0 + math.cos(math.pi * progress))
        lr = min_lr_ratio * base_lr + (base_lr - min_lr_ratio * base_lr) * cosine
    for pg in optimizer.param_groups:
        pg["lr"] = lr
    return lr


class Solution:
    def solve(self, train_loader, val_loader, metadata: dict = None) -> torch.nn.Module:
        set_seed(42)
        device = torch.device((metadata or {}).get("device", "cpu") if torch.cuda.is_available() and (metadata or {}).get("device", "cpu") != "cpu" else "cpu")

        input_dim = int(metadata.get("input_dim", 384)) if metadata else 384
        num_classes = int(metadata.get("num_classes", 128)) if metadata else 128
        param_limit = int(metadata.get("param_limit", 2_500_000)) if metadata else 2_500_000

        # Select architecture close to param limit while staying under it
        candidate_hidden = [1280, 1024, 512, 256]
        def calc_params(hidden):
            model = MLPClassifier(input_dim, num_classes, hidden, dropout=0.1)
            return count_trainable_params(model)

        # Try the main candidate and if exceeding limit, back off gradually
        hidden_dims = candidate_hidden
        while True:
            model_temp = MLPClassifier(input_dim, num_classes, hidden_dims, dropout=0.1)
            param_count = count_trainable_params(model_temp)
            if param_count <= param_limit:
                model = model_temp
                break
            # Reduce the last non-trivial hidden layer by 10% iteratively if needed
            adjusted = False
            for i in range(len(hidden_dims) - 1, -1, -1):
                if hidden_dims[i] > 128:
                    new_val = int(hidden_dims[i] * 0.9)
                    # round to nearest multiple of 32 for better alignment
                    new_val = max(128, (new_val // 32) * 32)
                    if new_val < hidden_dims[i]:
                        hidden_dims = hidden_dims[:i] + [new_val] + hidden_dims[i + 1:]
                        adjusted = True
                        break
            if not adjusted:
                # fallback to a known safe configuration
                hidden_dims = [1024, 1024, 256]
                model = MLPClassifier(input_dim, num_classes, hidden_dims, dropout=0.1)
                break

        # Compute normalization from training data
        mean, std = compute_dataset_stats(train_loader, device, input_dim)
        norm = Standardize(mean=mean, std=std)
        model.set_normalizer(norm)
        model.to(device)

        # Ensure we respect the parameter limit
        total_params = count_trainable_params(model)
        if total_params > param_limit:
            # As a last resort, shrink evenly
            scale = math.sqrt(param_limit / total_params) * 0.98
            new_hidden = []
            for h in hidden_dims:
                nh = max(128, int((h * scale) // 32) * 32)
                new_hidden.append(nh)
            model = MLPClassifier(input_dim, num_classes, new_hidden, dropout=0.1)
            model.set_normalizer(norm)
            model.to(device)
            total_params = count_trainable_params(model)
            if total_params > param_limit:
                # final fallback simple model guaranteed below limit
                model = MLPClassifier(input_dim, num_classes, [1024, 1024], dropout=0.1)
                model.set_normalizer(norm)
                model.to(device)

        # Training configuration
        epochs = 180
        steps_per_epoch = len(train_loader) if hasattr(train_loader, "__len__") else 8
        total_steps = epochs * max(1, steps_per_epoch)
        base_lr = 2e-3
        weight_decay = 1e-4
        label_smooth = 0.05

        optimizer = torch.optim.AdamW(model.parameters(), lr=base_lr, weight_decay=weight_decay, betas=(0.9, 0.999))
        criterion = nn.CrossEntropyLoss(label_smoothing=label_smooth)

        ema = EMA(model, decay=0.997)

        best_val_acc = -1.0
        best_state = None
        best_is_ema = False
        patience = 40
        epochs_since_improve = 0

        global_step = 0
        for epoch in range(epochs):
            model.train()
            for xb, yb in train_loader:
                xb = xb.to(device=device, dtype=torch.float32)
                yb = yb.to(device=device, dtype=torch.long)

                lr_now = adjust_lr(optimizer, global_step, total_steps, base_lr, warmup_ratio=0.08, min_lr_ratio=0.05)

                optimizer.zero_grad(set_to_none=True)
                logits = model(xb)
                loss = criterion(logits, yb)
                loss.backward()
                nn.utils.clip_grad_norm_(model.parameters(), max_norm=5.0)
                optimizer.step()

                with torch.no_grad():
                    ema.update(model)

                global_step += 1

            # Validation
            model.eval()
            with torch.no_grad():
                # Evaluate current weights
                total_correct = 0
                total_count = 0
                for xb, yb in val_loader:
                    xb = xb.to(device=device, dtype=torch.float32)
                    yb = yb.to(device=device, dtype=torch.long)
                    logits = model(xb)
                    preds = logits.argmax(dim=1)
                    total_correct += (preds == yb).sum().item()
                    total_count += yb.numel()
                val_acc_current = total_correct / max(1, total_count)

                # Evaluate EMA weights
                ema.apply_shadow(model)
                total_correct = 0
                total_count = 0
                for xb, yb in val_loader:
                    xb = xb.to(device=device, dtype=torch.float32)
                    yb = yb.to(device=device, dtype=torch.long)
                    logits = model(xb)
                    preds = logits.argmax(dim=1)
                    total_correct += (preds == yb).sum().item()
                    total_count += yb.numel()
                val_acc_ema = total_correct / max(1, total_count)
                ema.restore(model)

            current_is_better = False
            if val_acc_ema >= val_acc_current:
                if val_acc_ema > best_val_acc + 1e-6:
                    current_is_better = True
                    best_val_acc = val_acc_ema
                    best_state = {k: v.cpu().clone() for k, v in ema.shadow.items()}
                    best_is_ema = True
            else:
                if val_acc_current > best_val_acc + 1e-6:
                    current_is_better = True
                    best_val_acc = val_acc_current
                    best_state = {k: v.cpu().clone() for k, v in model.state_dict().items()}
                    best_is_ema = False

            if not current_is_better:
                epochs_since_improve += 1
            else:
                epochs_since_improve = 0

            if epochs_since_improve >= patience:
                break

        # Load best weights into model
        with torch.no_grad():
            if best_state is not None:
                if best_is_ema:
                    # map EMA shadow to model parameters
                    for name, param in model.named_parameters():
                        if param.requires_grad and name in best_state:
                            param.data.copy_(best_state[name].to(device))
                else:
                    model.load_state_dict({k: v.to(device) for k, v in best_state.items()}, strict=True)
            else:
                # As a fallback, prefer EMA weights
                ema.apply_shadow(model)

        return model