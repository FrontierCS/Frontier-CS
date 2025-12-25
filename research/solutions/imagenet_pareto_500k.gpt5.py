import math
import random
import copy
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.optim import AdamW


def set_seed(seed: int = 42):
    random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)


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
        return x / keep_prob * random_tensor


class BottleneckResBlock(nn.Module):
    def __init__(self, dim: int, hidden: int, dropout: float = 0.1, droppath: float = 0.0):
        super().__init__()
        self.norm = nn.LayerNorm(dim)
        self.fc1 = nn.Linear(dim, hidden)
        self.act = nn.SiLU()
        self.drop1 = nn.Dropout(dropout)
        self.fc2 = nn.Linear(hidden, dim)
        self.drop2 = nn.Dropout(dropout)
        self.drop_path = DropPath(droppath)

    def forward(self, x):
        y = self.norm(x)
        y = self.fc1(y)
        y = self.act(y)
        y = self.drop1(y)
        y = self.fc2(y)
        y = self.drop2(y)
        return x + self.drop_path(y)


class MLPResNetClassifier(nn.Module):
    def __init__(self, input_dim: int, num_classes: int, bottleneck: int = 192, num_blocks: int = 3,
                 dropout: float = 0.1, droppath: float = 0.1, final_norm: bool = True):
        super().__init__()
        self.dim = input_dim
        blocks = []
        for i in range(num_blocks):
            dp = droppath * (i + 1) / max(1, num_blocks)
            blocks.append(BottleneckResBlock(input_dim, bottleneck, dropout, dp))
        self.blocks = nn.Sequential(*blocks)
        self.final_norm = nn.LayerNorm(input_dim) if final_norm else None
        self.head = nn.Linear(input_dim, num_classes)

    def forward(self, x):
        x = self.blocks(x)
        if self.final_norm is not None:
            x = self.final_norm(x)
        return self.head(x)


class ModelEMA:
    def __init__(self, model: nn.Module, decay: float = 0.999):
        self.ema = copy.deepcopy(model).eval()
        for p in self.ema.parameters():
            p.requires_grad_(False)
        self.decay = decay

    @torch.no_grad()
    def update(self, model: nn.Module):
        d = self.decay
        msd = model.state_dict()
        for k, ema_v in self.ema.state_dict().items():
            model_v = msd[k]
            if ema_v.dtype.is_floating_point:
                ema_v.mul_(d).add_(model_v, alpha=1.0 - d)
            else:
                ema_v.copy_(model_v)

    def copy_to(self, model: nn.Module):
        model.load_state_dict(self.ema.state_dict(), strict=True)


def count_parameters(model: nn.Module) -> int:
    return sum(p.numel() for p in model.parameters() if p.requires_grad)


def mixup_data(x, y, num_classes, alpha=0.4):
    if alpha <= 0.0:
        return x, F.one_hot(y, num_classes=num_classes).float(), 1.0
    lam = torch.distributions.Beta(alpha, alpha).sample().item()
    batch_size = x.size(0)
    index = torch.randperm(batch_size, device=x.device)
    mixed_x = lam * x + (1 - lam) * x[index]
    y_a = F.one_hot(y, num_classes=num_classes).float()
    y_b = y_a[index]
    mixed_y = lam * y_a + (1 - lam) * y_b
    return mixed_x, mixed_y, lam


def soft_cross_entropy(logits, soft_targets):
    log_prob = F.log_softmax(logits, dim=1)
    loss = -(soft_targets * log_prob).sum(dim=1)
    return loss.mean()


def label_smoothing_targets(y, num_classes, smoothing=0.1):
    with torch.no_grad():
        confidence = 1.0 - smoothing
        smoothing_value = smoothing / (num_classes - 1)
        y_onehot = torch.full((y.size(0), num_classes), smoothing_value, device=y.device)
        y_onehot.scatter_(1, y.view(-1, 1), confidence)
    return y_onehot


class WarmupCosine:
    def __init__(self, optimizer, warmup_steps, total_steps, base_lr, min_lr=1e-5):
        self.optimizer = optimizer
        self.warmup_steps = max(1, warmup_steps)
        self.total_steps = max(self.warmup_steps + 1, total_steps)
        self.base_lr = base_lr
        self.min_lr = min_lr
        self.step_num = 0

    def step(self):
        self.step_num += 1
        if self.step_num <= self.warmup_steps:
            lr = self.base_lr * self.step_num / self.warmup_steps
        else:
            t = (self.step_num - self.warmup_steps) / max(1, self.total_steps - self.warmup_steps)
            lr = self.min_lr + 0.5 * (self.base_lr - self.min_lr) * (1 + math.cos(math.pi * t))
        for pg in self.optimizer.param_groups:
            pg['lr'] = lr

    def get_lr(self):
        return self.optimizer.param_groups[0]['lr']


def evaluate_accuracy(model: nn.Module, data_loader, device: torch.device):
    model.eval()
    correct = 0
    total = 0
    with torch.no_grad():
        for xb, yb in data_loader:
            xb = xb.to(device, non_blocking=False)
            yb = yb.to(device, non_blocking=False)
            logits = model(xb)
            preds = logits.argmax(dim=1)
            correct += (preds == yb).sum().item()
            total += yb.numel()
    return correct / max(1, total)


