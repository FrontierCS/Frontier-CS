import math
import os
import copy
import random
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F


def set_seed(seed: int = 42):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)


def count_parameters(model: nn.Module) -> int:
    return sum(p.numel() for p in model.parameters() if p.requires_grad)


class ResidualMLPBlock(nn.Module):
    def __init__(self, dim: int, hidden: int = None, dropout: float = 0.1):
        super().__init__()
        self.ln = nn.LayerNorm(dim)
        self.hidden = hidden
        self.act = nn.SiLU()
        self.dropout = nn.Dropout(dropout)
        if hidden is None or hidden == dim:
            self.fc = nn.Linear(dim, dim)
            self.fc2 = None
        else:
            self.fc = nn.Linear(dim, hidden)
            self.fc2 = nn.Linear(hidden, dim)

    def forward(self, x):
        y = self.ln(x)
        y = self.act(y)
        if self.fc2 is None:
            y = self.fc(y)
        else:
            y = self.fc(y)
            y = self.act(y)
            y = self.fc2(y)
        y = self.dropout(y)
        return x + y


class ResidualMLPNet(nn.Module):
    def __init__(self, input_dim: int, num_classes: int, blocks: list, dropout: float = 0.1, use_final_ln: bool = True):
        super().__init__()
        self.dim = input_dim
        self.blocks = nn.ModuleList()
        for hidden in blocks:
            self.blocks.append(ResidualMLPBlock(self.dim, hidden=hidden, dropout=dropout))
        self.use_final_ln = use_final_ln
        if use_final_ln:
            self.ln_f = nn.LayerNorm(self.dim)
        else:
            self.ln_f = nn.Identity()
        self.head = nn.Linear(self.dim, num_classes)
        self.reset_parameters()

    def reset_parameters(self):
        for m in self.modules():
            if isinstance(m, nn.Linear):
                nn.init.kaiming_uniform_(m.weight, a=math.sqrt(5))
                if m.bias is not None:
                    fan_in, _ = nn.init._calculate_fan_in_and_fan_out(m.weight)
                    bound = 1 / math.sqrt(fan_in) if fan_in > 0 else 0.0
                    nn.init.uniform_(m.bias, -bound, bound)
            elif isinstance(m, nn.LayerNorm):
                nn.init.ones_(m.weight)
                nn.init.zeros_(m.bias)

    def forward(self, x):
        # x shape: (B, input_dim)
        for blk in self.blocks:
            x = blk(x)
        x = self.ln_f(x)
        x = self.head(x)
        return x


def cross_entropy_label_smoothing(logits, targets, smoothing=0.0):
    if smoothing <= 0.0:
        return F.cross_entropy(logits, targets)
    n_classes = logits.size(-1)
    with torch.no_grad():
        true_dist = torch.empty_like(logits).fill_(smoothing / (n_classes - 1))
        true_dist.scatter_(1, targets.unsqueeze(1), 1.0 - smoothing)
    log_prob = F.log_softmax(logits, dim=-1)
    loss = (-true_dist * log_prob).sum(dim=-1).mean()
    return loss


def evaluate(model: nn.Module, loader, device: str):
    model.eval()
    correct = 0
    total = 0
    with torch.no_grad():
        for inputs, targets in loader:
            inputs = inputs.to(device=device, dtype=torch.float32, non_blocking=False)
            targets = targets.to(device=device, dtype=torch.long, non_blocking=False)
            outputs = model(inputs)
            preds = outputs.argmax(dim=1)
            correct += (preds == targets).sum().item()
            total += targets.numel()
    acc = correct / total if total > 0 else 0.0
    return acc


def update_ema(ema_model: nn.Module, model: nn.Module, decay: float):
    with torch.no_grad():
        for p_ema, p in zip(ema_model.parameters(), model.parameters()):
            p_ema.mul_(decay).add_(p.data, alpha=1.0 - decay)
        # Copy buffers if any (not really needed for LayerNorm)
        for b_ema, b in zip(ema_model.buffers(), model.buffers()):
            b_ema.copy_(b)


