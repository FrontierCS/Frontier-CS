import math
import copy
import random
import torch
import torch.nn as nn
import torch.nn.functional as F


def set_seed(seed: int = 42):
    random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)


class ResidualBlock(nn.Module):
    def __init__(self, dim: int, dropout: float = 0.1):
        super().__init__()
        self.norm1 = nn.LayerNorm(dim)
        self.fc1 = nn.Linear(dim, dim)
        self.act = nn.GELU()
        self.dropout = nn.Dropout(dropout)
        self.norm2 = nn.LayerNorm(dim)
        self.fc2 = nn.Linear(dim, dim)

    def forward(self, x):
        residual = x
        out = self.norm1(x)
        out = self.fc1(out)
        out = self.act(out)
        out = self.dropout(out)
        out = self.norm2(out)
        out = self.fc2(out)
        out = self.dropout(out)
        return residual + out


class MLPNet(nn.Module):
    def __init__(self, input_dim: int, num_classes: int, width: int, blocks: int, dropout: float = 0.1):
        super().__init__()
        self.in_norm = nn.LayerNorm(input_dim)
        self.fc1 = nn.Linear(input_dim, width)
        self.act1 = nn.GELU()
        self.drop1 = nn.Dropout(dropout)

        self.norm_h1 = nn.LayerNorm(width)
        self.fc_h = nn.Linear(width, width)
        self.act_h = nn.GELU()
        self.drop_h = nn.Dropout(dropout)

        self.norm_h2 = nn.LayerNorm(width)
        self.fc2 = nn.Linear(width, 256)
        self.act2 = nn.GELU()
        self.drop2 = nn.Dropout(dropout)

        self.blocks = nn.ModuleList([ResidualBlock(256, dropout=dropout) for _ in range(blocks)])

        self.out_norm = nn.LayerNorm(256)
        self.head = nn.Linear(256, num_classes)

    def forward(self, x):
        x = self.in_norm(x)
        x = self.fc1(x)
        x = self.act1(x)
        x = self.drop1(x)

        x = self.norm_h1(x)
        x = self.fc_h(x)
        x = self.act_h(x)
        x = self.drop_h(x)

        x = self.norm_h2(x)
        x = self.fc2(x)
        x = self.act2(x)
        x = self.drop2(x)

        for blk in self.blocks:
            x = blk(x)

        x = self.out_norm(x)
        x = self.head(x)
        return x


class EMA:
    def __init__(self, model: nn.Module, decay: float = 0.999):
        self.decay = decay
        self.shadow = {}
        self.backup = {}
        for name, param in model.named_parameters():
            if param.requires_grad:
                self.shadow[name] = param.data.clone()

    @torch.no_grad()
    def update(self, model: nn.Module):
        for name, param in model.named_parameters():
            if param.requires_grad:
                assert name in self.shadow
                self.shadow[name].mul_(self.decay).add_(param.data, alpha=1.0 - self.decay)

    def apply_shadow(self, model: nn.Module):
        self.backup = {}
        for name, param in model.named_parameters():
            if param.requires_grad:
                self.backup[name] = param.data.clone()
                param.data.copy_(self.shadow[name])

    def restore(self, model: nn.Module):
        for name, param in model.named_parameters():
            if param.requires_grad and name in self.backup:
                param.data.copy_(self.backup[name])
        self.backup = {}


def count_params(model: nn.Module) -> int:
    return sum(p.numel() for p in model.parameters() if p.requires_grad)


