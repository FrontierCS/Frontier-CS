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


def count_trainable_params(model: nn.Module) -> int:
    return sum(p.numel() for p in model.parameters() if p.requires_grad)


class ResMLPBlock(nn.Module):
    def __init__(self, dim: int, dropout: float = 0.1):
        super().__init__()
        self.norm = nn.LayerNorm(dim)
        self.fc1 = nn.Linear(dim, dim)
        self.act = nn.GELU()
        self.drop = nn.Dropout(dropout)
        self.fc2 = nn.Linear(dim, dim)

    def forward(self, x):
        y = self.norm(x)
        y = self.fc1(y)
        y = self.act(y)
        y = self.drop(y)
        y = self.fc2(y)
        y = self.drop(y)
        return x + y


class ResMLP(nn.Module):
    def __init__(self, input_dim: int, num_classes: int, width: int, num_blocks: int, dropout: float = 0.1):
        super().__init__()
        self.input = nn.Linear(input_dim, width)
        self.blocks = nn.ModuleList([ResMLPBlock(width, dropout=dropout) for _ in range(num_blocks)])
        self.dropout = nn.Dropout(dropout)
        self.head = nn.Linear(width, num_classes)
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

    def forward(self, x):
        x = self.input(x)
        for blk in self.blocks:
            x = blk(x)
        x = self.dropout(x)
        x = self.head(x)
        return x


class ModelEMA:
    def __init__(self, model: nn.Module, decay: float = 0.995):
        self.decay = decay
        self.ema = copy.deepcopy(model)
        for p in self.ema.parameters():
            p.requires_grad_(False)

    @torch.no_grad()
    def update(self, model: nn.Module):
        d = self.decay
        for p_ema, p in zip(self.ema.parameters(), model.parameters()):
            p_ema.data.mul_(d).add_(p.data, alpha=1.0 - d)
        for b_ema, b in zip(self.ema.buffers(), model.buffers()):
            b_ema.copy_(b)


def one_hot(labels: torch.Tensor, num_classes: int) -> torch.Tensor:
    return F.one_hot(labels, num_classes=num_classes).float()


def soft_cross_entropy(logits: torch.Tensor, target: torch.Tensor, smoothing: float = 0.0) -> torch.Tensor:
    log_probs = F.log_softmax(logits, dim=-1)
    if target.dtype in (torch.long, torch.int64):
        n_classes = logits.size(-1)
        with torch.no_grad():
            true_dist = torch.zeros_like(log_probs)
            true_dist.fill_(smoothing / (n_classes))
            true_dist.scatter_(1, target.unsqueeze(1), 1.0 - smoothing + (smoothing / (n_classes)))
        loss = -(true_dist * log_probs).sum(dim=-1)
    else:
        loss = -(target * log_probs).sum(dim=-1)
    return loss.mean()


def accuracy_from_logits(logits: torch.Tensor, targets: torch.Tensor) -> float:
    preds = logits.argmax(dim=1)
    return (preds == targets).float().mean().item()


def create_optimizer(model: nn.Module, lr: float = 3e-3, weight_decay: float = 5e-2):
    decay, no_decay = [], []
    for p in model.parameters():
        if p.dim() == 1:
            no_decay.append(p)
        else:
            decay.append(p)
    param_groups = [
        {"params": decay, "weight_decay": weight_decay},
        {"params": no_decay, "weight_decay": 0.0},
    ]
    optimizer = torch.optim.AdamW(param_groups, lr=lr, betas=(0.9, 0.99))
    return optimizer


def evaluate_model(model: nn.Module, loader, device: torch.device) -> float:
    model.eval()
    correct = 0
    total = 0
    with torch.no_grad():
        for x, y in loader:
            x = x.to(device, non_blocking=False)
            y = y.to(device, non_blocking=False)
            logits = model(x)
            preds = logits.argmax(dim=1)
            correct += (preds == y).sum().item()
            total += y.numel()
    return (correct / total) if total > 0 else 0.0


