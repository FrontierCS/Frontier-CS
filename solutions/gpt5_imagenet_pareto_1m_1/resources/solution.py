import math
import time
import random
import copy
from typing import Dict, Any

import torch
import torch.nn as nn
import torch.nn.functional as F


def set_seed(seed: int = 42):
    random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)


def count_parameters(model: nn.Module) -> int:
    return sum(p.numel() for p in model.parameters() if p.requires_grad)


class ResidualLinearBlock(nn.Module):
    def __init__(self, dim: int, dropout: float = 0.1):
        super().__init__()
        self.norm = nn.LayerNorm(dim)
        self.linear = nn.Linear(dim, dim)
        self.dropout = nn.Dropout(dropout)
        nn.init.zeros_(self.linear.weight)
        nn.init.zeros_(self.linear.bias)

    def forward(self, x):
        y = self.norm(x)
        y = F.gelu(y)
        y = self.linear(y)
        y = self.dropout(y)
        return x + y


class MLPNet(nn.Module):
    def __init__(self, input_dim: int, hidden_dim: int, num_blocks: int, num_classes: int, dropout: float = 0.1):
        super().__init__()
        self.in_norm = nn.LayerNorm(input_dim)
        self.fc_in = nn.Linear(input_dim, hidden_dim)
        self.in_drop = nn.Dropout(dropout)

        blocks = []
        for _ in range(num_blocks):
            blocks.append(ResidualLinearBlock(hidden_dim, dropout=dropout))
        self.blocks = nn.ModuleList(blocks)

        self.head_norm = nn.LayerNorm(hidden_dim)
        self.fc_out = nn.Linear(hidden_dim, num_classes)

        nn.init.xavier_uniform_(self.fc_in.weight)
        nn.init.zeros_(self.fc_in.bias)
        nn.init.xavier_uniform_(self.fc_out.weight)
        nn.init.zeros_(self.fc_out.bias)

    def forward(self, x):
        x = self.in_norm(x)
        x = self.fc_in(x)
        x = F.gelu(x)
        x = self.in_drop(x)
        for blk in self.blocks:
            x = blk(x)
        x = self.head_norm(x)
        x = F.gelu(x)
        x = self.fc_out(x)
        return x


class EMA:
    def __init__(self, model: nn.Module, decay: float = 0.995):
        self.decay = decay
        self.shadow = {}
        self.backup = {}
        for name, param in model.named_parameters():
            if param.requires_grad:
                self.shadow[name] = param.data.clone()

    def update(self, model: nn.Module):
        decay = self.decay
        for name, param in model.named_parameters():
            if param.requires_grad:
                assert name in self.shadow
                new_avg = (1.0 - decay) * param.data + decay * self.shadow[name]
                self.shadow[name] = new_avg.clone()

    def apply_shadow(self, model: nn.Module):
        self.backup = {}
        for name, param in model.named_parameters():
            if param.requires_grad:
                self.backup[name] = param.data.clone()
                param.data = self.shadow[name].clone()

    def restore(self, model: nn.Module):
        for name, param in model.named_parameters():
            if param.requires_grad and name in self.backup:
                param.data = self.backup[name].clone()
        self.backup = {}


def evaluate(model: nn.Module, loader, device: str) -> float:
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
    return correct / max(1, total)


def adjust_lr_cosine(optimizer, step: int, total_steps: int, warmup_steps: int, peak_lr: float, final_lr: float):
    if total_steps <= 0:
        lr = peak_lr
    elif step < warmup_steps:
        lr = peak_lr * float(step + 1) / float(max(1, warmup_steps))
    else:
        progress = float(step - warmup_steps) / float(max(1, total_steps - warmup_steps))
        lr = final_lr + 0.5 * (peak_lr - final_lr) * (1.0 + math.cos(math.pi * progress))
    for g in optimizer.param_groups:
        g['lr'] = lr
    return lr