def build_best_model(input_dim: int, num_classes: int, param_limit: int, dropout: float = 0.1):
    best_cfg = None
    best_params = -1

    # Explore number of residual blocks and width to maximize params under limit
    for blocks in range(4, -1, -1):
        # Width search range
        for width in range(640, 255, -1):
            model = MLPNet(input_dim, num_classes, width=width, blocks=blocks, dropout=dropout)
            p = count_params(model)
            if p <= param_limit and p > best_params:
                best_params = p
                best_cfg = (width, blocks)
        if best_cfg is not None:
            break

    if best_cfg is None:
        # Fall back to a minimal safe model
        best_cfg = (384, 0)

    width, blocks = best_cfg
    model = MLPNet(input_dim, num_classes, width=width, blocks=blocks, dropout=dropout)
    # Ensure strict constraint
    if count_params(model) > param_limit:
        # Decrease width until it fits
        while count_params(model) > param_limit and width > 64:
            width -= 1
            model = MLPNet(input_dim, num_classes, width=width, blocks=blocks, dropout=dropout)
    return model


def evaluate(model: nn.Module, data_loader, device: str, use_ema: bool = False, ema: EMA = None):
    model.eval()
    need_restore = False
    if use_ema and ema is not None:
        ema.apply_shadow(model)
        need_restore = True

    correct = 0
    total = 0
    with torch.no_grad():
        for inputs, targets in data_loader:
            inputs = inputs.to(device, non_blocking=False)
            targets = targets.to(device, non_blocking=False)
            outputs = model(inputs)
            preds = outputs.argmax(dim=1)
            correct += (preds == targets).sum().item()
            total += targets.numel()

    if need_restore:
        ema.restore(model)
    return correct / max(1, total)


class Solution:
    def solve(self, train_loader, val_loader, metadata: dict = None) -> torch.nn.Module:
        set_seed(42)
        if metadata is None:
            metadata = {}
        input_dim = int(metadata.get("input_dim", 384))
        num_classes = int(metadata.get("num_classes", 128))
        param_limit = int(metadata.get("param_limit", 1_000_000))
        device = str(metadata.get("device", "cpu"))

        dropout = 0.15

        model = build_best_model(input_dim, num_classes, param_limit, dropout=dropout)
        model.to(device)

        # Recheck parameter constraint
        if count_params(model) > param_limit:
            # As a last resort, build a smaller baseline
            model = MLPNet(input_dim, num_classes, width=384, blocks=0, dropout=dropout).to(device)

        optimizer = torch.optim.AdamW(model.parameters(), lr=0.003, weight_decay=0.01)
        steps_per_epoch = max(1, len(train_loader))
        target_total_steps = 8000
        epochs = max(50, min(200, target_total_steps // steps_per_epoch))

        # OneCycle schedule
        total_steps = epochs * steps_per_epoch
        scheduler = torch.optim.lr_scheduler.OneCycleLR(
            optimizer,
            max_lr=0.01,
            total_steps=total_steps,
            pct_start=0.15,
            anneal_strategy='cos',
            div_factor=10.0,
            final_div_factor=10.0
        )

        ema = EMA(model, decay=0.999)
        best_acc = 0.0
        best_state = None
        patience = 30
        no_improve = 0

        label_smoothing = 0.1
        for epoch in range(epochs):
            model.train()
            for inputs, targets in train_loader:
                inputs = inputs.to(device, non_blocking=False)
                targets = targets.to(device, non_blocking=False)

                optimizer.zero_grad(set_to_none=True)
                outputs = model(inputs)
                loss = F.cross_entropy(outputs, targets, label_smoothing=label_smoothing)
                loss.backward()
                torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=5.0)
                optimizer.step()
                scheduler.step()
                ema.update(model)

            if val_loader is not None:
                val_acc = evaluate(model, val_loader, device, use_ema=True, ema=ema)
                if val_acc > best_acc:
                    best_acc = val_acc
                    best_state = copy.deepcopy(ema.shadow)
                    no_improve = 0
                else:
                    no_improve += 1
                    if no_improve >= patience:
                        break

        if best_state is not None:
            # Load EMA best weights
            for name, param in model.named_parameters():
                if param.requires_grad and name in best_state:
                    param.data.copy_(best_state[name])
        else:
            # Apply current EMA weights if available
            ema.apply_shadow(model)

        model.eval()
        model.to("cpu")
        return model