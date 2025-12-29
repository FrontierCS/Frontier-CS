import math
import os
import random
from copy import deepcopy
import torch
import torch.nn as nn
import torch.nn.functional as F


def seed_everything(seed: int = 42):
    random.seed(seed)
    os.environ["PYTHONHASHSEED"] = str(seed)
    torch.manual_seed(seed)


def count_parameters(model: nn.Module) -> int:
    return sum(p.numel() for p in model.parameters() if p.requires_grad)


class ResidualBottleneckMLP(nn.Module):
    def __init__(self, dim: int, hidden: int, dropout: float = 0.1, layerscale_init: float = 0.1):
        super().__init__()
        self.norm = nn.LayerNorm(dim)
        self.fc1 = nn.Linear(dim, hidden, bias=True)
        self.fc2 = nn.Linear(hidden, dim, bias=True)
        self.act = nn.GELU()
        self.drop = nn.Dropout(dropout)
        # LayerScale to stabilize training
        self.scale = nn.Parameter(torch.ones(dim) * layerscale_init)

    def forward(self, x):
        y = self.norm(x)
        y = self.fc1(y)
        y = self.act(y)
        y = self.fc2(y)
        y = self.drop(y)
        return x + y * self.scale


class MLPClassifier(nn.Module):
    def __init__(self, input_dim: int, num_classes: int, r_list, head_dim: int = 64, dropout: float = 0.1):
        super().__init__()
        self.input_norm = nn.LayerNorm(input_dim)
        blocks = []
        for r in r_list:
            blocks.append(ResidualBottleneckMLP(input_dim, r, dropout=dropout))
        self.blocks = nn.Sequential(*blocks)
        self.out_norm = nn.LayerNorm(input_dim)
        self.head_fc1 = nn.Linear(input_dim, head_dim, bias=True)
        self.head_act = nn.GELU()
        self.head_drop = nn.Dropout(dropout)
        self.head_fc2 = nn.Linear(head_dim, num_classes, bias=True)

    def forward(self, x):
        x = x.view(x.size(0), -1)
        x = self.input_norm(x)
        x = self.blocks(x)
        x = self.out_norm(x)
        x = self.head_fc1(x)
        x = self.head_act(x)
        x = self.head_drop(x)
        x = self.head_fc2(x)
        return x


class EMA:
    def __init__(self, model: nn.Module, decay: float = 0.999):
        self.decay = decay
        self.shadow = {}
        for name, p in model.named_parameters():
            if p.requires_grad:
                self.shadow[name] = p.detach().clone()

    @torch.no_grad()
    def update(self, model: nn.Module):
        for name, p in model.named_parameters():
            if not p.requires_grad:
                continue
            self.shadow[name].mul_(self.decay).add_(p.detach(), alpha=1.0 - self.decay)

    @torch.no_grad()
    def apply_to(self, model: nn.Module):
        for name, p in model.named_parameters():
            if p.requires_grad:
                p.data.copy_(self.shadow[name])