def train_model(model: nn.Module, train_loader, val_loader, device: torch.device, num_classes: int,
                epochs: int = 120, lr: float = 3e-3, weight_decay: float = 5e-2,
                mixup_alpha: float = 0.15, label_smoothing: float = 0.05, patience: int = 25):
    optimizer = create_optimizer(model, lr=lr, weight_decay=weight_decay)
    steps_per_epoch = max(1, len(train_loader))
    scheduler = torch.optim.lr_scheduler.OneCycleLR(
        optimizer,
        max_lr=lr,
        epochs=epochs,
        steps_per_epoch=steps_per_epoch,
        pct_start=0.12,
        div_factor=25.0,
        final_div_factor=100.0,
        anneal_strategy='cos'
    )

    ema = ModelEMA(model, decay=0.996)

    best_acc = -1.0
    best_state = None
    best_is_ema = True
    no_improve = 0

    for epoch in range(epochs):
        model.train()
        for x, y in train_loader:
            x = x.to(device, non_blocking=False)
            y = y.to(device, non_blocking=False)

            use_mix = mixup_alpha > 0.0
            if use_mix:
                lam = np.random.beta(mixup_alpha, mixup_alpha)
                perm = torch.randperm(x.size(0), device=device)
                x = lam * x + (1.0 - lam) * x[perm]
                y_a = one_hot(y, num_classes)
                y_b = one_hot(y[perm], num_classes)
                y_mix = lam * y_a + (1.0 - lam) * y_b
                target = y_mix
                smoothing = 0.0
            else:
                target = y
                smoothing = label_smoothing

            logits = model(x)
            loss = soft_cross_entropy(logits, target, smoothing=smoothing)

            optimizer.zero_grad(set_to_none=True)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
            optimizer.step()
            scheduler.step()
            ema.update(model)

        # Evaluate on validation
        with torch.no_grad():
            val_acc_model = evaluate_model(model, val_loader, device)
            val_acc_ema = evaluate_model(ema.ema, val_loader, device)

        if val_acc_ema >= val_acc_model:
            curr_acc = val_acc_ema
            curr_is_ema = True
        else:
            curr_acc = val_acc_model
            curr_is_ema = False

        if curr_acc > best_acc + 1e-6:
            best_acc = curr_acc
            best_is_ema = curr_is_ema
            if best_is_ema:
                best_state = copy.deepcopy(ema.ema.state_dict())
            else:
                best_state = copy.deepcopy(model.state_dict())
            no_improve = 0
        else:
            no_improve += 1
            if no_improve >= patience:
                break

    # Load best weights into EMA model for return
    if best_state is not None:
        ema.ema.load_state_dict(best_state)
    return ema.ema


class Solution:
    def _build_candidate_model(self, input_dim: int, num_classes: int, param_limit: int):
        # Try K=2 residual blocks first, then K=1
        device = torch.device("cpu")
        best_model = None
        best_params = -1
        # Search for maximum width that fits
        for K in [2, 1]:
            low, high = 128, 2048
            best_w = None
            while low <= high:
                mid = (low + high) // 2
                model = ResMLP(input_dim, num_classes, width=mid, num_blocks=K, dropout=0.10)
                pcount = count_trainable_params(model)
                if pcount <= param_limit:
                    best_w = mid
                    low = mid + 1
                else:
                    high = mid - 1
            if best_w is not None:
                model = ResMLP(input_dim, num_classes, width=best_w, num_blocks=K, dropout=0.10)
                pcount = count_trainable_params(model)
                if pcount <= param_limit and pcount > best_params:
                    best_params = pcount
                    best_model = model
        if best_model is None:
            # Fallback minimal model
            best_model = nn.Sequential(nn.Linear(input_dim, num_classes))
        return best_model

    def solve(self, train_loader, val_loader, metadata: dict = None) -> torch.nn.Module:
        set_seed(42)
        if metadata is None:
            metadata = {}
        input_dim = int(metadata.get("input_dim", 384))
        num_classes = int(metadata.get("num_classes", 128))
        param_limit = int(metadata.get("param_limit", 2_500_000))
        device_str = metadata.get("device", "cpu")
        device = torch.device(device_str if torch.cuda.is_available() and device_str.startswith("cuda") else "cpu")

        model = self._build_candidate_model(input_dim, num_classes, param_limit)
        # Ensure parameter constraint
        pcount = count_trainable_params(model)
        if pcount > param_limit:
            # Reduce width/K aggressively
            model = ResMLP(input_dim, num_classes, width=512, num_blocks=1, dropout=0.10)
            if count_trainable_params(model) > param_limit:
                model = nn.Sequential(nn.Linear(input_dim, num_classes))

        model.to(device)

        # Training hyperparameters
        epochs = 120
        # Adjust epochs based on dataset size for safety
        try:
            train_samples = int(metadata.get("train_samples", 2048))
        except Exception:
            train_samples = 2048
        if train_samples < 1500:
            epochs = 150
        elif train_samples > 3000:
            epochs = 100

        lr = 3e-3
        weight_decay = 5e-2
        mixup_alpha = 0.15
        label_smoothing = 0.05
        patience = 25

        val_loader = val_loader if val_loader is not None else train_loader

        trained_model = train_model(
            model=model,
            train_loader=train_loader,
            val_loader=val_loader,
            device=device,
            num_classes=num_classes,
            epochs=epochs,
            lr=lr,
            weight_decay=weight_decay,
            mixup_alpha=mixup_alpha,
            label_smoothing=label_smoothing,
            patience=patience,
        )
        trained_model.to(device)
        return trained_model