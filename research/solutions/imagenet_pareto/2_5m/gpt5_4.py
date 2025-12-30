import math
import random
import copy
import time
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F


def set_seed(seed: int = 1337):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)


def count_trainable_params(model: nn.Module) -> int:
    return sum(p.numel() for p in model.parameters() if p.requires_grad)


class LabelSmoothingCrossEntropy(nn.Module):
    def __init__(self, smoothing: float = 0.1):
        super().__init__()
        self.smoothing = smoothing

    def forward(self, logits, target):
        num_classes = logits.size(-1)
        log_probs = F.log_softmax(logits, dim=-1)
        with torch.no_grad():
            true_dist = torch.zeros_like(log_probs)
            true_dist.fill_(self.smoothing / (num_classes - 1))
            true_dist.scatter_(1, target.unsqueeze(1), 1.0 - self.smoothing)
        return torch.mean(torch.sum(-true_dist * log_probs, dim=1))


class ResBlock(nn.Module):
    def __init__(self, dim: int, dropout: float = 0.1, activation: str = "gelu", res_scale: float = 1.0):
        super().__init__()
        self.ln1 = nn.LayerNorm(dim)
        self.fc1 = nn.Linear(dim, dim)
        self.ln2 = nn.LayerNorm(dim)
        self.fc2 = nn.Linear(dim, dim)
        self.dropout = nn.Dropout(dropout)
        self.res_scale = res_scale
        if activation == "gelu":
            self.act = nn.GELU()
        elif activation == "silu":
            self.act = nn.SiLU()
        else:
            self.act = nn.ReLU(inplace=True)

    def forward(self, x):
        out = self.fc1(self.act(self.ln1(x)))
        out = self.dropout(out)
        out = self.fc2(self.act(self.ln2(out)))
        out = self.dropout(out)
        return x + out * self.res_scale


class MLPResNet(nn.Module):
    def __init__(self, input_dim: int, num_classes: int, width: int, blocks: int, dropout: float = 0.1, activation: str = "gelu"):
        super().__init__()
        self.inp = nn.Linear(input_dim, width)
        self.blocks = nn.ModuleList([ResBlock(width, dropout=dropout, activation=activation, res_scale=1.0) for _ in range(blocks)])
        self.pre_out_ln = nn.LayerNorm(width)
        self.dropout = nn.Dropout(dropout)
        self.out = nn.Linear(width, num_classes)

        self.reset_parameters()

    def reset_parameters(self):
        for m in self.modules():
            if isinstance(m, nn.Linear):
                nn.init.kaiming_normal_(m.weight, nonlinearity='relu')
                if m.bias is not None:
                    nn.init.zeros_(m.bias)
            elif isinstance(m, nn.LayerNorm):
                nn.init.ones_(m.weight)
                nn.init.zeros_(m.bias)

    def forward(self, x):
        x = self.inp(x)
        for blk in self.blocks:
            x = blk(x)
        x = self.pre_out_ln(x)
        x = self.dropout(x)
        x = self.out(x)
        return x