def build_best_model(input_dim, num_classes, param_limit):
    # Try preferred high-capacity configuration first
    configs = []
    # (num_blocks, bottleneck_ratio, dropout, droppath, final_norm)
    configs.append((3, 0.5, 0.1, 0.1, True))
    configs.append((3, 0.5, 0.2, 0.1, True))
    configs.append((2, 2.0 / 3.0, 0.1, 0.1, True))
    configs.append((3, 0.4, 0.1, 0.1, True))
    configs.append((4, 0.25, 0.1, 0.1, True))
    configs.append((2, 0.5, 0.1, 0.1, True))
    configs.append((2, 0.33, 0.1, 0.1, True))
    for nb, ratio, dropout, droppath, fn in configs:
        bottleneck = max(8, int(input_dim * ratio))
        model = MLPResNetClassifier(input_dim, num_classes, bottleneck=bottleneck, num_blocks=nb,
                                    dropout=dropout, droppath=droppath, final_norm=fn)
        if count_parameters(model) <= param_limit:
            return model
    # Fallback simple MLP if above did not fit
    hidden = min(input_dim, max(64, param_limit // (input_dim + num_classes + 8)))
    model = nn.Sequential(
        nn.Linear(input_dim, hidden),
        nn.GELU(),
        nn.Dropout(0.1),
        nn.Linear(hidden, num_classes),
    )
    # As final safety, drop hidden until param limit satisfied
    while count_parameters(model) > param_limit and hidden > 32:
        hidden = hidden // 2
        model = nn.Sequential(
            nn.Linear(input_dim, hidden),
            nn.GELU(),
            nn.Dropout(0.1),
            nn.Linear(hidden, num_classes),
        )
    return model


class Solution:
    def solve(self, train_loader, val_loader, metadata: dict = None) -> torch.nn.Module:
        set_seed(1234)
        device = torch.device(metadata.get("device", "cpu") if metadata else "cpu")
        num_classes = int(metadata.get("num_classes", 128))
        input_dim = int(metadata.get("input_dim", 384))
        param_limit = int(metadata.get("param_limit", 500000))

        model = build_best_model(input_dim, num_classes, param_limit)
        assert count_parameters(model) <= param_limit

        model.to(device)
        ema = ModelEMA(model, decay=0.997)

        base_lr = 3e-3
        weight_decay = 6e-4
        optimizer = AdamW(model.parameters(), lr=base_lr, weight_decay=weight_decay, betas=(0.9, 0.999))

        epochs = 140
        steps_per_epoch = max(1, len(train_loader))
        total_steps = epochs * steps_per_epoch
        warmup_steps = max(5 * steps_per_epoch, int(0.05 * total_steps))
        scheduler = WarmupCosine(optimizer, warmup_steps=warmup_steps, total_steps=total_steps, base_lr=base_lr, min_lr=5e-5)

        use_mixup = True
        mixup_alpha = 0.4
        mixup_prob = 0.6
        label_smoothing = 0.1
        max_grad_norm = 1.0

        best_acc = 0.0
        best_state = copy.deepcopy(model.state_dict())
        best_ema_state = copy.deepcopy(ema.ema.state_dict())

        patience = 35
        wait = 0

        step_count = 0
        for epoch in range(epochs):
            model.train()
            for xb, yb in train_loader:
                xb = xb.to(device, non_blocking=False)
                yb = yb.to(device, non_blocking=False)

                apply_mix = use_mixup and (random.random() < mixup_prob)
                if apply_mix:
                    mx, my, _ = mixup_data(xb, yb, num_classes=num_classes, alpha=mixup_alpha)
                    logits = model(mx)
                    loss = soft_cross_entropy(logits, my)
                else:
                    logits = model(xb)
                    if label_smoothing > 0.0:
                        targets = label_smoothing_targets(yb, num_classes, smoothing=label_smoothing)
                        loss = soft_cross_entropy(logits, targets)
                    else:
                        loss = F.cross_entropy(logits, yb)

                optimizer.zero_grad(set_to_none=True)
                loss.backward()
                if max_grad_norm is not None and max_grad_norm > 0.0:
                    torch.nn.utils.clip_grad_norm_(model.parameters(), max_grad_norm)
                optimizer.step()
                ema.update(model)
                scheduler.step()
                step_count += 1

            # Evaluate using EMA weights
            ema_model = ema.ema
            acc = evaluate_accuracy(ema_model, val_loader, device)

            if acc > best_acc:
                best_acc = acc
                best_state = copy.deepcopy(model.state_dict())
                best_ema_state = copy.deepcopy(ema_model.state_dict())
                wait = 0
            else:
                wait += 1

            if wait >= patience:
                break

        # Load best EMA weights into model for evaluation
        model.load_state_dict(best_state)
        ema.ema.load_state_dict(best_ema_state)
        ema.copy_to(model)

        model.eval()
        return model
