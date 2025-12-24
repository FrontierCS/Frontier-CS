import math
import copy
import torch
import torch.nn as nn
import torch.nn.functional as F


def count_parameters(model: nn.Module) -> int:
    return sum(p.numel() for p in model.parameters() if p.requires_grad)


def compute_dataset_stats(loader, input_dim: int, device: torch.device):
    total = 0
    mean = torch.zeros(input_dim, dtype=torch.float64)
    sq_mean = torch.zeros(input_dim, dtype=torch.float64)
    for x, _ in loader:
        x = x.to('cpu', dtype=torch.float64)
        total += x.shape[0]
        mean += x.sum(dim=0)
        sq_mean += (x * x).sum(dim=0)
    mean = mean / total
    var = (sq_mean / total) - mean * mean
    std = torch.sqrt(torch.clamp(var, min=1e-8))
    mean = mean.to(torch.float32).to(device)
    std = std.to(torch.float32).to(device)
    return mean, std


class Standardize(nn.Module):
    def __init__(self, mean: torch.Tensor, std: torch.Tensor):
        super().__init__()
        self.register_buffer('mean', mean.clone().detach())
        self.register_buffer('std', std.clone().detach())

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return (x - self.mean) / self.std


class BottleneckMLPBlock(nn.Module):
    def __init__(self, dim: int, bottleneck_dim: int, dropout: float = 0.1):
        super().__init__()
        self.norm = nn.LayerNorm(dim)
        self.fc1 = nn.Linear(dim, bottleneck_dim)
        self.act = nn.GELU()
        self.drop = nn.Dropout(dropout)
        self.fc2 = nn.Linear(bottleneck_dim, dim)
        self.drop2 = nn.Dropout(dropout)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        y = self.norm(x)
        y = self.fc1(y)
        y = self.act(y)
        y = self.drop(y)
        y = self.fc2(y)
        y = self.drop2(y)
        return x + y


class BottleneckMLPNet(nn.Module):
    def __init__(self, input_dim: int, num_classes: int, mean: torch.Tensor, std: torch.Tensor,
                 hidden_dim: int, num_blocks: int, bottleneck_dim: int, dropout: float = 0.1):
        super().__init__()
        self.std = Standardize(mean, std)
        self.input_ln = nn.LayerNorm(input_dim)
        self.fc_in = nn.Linear(input_dim, hidden_dim)
        self.act_in = nn.GELU()
        self.drop_in = nn.Dropout(dropout)
        self.blocks = nn.ModuleList([
            BottleneckMLPBlock(hidden_dim, bottleneck_dim, dropout=dropout) for _ in range(num_blocks)
        ])
        self.final_ln = nn.LayerNorm(hidden_dim)
        self.head = nn.Linear(hidden_dim, num_classes)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = x.view(x.shape[0], -1)
        x = self.std(x)
        x = self.input_ln(x)
        x = self.fc_in(x)
        x = self.act_in(x)
        x = self.drop_in(x)
        for blk in self.blocks:
            x = blk(x)
        x = self.final_ln(x)
        out = self.head(x)
        return out


class EMA:
    def __init__(self, model: nn.Module, decay: float = 0.999):
        self.decay = decay
        self.shadow = {}
        for name, param in model.named_parameters():
            if param.requires_grad:
                self.shadow[name] = param.data.clone()

    @torch.no_grad()
    def update(self, model: nn.Module):
        for name, param in model.named_parameters():
            if param.requires_grad:
                self.shadow[name].mul_(self.decay).add_(param.data, alpha=1.0 - self.decay)

    @torch.no_grad()
    def copy_to(self, model: nn.Module):
        for name, param in model.named_parameters():
            if param.requires_grad:
                param.data.copy_(self.shadow[name])

    @torch.no_grad()
    def export_state(self):
        return {k: v.clone() for k, v in self.shadow.items()}


def param_count_formula(input_dim: int, num_classes: int, hidden_dim: int, num_blocks: int, bottleneck_dim: int) -> int:
    # Standardize has no trainable parameters
    # input LayerNorm: weight + bias
    count = 2 * input_dim
    # fc_in: weights + bias
    count += input_dim * hidden_dim + hidden_dim
    # blocks
    for _ in range(num_blocks):
        # LayerNorm
        count += 2 * hidden_dim
        # fc1 and fc2 with biases
        count += hidden_dim * bottleneck_dim + bottleneck_dim
        count += bottleneck_dim * hidden_dim + hidden_dim
    # final LayerNorm
    count += 2 * hidden_dim
    # head
    count += hidden_dim * num_classes + num_classes
    return count