def analytic_max_width(input_dim: int, num_classes: int, param_limit: int, blocks: int) -> int:
    # Param formula:
    # total = 2B*d^2 + d*(input_dim + num_classes + (6B + 3)) + num_classes
    # Solve 2B*d^2 + S*d + C <= 0, where S = input_dim + num_classes + (6B + 3), C = num_classes - param_limit
    B = blocks
    S = input_dim + num_classes + (6 * B + 3)
    C = num_classes - param_limit
    a = 2 * B
    b = S
    c = C
    disc = b * b - 4 * a * c
    if disc <= 0:
        return 0
    sqrt_disc = int(math.sqrt(disc))
    d = int(( -b + sqrt_disc ) // (2 * a))
    return max(d, 1)


def param_formula(input_dim: int, num_classes: int, d: int, blocks: int) -> int:
    return 2 * blocks * d * d + d * (input_dim + num_classes + (6 * blocks + 3)) + num_classes


def best_architecture(input_dim: int, num_classes: int, param_limit: int):
    # Search blocks in a reasonable range and pick width to maximize parameter utilization under the limit
    best = None
    for B in range(5, 1, -1):  # Try deeper first
        d_est = analytic_max_width(input_dim, num_classes, param_limit, B)
        d_est = min(d_est, 2048)
        if d_est <= 0:
            continue
        # Adjust downward until within limit using the exact instantiated param count formula as a guide
        d = d_est
        # Provide a margin to safely handle counting differences (though our formula matches the model)
        while d > 1 and param_formula(input_dim, num_classes, d, B) > param_limit:
            d -= 1
        if d <= 1:
            continue
        params_est = param_formula(input_dim, num_classes, d, B)
        if params_est > param_limit:
            continue
        if best is None or params_est > best[2]:
            best = (B, d, params_est)
    if best is None:
        # Fallback to a tiny network
        B, d = 2, 128
        return B, d
    return best[0], best[1]


def get_param_groups(model: nn.Module, weight_decay: float):
    decay, no_decay = [], []
    for name, p in model.named_parameters():
        if not p.requires_grad:
            continue
        if p.ndim >= 2:
            decay.append(p)
        else:
            no_decay.append(p)
    return [
        {'params': decay, 'weight_decay': weight_decay},
        {'params': no_decay, 'weight_decay': 0.0},
    ]


def evaluate(model: nn.Module, loader, device):
    model.eval()
    correct = 0
    total = 0
    with torch.no_grad():
        for xb, yb in loader:
            xb = xb.to(device=device, dtype=torch.float32, non_blocking=False)
            yb = yb.to(device=device, dtype=torch.long, non_blocking=False)
            logits = model(xb)
            preds = logits.argmax(dim=1)
            correct += (preds == yb).sum().item()
            total += yb.numel()
    if total == 0:
        return 0.0
    return correct / total


class Solution:
    def solve(self, train_loader, val_loader, metadata: dict = None) -> torch.nn.Module:
        set_seed(42)

        if metadata is None:
            metadata = {}
        input_dim = int(metadata.get("input_dim", 384))
        num_classes = int(metadata.get("num_classes", 128))
        param_limit = int(metadata.get("param_limit", 2_500_000))
        device = torch.device(metadata.get("device", "cpu"))

        # Choose architecture under parameter limit
        blocks, width = best_architecture(input_dim, num_classes, param_limit)

        # Dropout based on depth
        if blocks >= 4:
            dropout = 0.2
        elif blocks == 3:
            dropout = 0.15
        else:
            dropout = 0.1

        model = MLPResNet(input_dim=input_dim, num_classes=num_classes, width=width, blocks=blocks, dropout=dropout, activation="gelu")
        # Ensure parameter constraint
        actual_params = count_trainable_params(model)
        while actual_params > param_limit and width > 8:
            width -= 1
            model = MLPResNet(input_dim=input_dim, num_classes=num_classes, width=width, blocks=blocks, dropout=dropout, activation="gelu")
            actual_params = count_trainable_params(model)

        model.to(device)

        # Optimizer and scheduler
        base_lr = 0.003 if width >= 512 else 0.004
        weight_decay = 0.02 if width >= 512 else 0.01

        param_groups = get_param_groups(model, weight_decay=weight_decay)
        optimizer = torch.optim.AdamW(param_groups, lr=base_lr, betas=(0.9, 0.999), eps=1e-8)

        # Training settings
        total_epochs = 200
        steps_per_epoch = max(1, len(train_loader))
        use_onecycle = True if steps_per_epoch > 1 else False
        if use_onecycle:
            scheduler = torch.optim.lr_scheduler.OneCycleLR(
                optimizer,
                max_lr=base_lr,
                epochs=total_epochs,
                steps_per_epoch=steps_per_epoch,
                pct_start=0.1,
                div_factor=10.0,
                final_div_factor=100.0,
                anneal_strategy='cos'
            )
        else:
            scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=total_epochs, eta_min=base_lr * 0.05)

        criterion = LabelSmoothingCrossEntropy(smoothing=0.1)

        # Early stopping
        best_val_acc = -1.0
        best_state = copy.deepcopy(model.state_dict())
        patience = 40
        epochs_no_improve = 0

        # Training loop
        for epoch in range(total_epochs):
            model.train()
            for xb, yb in train_loader:
                xb = xb.to(device=device, dtype=torch.float32, non_blocking=False)
                yb = yb.to(device=device, dtype=torch.long, non_blocking=False)

                optimizer.zero_grad(set_to_none=True)
                logits = model(xb)
                loss = criterion(logits, yb)
                loss.backward()
                torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
                optimizer.step()
                if use_onecycle:
                    scheduler.step()

            if not use_onecycle:
                scheduler.step()

            # Validation
            val_acc = evaluate(model, val_loader, device) if val_loader is not None else 0.0
            if val_acc > best_val_acc:
                best_val_acc = val_acc
                best_state = copy.deepcopy(model.state_dict())
                epochs_no_improve = 0
            else:
                epochs_no_improve += 1

            if epochs_no_improve >= patience:
                break

        # Load best model
        model.load_state_dict(best_state)
        model.eval()
        return model