class Solution:
    def solve(self, train_loader, val_loader, metadata: dict = None) -> torch.nn.Module:
        if metadata is None:
            metadata = {}
        input_dim = int(metadata.get("input_dim", 384))
        num_classes = int(metadata.get("num_classes", 128))
        param_limit = int(metadata.get("param_limit", 1_000_000))
        device = str(metadata.get("device", "cpu"))

        seed = 1337 + int(time.time()) % 1000
        set_seed(seed)

        candidates = [
            (768, 1, 0.10),
            (704, 1, 0.10),
            (640, 1, 0.10),
            (576, 1, 0.10),
            (512, 2, 0.10),
            (512, 1, 0.10),
        ]

        model = None
        chosen = None
        for hidden_dim, num_blocks, dropout in candidates:
            temp_model = MLPNet(input_dim=input_dim, hidden_dim=hidden_dim, num_blocks=num_blocks,
                                num_classes=num_classes, dropout=dropout)
            if count_parameters(temp_model) <= param_limit:
                model = temp_model
                chosen = (hidden_dim, num_blocks, dropout)
                break
        if model is None:
            # Fallback minimal model to ensure constraint
            model = MLPNet(input_dim=input_dim, hidden_dim=256, num_blocks=1, num_classes=num_classes, dropout=0.1)

        model.to(device)
        total_params = count_parameters(model)
        if total_params > param_limit:
            # As a final safety, shrink to 384 hidden with 1 block
            model = MLPNet(input_dim=input_dim, hidden_dim=384, num_blocks=1, num_classes=num_classes, dropout=0.1)
            model.to(device)

        # Training setup
        epochs = 120
        patience = 24
        label_smoothing = 0.03
        peak_lr = 4e-3
        final_lr = 4e-4
        weight_decay = 1e-2
        max_grad_norm = 2.0

        optimizer = torch.optim.AdamW(model.parameters(), lr=peak_lr, weight_decay=weight_decay, betas=(0.9, 0.95), eps=1e-8)
        criterion = nn.CrossEntropyLoss(label_smoothing=label_smoothing)

        steps_per_epoch = max(1, len(train_loader))
        total_steps = epochs * steps_per_epoch
        warmup_steps = max(10, int(0.05 * total_steps))

        ema = EMA(model, decay=0.995)

        best_val_acc = 0.0
        best_state = copy.deepcopy(model.state_dict())
        best_is_ema = False
        epochs_no_improve = 0

        global_step = 0
        for epoch in range(epochs):
            model.train()
            for xb, yb in train_loader:
                xb = xb.to(device)
                yb = yb.to(device)
                adjust_lr_cosine(optimizer, global_step, total_steps, warmup_steps, peak_lr, final_lr)

                optimizer.zero_grad(set_to_none=True)
                logits = model(xb)
                loss = criterion(logits, yb)
                loss.backward()
                if max_grad_norm is not None:
                    torch.nn.utils.clip_grad_norm_(model.parameters(), max_grad_norm)
                optimizer.step()
                ema.update(model)

                global_step += 1

            # Evaluate both model and EMA
            val_acc_raw = evaluate(model, val_loader, device)
            ema.apply_shadow(model)
            val_acc_ema = evaluate(model, val_loader, device)
            ema.restore(model)

            if val_acc_ema >= val_acc_raw:
                current_acc = val_acc_ema
                is_ema = True
            else:
                current_acc = val_acc_raw
                is_ema = False

            if current_acc > best_val_acc + 1e-6:
                best_val_acc = current_acc
                if is_ema:
                    ema.apply_shadow(model)
                    best_state = copy.deepcopy(model.state_dict())
                    ema.restore(model)
                    best_is_ema = True
                else:
                    best_state = copy.deepcopy(model.state_dict())
                    best_is_ema = False
                epochs_no_improve = 0
            else:
                epochs_no_improve += 1
                if epochs_no_improve >= patience:
                    break

        # Load best weights (EMA if best_is_ema)
        if best_is_ema:
            model.load_state_dict(best_state)
        else:
            model.load_state_dict(best_state)

        model.eval()
        model.to("cpu")
        return model