class Solution:
    def solve(self, train_loader, val_loader, metadata: dict = None) -> torch.nn.Module:
        set_seed(42)
        try:
            torch.set_num_threads(min(8, os.cpu_count() or 1))
        except Exception:
            pass

        if metadata is None:
            metadata = {}
        input_dim = int(metadata.get("input_dim", 384))
        num_classes = int(metadata.get("num_classes", 128))
        param_limit = int(metadata.get("param_limit", 500_000))
        device = metadata.get("device", "cpu")

        # Architecture configuration targeting ~497k params for 384-dim
        # Blocks list: hidden sizes; None or same dim means single 384->384, number means bottleneck
        base_blocks = [128, 128, 128, None]  # 3 bottleneck + 1 same-dim
        use_final_ln = True
        dropout = 0.10

        model = ResidualMLPNet(input_dim, num_classes, blocks=base_blocks, dropout=dropout, use_final_ln=use_final_ln)
        if count_parameters(model) > param_limit:
            # Fallback to 4 bottleneck blocks
            fallback_blocks = [128, 128, 128, 128]
            model = ResidualMLPNet(input_dim, num_classes, blocks=fallback_blocks, dropout=dropout, use_final_ln=use_final_ln)
        if count_parameters(model) > param_limit:
            # Fallback remove final LN
            model = ResidualMLPNet(input_dim, num_classes, blocks=fallback_blocks, dropout=dropout, use_final_ln=False)
        if count_parameters(model) > param_limit:
            # Fallback to 3 bottleneck blocks
            model = ResidualMLPNet(input_dim, num_classes, blocks=[128, 128, 128], dropout=dropout, use_final_ln=False)

        # Final assurance
        if count_parameters(model) > param_limit:
            # As a last resort, use a compact 2-layer MLP
            model = nn.Sequential(
                nn.LayerNorm(input_dim),
                nn.Linear(input_dim, 384),
                nn.SiLU(),
                nn.Dropout(dropout),
                nn.Linear(384, num_classes),
            )

        model.to(device)

        # EMA model
        ema_model = copy.deepcopy(model).to(device)
        for p in ema_model.parameters():
            p.requires_grad_(False)

        # Optimizer and scheduler
        # Use AdamW with decoupled weight decay
        base_lr = 3e-3
        weight_decay = 0.05
        optimizer = torch.optim.AdamW(model.parameters(), lr=base_lr, weight_decay=weight_decay, betas=(0.9, 0.999))
        total_epochs = 300
        steps_per_epoch = max(1, len(train_loader))
        total_steps = total_epochs * steps_per_epoch
        warmup_steps = max(10, int(0.1 * total_steps))
        min_lr = base_lr * 0.05
        label_smoothing = 0.05
        grad_clip = 1.0
        ema_decay = 0.995

        def lr_schedule(step):
            if step < warmup_steps:
                return min_lr + (base_lr - min_lr) * (step / max(1, warmup_steps))
            # Cosine decay
            t = (step - warmup_steps) / max(1, (total_steps - warmup_steps))
            cos_decay = 0.5 * (1 + math.cos(math.pi * t))
            return min_lr + (base_lr - min_lr) * cos_decay

        global_step = 0

        # Early stopping on EMA validation accuracy
        best_acc = 0.0
        best_state = copy.deepcopy(ema_model.state_dict())
        patience = 40
        epochs_no_improve = 0

        for epoch in range(total_epochs):
            model.train()
            for inputs, targets in train_loader:
                inputs = inputs.to(device=device, dtype=torch.float32, non_blocking=False)
                targets = targets.to(device=device, dtype=torch.long, non_blocking=False)

                # Update LR per step
                lr = lr_schedule(global_step)
                for g in optimizer.param_groups:
                    g['lr'] = lr

                optimizer.zero_grad(set_to_none=True)
                logits = model(inputs)
                loss = cross_entropy_label_smoothing(logits, targets, smoothing=label_smoothing)
                loss.backward()
                if grad_clip is not None:
                    torch.nn.utils.clip_grad_norm_(model.parameters(), grad_clip)
                optimizer.step()

                # EMA update
                update_ema(ema_model, model, ema_decay)

                global_step += 1

            # Evaluate EMA model on validation set
            val_acc = evaluate(ema_model, val_loader, device)
            if val_acc > best_acc:
                best_acc = val_acc
                best_state = copy.deepcopy(ema_model.state_dict())
                epochs_no_improve = 0
            else:
                epochs_no_improve += 1
                if epochs_no_improve >= patience:
                    break

        # Load best EMA weights into the main model for return
        model.load_state_dict(best_state, strict=False)
        model.eval()
        return model