class Solution:
    def _build_model_under_budget(self, input_dim: int, num_classes: int, param_limit: int):
        # Initialize candidate configuration based on input_dim
        def round8(x): return max(8, int(x // 8) * 8)
        r1 = round8(max(32, input_dim // 3))
        r2 = round8(max(24, input_dim // 8))
        r3 = round8(max(16, input_dim // 16))
        r_list = [r1, r2, r3]
        head_dim = max(32, min(64, round8(input_dim // 6 if input_dim >= 192 else input_dim // 8)))

        # Try to reduce progressively until under budget
        while True:
            model = MLPClassifier(input_dim, num_classes, r_list=r_list, head_dim=head_dim, dropout=0.1)
            params = count_parameters(model)
            if params <= param_limit:
                return model
            # Reduce capacity by priority: head_dim -> smallest bottleneck -> second smallest -> largest
            if head_dim > 32:
                head_dim = max(32, head_dim - 8)
                continue
            if r_list[-1] > 8:
                r_list[-1] = max(8, r_list[-1] - 8)
                continue
            if r_list[-2] > 8:
                r_list[-2] = max(8, r_list[-2] - 8)
                continue
            if r_list[0] > 16:
                r_list[0] = max(16, r_list[0] - 8)
                continue
            # As a last resort, drop a block
            if len(r_list) > 1:
                r_list.pop()
                continue
            # If still above budget (shouldn't happen), return minimal model
            return model

    def _eval_accuracy(self, model: nn.Module, loader, device: str):
        model.eval()
        correct = 0
        total = 0
        with torch.no_grad():
            for x, y in loader:
                x = x.to(device, non_blocking=False).float()
                y = y.to(device, non_blocking=False).long()
                logits = model(x)
                preds = logits.argmax(dim=1)
                correct += (preds == y).sum().item()
                total += y.numel()
        return correct / max(1, total)

    def solve(self, train_loader, val_loader, metadata: dict = None) -> torch.nn.Module:
        seed_everything(42)
        device = (metadata or {}).get("device", "cpu")
        input_dim = (metadata or {}).get("input_dim", 384)
        num_classes = (metadata or {}).get("num_classes", 128)
        param_limit = (metadata or {}).get("param_limit", 200_000)

        model = self._build_model_under_budget(input_dim, num_classes, param_limit)
        model.to(device)

        # Safety: ensure parameter budget is respected
        if count_parameters(model) > param_limit:
            # Fallback minimal model
            model = MLPClassifier(input_dim, num_classes, r_list=[max(8, input_dim // 16)], head_dim=32, dropout=0.1)
            model.to(device)

        optimizer = torch.optim.AdamW(model.parameters(), lr=2e-3, weight_decay=2e-4, betas=(0.9, 0.999))
        ema = EMA(model, decay=0.997)

        # Scheduler: cosine with warmup per-step
        num_epochs = 160
        steps_per_epoch = max(1, len(train_loader))
        total_steps = num_epochs * steps_per_epoch
        warmup_steps = max(10, min(200, total_steps // 10))
        base_lr = 2e-3
        min_lr = 1e-5

        def adjust_lr(step):
            if total_steps <= 0:
                lr = base_lr
            elif step < warmup_steps:
                lr = base_lr * float(step + 1) / float(max(1, warmup_steps))
            else:
                progress = float(step - warmup_steps) / float(max(1, total_steps - warmup_steps))
                lr = min_lr + 0.5 * (base_lr - min_lr) * (1.0 + math.cos(math.pi * progress))
            for pg in optimizer.param_groups:
                pg["lr"] = lr

        smoothing = 0.08
        mixup_alpha = 0.2
        mixup_prob = 0.5
        grad_clip_norm = 1.0

        def mixup_data(x, y, alpha=1.0):
            if alpha <= 0:
                return x, y, y, 1.0
            lam = np_random_beta(alpha, alpha)
            batch_size = x.size(0)
            index = torch.randperm(batch_size, device=x.device)
            mixed_x = lam * x + (1 - lam) * x[index]
            y_a, y_b = y, y[index]
            return mixed_x, y_a, y_b, lam

        def np_random_beta(a, b):
            # Torch Beta distribution may not be available in all versions; use numpy-like via torch.gamma
            ga = torch.distributions.Gamma(a, 1.0).sample()
            gb = torch.distributions.Gamma(b, 1.0).sample()
            return float(ga / (ga + gb))

        global_step = 0
        best_val_acc = -1.0
        best_state_dict = None
        patience = 30
        no_improve_epochs = 0

        for epoch in range(num_epochs):
            model.train()
            epoch_loss = 0.0
            for batch in train_loader:
                x, y = batch
                x = x.to(device, non_blocking=False).float()
                y = y.to(device, non_blocking=False).long()

                use_mix = (random.random() < mixup_prob)
                if use_mix:
                    xm, ya, yb, lam = mixup_data(x, y, mixup_alpha)
                    logits = model(xm)
                    loss = lam * F.cross_entropy(logits, ya, label_smoothing=smoothing) + (1 - lam) * F.cross_entropy(
                        logits, yb, label_smoothing=smoothing
                    )
                else:
                    logits = model(x)
                    loss = F.cross_entropy(logits, y, label_smoothing=smoothing)

                optimizer.zero_grad(set_to_none=True)
                loss.backward()
                if grad_clip_norm is not None and grad_clip_norm > 0:
                    nn.utils.clip_grad_norm_(model.parameters(), grad_clip_norm)
                optimizer.step()
                ema.update(model)

                adjust_lr(global_step)
                global_step += 1
                epoch_loss += float(loss.detach().cpu())

            # Evaluate with EMA weights
            # Backup current params
            backup_state = {k: v.detach().clone() for k, v in model.state_dict().items()}
            ema.apply_to(model)
            val_acc = self._eval_accuracy(model, val_loader, device)
            # Restore parameters
            model.load_state_dict(backup_state)

            if val_acc > best_val_acc:
                best_val_acc = val_acc
                best_state_dict = deepcopy(ema.shadow)  # save EMA parameters
                no_improve_epochs = 0
            else:
                no_improve_epochs += 1

            if no_improve_epochs >= patience:
                break

        # Load best EMA weights if available
        if best_state_dict is not None:
            with torch.no_grad():
                for name, p in model.named_parameters():
                    if p.requires_grad and name in best_state_dict:
                        p.data.copy_(best_state_dict[name])

        model.eval()
        return model