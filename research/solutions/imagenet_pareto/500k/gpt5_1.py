import math
import copy
import torch
import torch.nn as nn
import torch.nn.functional as F


class InputNorm(nn.Module):
    def __init__(self, mean: torch.Tensor, std: torch.Tensor, eps: float = 1e-6):
        super().__init__()
        self.eps = eps
        self.register_buffer("mean", mean.view(1, -1))
        self.register_buffer("std", std.view(1, -1))

    def forward(self, x):
        return (x - self.mean) / (self.std + self.eps)


class PreNormResidualBlock(nn.Module):
    def __init__(self, dim: int, dropout: float = 0.1):
        super().__init__()
        self.ln = nn.LayerNorm(dim)
        self.fc = nn.Linear(dim, dim)
        self.act = nn.GELU()
        self.drop = nn.Dropout(dropout)

    def forward(self, x):
        y = self.ln(x)
        y = self.act(y)
        y = self.drop(y)
        y = self.fc(y)
        return x + y


class ResidualMLP(nn.Module):
    def __init__(self, input_dim: int, num_classes: int, mean: torch.Tensor, std: torch.Tensor,
                 num_blocks: int = 3, dropout: float = 0.1, final_norm: bool = True):
        super().__init__()
        self.norm = InputNorm(mean, std)
        self.blocks = nn.Sequential(*[PreNormResidualBlock(input_dim, dropout=dropout) for _ in range(num_blocks)])
        self.final_norm = nn.LayerNorm(input_dim) if final_norm else nn.Identity()
        self.head_drop = nn.Dropout(dropout)
        self.head = nn.Linear(input_dim, num_classes)

    def forward(self, x):
        x = self.norm(x)
        x = self.blocks(x)
        x = self.final_norm(x)
        x = self.head_drop(x)
        return self.head(x)


class EMA:
    def __init__(self, model: nn.Module, decay: float = 0.995):
        self.decay = decay
        self.shadow = [p.detach().clone() for p in model.parameters() if p.requires_grad]
        self.backup = None

    @torch.no_grad()
    def update(self, model: nn.Module):
        idx = 0
        for p in model.parameters():
            if p.requires_grad:
                self.shadow[idx].mul_(self.decay).add_(p.detach(), alpha=1.0 - self.decay)
                idx += 1

    @torch.no_grad()
    def store(self, model: nn.Module):
        self.backup = [p.detach().clone() for p in model.parameters() if p.requires_grad]

    @torch.no_grad()
    def copy_to(self, model: nn.Module):
        idx = 0
        for p in model.parameters():
            if p.requires_grad:
                p.data.copy_(self.shadow[idx].data)
                idx += 1

    @torch.no_grad()
    def restore(self, model: nn.Module):
        if self.backup is None:
            return
        idx = 0
        for p in model.parameters():
            if p.requires_grad:
                p.data.copy_(self.backup[idx].data)
                idx += 1
        self.backup = None


def count_trainable_parameters(model: nn.Module) -> int:
    return sum(p.numel() for p in model.parameters() if p.requires_grad)


def compute_loader_stats(loader, dim: int, device: str = "cpu"):
    total = 0
    sum_x = torch.zeros(dim, dtype=torch.float64)
    sum_x2 = torch.zeros(dim, dtype=torch.float64)
    with torch.no_grad():
        for xb, _ in loader:
            xb = xb.to("cpu", dtype=torch.float64)
            total += xb.shape[0]
            sum_x += xb.sum(dim=0)
            sum_x2 += (xb * xb).sum(dim=0)
    mean = (sum_x / max(total, 1)).to(torch.float32)
    var = (sum_x2 / max(total, 1)) - mean.to(torch.float64) ** 2
    var = var.clamp_min(0.0).to(torch.float32)
    std = torch.sqrt(var + 1e-6)
    return mean, std


def evaluate_accuracy(model: nn.Module, loader, device: str = "cpu"):
    model.eval()
    correct = 0
    total = 0
    with torch.no_grad():
        for xb, yb in loader:
            xb = xb.to(device)
            yb = yb.to(device)
            logits = model(xb)
            preds = logits.argmax(dim=1)
            correct += (preds == yb).sum().item()
            total += yb.numel()
    return correct / max(total, 1)


class Solution:
    def solve(self, train_loader, val_loader, metadata: dict = None) -> torch.nn.Module:
        if metadata is None:
            metadata = {}
        device = metadata.get("device", "cpu")
        input_dim = int(metadata.get("input_dim", 384))
        num_classes = int(metadata.get("num_classes", 128))
        param_limit = int(metadata.get("param_limit", 500000))

        torch.manual_seed(42)

        mean, std = compute_loader_stats(train_loader, input_dim, device=device)

        # Build model respecting parameter limit; start with 3 residual blocks
        num_blocks = 3
        dropout = 0.1
        final_norm = True

        model = ResidualMLP(input_dim, num_classes, mean, std, num_blocks=num_blocks, dropout=dropout, final_norm=final_norm)
        params = count_trainable_parameters(model)
        if params > param_limit:
            # Reduce blocks until within limit
            for nb in range(2, 0, -1):
                model = ResidualMLP(input_dim, num_classes, mean, std, num_blocks=nb, dropout=dropout, final_norm=final_norm)
                params = count_trainable_parameters(model)
                if params <= param_limit:
                    break
        # As an extra safeguard, if still over, reduce final_norm or dropout-dependent parts (though dropout has no params)
        if count_trainable_parameters(model) > param_limit:
            model = ResidualMLP(input_dim, num_classes, mean, std, num_blocks=1, dropout=dropout, final_norm=False)
        assert count_trainable_parameters(model) <= param_limit

        model.to(device)

        # Optimizer and loss
        base_lr = 3e-3
        min_lr = base_lr * 0.05
        epochs = 200
        warmup_epochs = 10
        weight_decay = 1e-4
        label_smoothing = 0.05

        optimizer = torch.optim.AdamW(model.parameters(), lr=base_lr, weight_decay=weight_decay)
        criterion = nn.CrossEntropyLoss(label_smoothing=label_smoothing)
        ema = EMA(model, decay=0.995)

        def lr_for_epoch(e):
            if e < warmup_epochs:
                return base_lr * float(e + 1) / float(warmup_epochs)
            t = (e - warmup_epochs) / max(1, (epochs - warmup_epochs))
            cos = 0.5 * (1.0 + math.cos(math.pi * t))
            return min_lr + (base_lr - min_lr) * cos

        best_state = None
        best_val_acc = -1.0

        for epoch in range(epochs):
            for g in optimizer.param_groups:
                g["lr"] = lr_for_epoch(epoch)

            model.train()
            for xb, yb in train_loader:
                xb = xb.to(device)
                yb = yb.to(device)

                optimizer.zero_grad(set_to_none=True)
                logits = model(xb)
                loss = criterion(logits, yb)
                loss.backward()
                nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
                optimizer.step()
                ema.update(model)

            if val_loader is not None:
                ema.store(model)
                ema.copy_to(model)
                val_acc = evaluate_accuracy(model, val_loader, device=device)
                if val_acc > best_val_acc:
                    best_val_acc = val_acc
                    best_state = copy.deepcopy({k: v.detach().cpu() for k, v in model.state_dict().items()})
                ema.restore(model)

        # Load best EMA weights if we have them, else final EMA
        if best_state is not None:
            model.load_state_dict(best_state)
            model.to(device)
        else:
            ema.copy_to(model)

        model.eval()
        return model