def select_config_within_budget(input_dim: int, num_classes: int, param_limit: int):
    best = None
    best_params = -1
    # candidate hidden dims descending
    hidden_candidates = [1152, 1088, 1024, 960, 928, 896, 864, 832, 800, 768, 736, 704, 672, 640, 608, 576]
    # candidate bottleneck ratios; prefer 4 -> 1/4 expansion
    ratio_candidates = [4, 3, 5]  # try 4 first, then 3, then 5
    # candidate blocks range high to low
    for h in hidden_candidates:
        for r in ratio_candidates:
            m = max(64, (h // r))
            # Search blocks with a generous upper bound
            # Upper bound estimation
            max_blocks_est = max(2, int((param_limit - (input_dim + num_classes + 512) * h) / max(1, (h * h // 2))))
            # Ensure some reasonable search range
            for b in range(min(20, max_blocks_est + 6), 1, -1):
                p = param_count_formula(input_dim, num_classes, h, b, m)
                if p <= param_limit and p > best_params:
                    best = (h, b, m)
                    best_params = p
            # Early exit if we already very close to the limit
            if best is not None and (param_limit - best_params) < 20000:
                return best, best_params
    if best is None:
        # Fallback to safe small config
        h, b, m = 512, 6, 128
        p = param_count_formula(input_dim, num_classes, h, b, m)
        return (h, b, m), p
    return best, best_params


def evaluate_accuracy(model: nn.Module, loader, device: torch.device) -> float:
    model.eval()
    correct = 0
    total = 0
    with torch.no_grad():
        for x, y in loader:
            x = x.to(device, dtype=torch.float32)
            y = y.to(device, dtype=torch.long)
            logits = model(x)
            preds = logits.argmax(dim=1)
            correct += (preds == y).sum().item()
            total += y.numel()
    return (correct / total) if total > 0 else 0.0


class Solution:
    def solve(self, train_loader, val_loader, metadata: dict = None) -> torch.nn.Module:
        if metadata is None:
            metadata = {}
        device = torch.device(metadata.get("device", "cpu"))
        input_dim = int(metadata.get("input_dim", 384))
        num_classes = int(metadata.get("num_classes", 128))
        param_limit = int(metadata.get("param_limit", 5_000_000))

        mean, std = compute_dataset_stats(train_loader, input_dim, device)

        # Select architecture under parameter limit
        (hidden_dim, num_blocks, bottleneck_dim), est_params = select_config_within_budget(input_dim, num_classes, param_limit)

        model = BottleneckMLPNet(
            input_dim=input_dim,
            num_classes=num_classes,
            mean=mean,
            std=std,
            hidden_dim=hidden_dim,
            num_blocks=num_blocks,
            bottleneck_dim=bottleneck_dim,
            dropout=0.1
        ).to(device)

        # Ensure parameter limit not exceeded
        actual_params = count_parameters(model)
        if actual_params > param_limit:
            # Reduce blocks until under limit
            while num_blocks > 2 and actual_params > param_limit:
                num_blocks -= 1
                model = BottleneckMLPNet(
                    input_dim=input_dim,
                    num_classes=num_classes,
                    mean=mean,
                    std=std,
                    hidden_dim=hidden_dim,
                    num_blocks=num_blocks,
                    bottleneck_dim=bottleneck_dim,
                    dropout=0.1
                ).to(device)
                actual_params = count_parameters(model)
            # If still over, reduce hidden_dim
            while hidden_dim > 256 and actual_params > param_limit:
                hidden_dim -= 32
                bottleneck_dim = max(64, hidden_dim // 4)
                model = BottleneckMLPNet(
                    input_dim=input_dim,
                    num_classes=num_classes,
                    mean=mean,
                    std=std,
                    hidden_dim=hidden_dim,
                    num_blocks=num_blocks,
                    bottleneck_dim=bottleneck_dim,
                    dropout=0.1
                ).to(device)
                actual_params = count_parameters(model)

        # Training hyperparameters
        total_epochs = 220
        warmup_epochs = 8
        batch_per_epoch = max(1, len(getattr(train_loader, 'dataset', [])) // max(1, getattr(train_loader, 'batch_size', 64)))
        lr = 2.0e-3
        weight_decay = 0.02
        label_smoothing = 0.05
        grad_clip = 1.0

        optimizer = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=weight_decay, betas=(0.9, 0.99))

        def lr_lambda(epoch):
            if epoch < warmup_epochs:
                return float(epoch + 1) / float(max(1, warmup_epochs))
            t = (epoch - warmup_epochs) / float(max(1, total_epochs - warmup_epochs))
            return 0.5 * (1.0 + math.cos(math.pi * t))

        scheduler = torch.optim.lr_scheduler.LambdaLR(optimizer, lr_lambda=lr_lambda)

        ema = EMA(model, decay=0.999)

        best_val_acc = -1.0
        best_ema_shadow = ema.export_state()
        patience = 50
        patience_counter = 0

        for epoch in range(total_epochs):
            model.train()
            for xb, yb in train_loader:
                xb = xb.to(device, dtype=torch.float32)
                yb = yb.to(device, dtype=torch.long)
                optimizer.zero_grad(set_to_none=True)
                logits = model(xb)
                loss = F.cross_entropy(logits, yb, label_smoothing=label_smoothing)
                loss.backward()
                if grad_clip is not None and grad_clip > 0:
                    torch.nn.utils.clip_grad_norm_(model.parameters(), grad_clip)
                optimizer.step()
                ema.update(model)
            scheduler.step()

            # Evaluate with EMA weights
            ema.copy_to(model)
            val_acc = evaluate_accuracy(model, val_loader, device) if val_loader is not None else evaluate_accuracy(model, train_loader, device)
            # Restore current (non-EMA) weights by reloading from optimizer param tensors updated this epoch
            # We will reload from ema.shadow via previous step at next epoch's update anyway; no need to restore exact pre-EMA weights
            # Track best
            if val_acc > best_val_acc:
                best_val_acc = val_acc
                best_ema_shadow = ema.export_state()
                patience_counter = 0
            else:
                patience_counter += 1

            if patience_counter >= patience:
                break

        # Load best EMA weights into model
        with torch.no_grad():
            for name, param in model.named_parameters():
                if param.requires_grad and name in best_ema_shadow:
                    param.data.copy_(best_ema_shadow[name])

        model.eval()
        return model
