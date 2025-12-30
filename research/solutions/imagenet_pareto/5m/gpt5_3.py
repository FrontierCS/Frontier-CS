import math
import time
from typing import Tuple, List

import torch
import torch.nn as nn
import torch.nn.functional as F


class ResidualLowRankBlock(nn.Module):
    def __init__(self, hidden_dim: int, rank_dim: int, dropout: float = 0.1, res_scale: float = 1.0, activation: str = "silu"):
        super().__init__()
        self.ln = nn.LayerNorm(hidden_dim)
        self.fc1 = nn.Linear(hidden_dim, rank_dim, bias=True)
        self.fc2 = nn.Linear(rank_dim, hidden_dim, bias=True)
        self.dropout = nn.Dropout(dropout)
        self.res_scale = res_scale
        if activation == "gelu":
            self.act = nn.GELU()
        elif activation == "relu":
            self.act = nn.ReLU()
        else:
            self.act = nn.SiLU()

        self._init_weights()

    def _init_weights(self):
        nn.init.kaiming_uniform_(self.fc1.weight, a=math.sqrt(5))
        nn.init.zeros_(self.fc1.bias)
        nn.init.kaiming_uniform_(self.fc2.weight, a=math.sqrt(5))
        nn.init.zeros_(self.fc2.bias)
        nn.init.ones_(self.ln.weight)
        nn.init.zeros_(self.ln.bias)

    def forward(self, x):
        h = self.ln(x)
        h = self.fc1(h)
        h = self.act(h)
        h = self.dropout(h)
        h = self.fc2(h)
        h = self.dropout(h)
        return x + self.res_scale * h


class LowRankMLP(nn.Module):
    def __init__(self, input_dim: int, num_classes: int, hidden_dim: int, rank_dim: int, num_blocks: int, dropout: float = 0.1, activation: str = "silu"):
        super().__init__()
        self.input_dim = input_dim
        self.num_classes = num_classes
        self.hidden_dim = hidden_dim
        self.rank_dim = rank_dim
        self.num_blocks = num_blocks

        self.in_proj = nn.Linear(input_dim, hidden_dim, bias=True)
        self.in_ln = nn.LayerNorm(hidden_dim)

        blocks = []
        res_scale = 1.0
        for _ in range(num_blocks):
            blocks.append(ResidualLowRankBlock(hidden_dim, rank_dim, dropout=dropout, res_scale=res_scale, activation=activation))
        self.blocks = nn.ModuleList(blocks)
        self.out_ln = nn.LayerNorm(hidden_dim)
        self.head = nn.Linear(hidden_dim, num_classes, bias=True)

        self._init_weights()

    def _init_weights(self):
        nn.init.kaiming_uniform_(self.in_proj.weight, a=math.sqrt(5))
        if self.in_proj.bias is not None:
            nn.init.zeros_(self.in_proj.bias)
        nn.init.ones_(self.in_ln.weight)
        nn.init.zeros_(self.in_ln.bias)
        nn.init.ones_(self.out_ln.weight)
        nn.init.zeros_(self.out_ln.bias)
        nn.init.kaiming_uniform_(self.head.weight, a=math.sqrt(5))
        if self.head.bias is not None:
            nn.init.zeros_(self.head.bias)

    def forward(self, x):
        x = self.in_proj(x)
        x = self.in_ln(x)
        for blk in self.blocks:
            x = blk(x)
        x = self.out_ln(x)
        x = self.head(x)
        return x


def count_trainable_parameters(model: nn.Module) -> int:
    return sum(p.numel() for p in model.parameters() if p.requires_grad)


def accuracy_from_logits(logits: torch.Tensor, targets: torch.Tensor) -> float:
    preds = logits.argmax(dim=1)
    correct = (preds == targets).sum().item()
    total = targets.numel()
    return correct / total if total > 0 else 0.0


def evaluate_accuracy(model: nn.Module, data_loader, device: torch.device) -> float:
    model.eval()
    correct = 0
    total = 0
    with torch.no_grad():
        for xb, yb in data_loader:
            xb = xb.to(device=device, dtype=torch.float32, non_blocking=False)
            yb = yb.to(device=device, dtype=torch.long, non_blocking=False)
            logits = model(xb)
            preds = logits.argmax(dim=1)
            correct += (preds == yb).sum().item()
            total += yb.numel()
    return correct / total if total > 0 else 0.0


def _get_param_tensors(model: nn.Module) -> List[torch.Tensor]:
    return [p for p in model.parameters() if p.requires_grad]


def ema_initialize(model: nn.Module) -> List[torch.Tensor]:
    return [p.detach().clone() for p in _get_param_tensors(model)]


def ema_update(model: nn.Module, ema_params: List[torch.Tensor], decay: float):
    with torch.no_grad():
        for p, e in zip(_get_param_tensors(model), ema_params):
            e.mul_(decay).add_(p.data, alpha=(1.0 - decay))


def ema_apply_to_model(model: nn.Module, ema_params: List[torch.Tensor]) -> List[torch.Tensor]:
    backup = []
    with torch.no_grad():
        for p, e in zip(_get_param_tensors(model), ema_params):
            backup.append(p.data.detach().clone())
            p.data.copy_(e)
    return backup


def restore_from_backup(model: nn.Module, backup_params: List[torch.Tensor]):
    with torch.no_grad():
        for p, b in zip(_get_param_tensors(model), backup_params):
            p.data.copy_(b)


class Solution:
    def solve(self, train_loader, val_loader, metadata: dict = None) -> torch.nn.Module:
        device_str = metadata.get("device", "cpu") if metadata is not None else "cpu"
        device = torch.device(device_str)

        input_dim = int(metadata.get("input_dim", 384)) if metadata is not None else 384
        num_classes = int(metadata.get("num_classes", 128)) if metadata is not None else 128
        param_limit = int(metadata.get("param_limit", 5_000_000)) if metadata is not None else 5_000_000

        # Candidate configurations ordered from largest to smaller, all intended to fit under 5M with LayerNorm-based model
        candidates = [
            (2752, 160, 4),  # ~4.98M
            (2688, 160, 4),
            (2560, 160, 4),
            (2304, 192, 4),
            (2304, 256, 3),
            (2048, 192, 4),
            (2048, 256, 3),
            (1920, 192, 4),
            (1536, 192, 4),
        ]

        chosen_model = None
        dropout = 0.10
        activation = "silu"

        for hidden_dim, rank_dim, num_blocks in candidates:
            model = LowRankMLP(input_dim, num_classes, hidden_dim, rank_dim, num_blocks, dropout=dropout, activation=activation)
            total_params = count_trainable_parameters(model)
            if total_params <= param_limit:
                chosen_model = model
                break

        if chosen_model is None:
            # Fallback to a small model ensuring we stay within param limit
            chosen_model = LowRankMLP(input_dim, num_classes, 1024, 128, 3, dropout=0.05, activation=activation)
            # In worst case if still exceeds, reduce
            while count_trainable_parameters(chosen_model) > param_limit:
                # Gradually shrink
                hd = max(512, chosen_model.hidden_dim - 128)
                rd = max(64, chosen_model.rank_dim - 32)
                nb = max(2, chosen_model.num_blocks - 1)
                chosen_model = LowRankMLP(input_dim, num_classes, hd, rd, nb, dropout=0.05, activation=activation)

        model = chosen_model.to(device)
        param_count = count_trainable_parameters(model)

        # Training hyperparameters
        # Choose epochs based on model size to balance time and performance
        if param_count > 4_750_000:
            epochs = 120
            lr = 3e-3
            weight_decay = 1e-4
        elif param_count > 3_500_000:
            epochs = 130
            lr = 3e-3
            weight_decay = 1.2e-4
        else:
            epochs = 150
            lr = 3e-3
            weight_decay = 1.5e-4

        label_smoothing = 0.05
        max_grad_norm = 1.0
        mixup_alpha = 0.2
        mixup_prob = 0.50
        use_mixup = True

        optimizer = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=weight_decay, betas=(0.9, 0.99))
        scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=epochs, eta_min=lr * 0.05)
        criterion = nn.CrossEntropyLoss(label_smoothing=label_smoothing)

        # EMA of model parameters
        ema_decay = 0.995
        ema_params = ema_initialize(model)

        # Early stopping
        best_val_acc = -1.0
        best_state = None
        patience = 20
        epochs_no_improve = 0

        def train_one_epoch():
            model.train()
            total_loss = 0.0
            total = 0
            for xb, yb in train_loader:
                xb = xb.to(device=device, dtype=torch.float32, non_blocking=False)
                yb = yb.to(device=device, dtype=torch.long, non_blocking=False)

                optimizer.zero_grad(set_to_none=True)

                if use_mixup and (mixup_alpha > 0.0) and (torch.rand(1).item() < mixup_prob):
                    lam = torch.distributions.Beta(mixup_alpha, mixup_alpha).sample().item()
                    batch_size = xb.size(0)
                    index = torch.randperm(batch_size, device=xb.device)
                    xb_mixed = lam * xb + (1.0 - lam) * xb[index, :]
                    logits = model(xb_mixed)
                    yb_shuffled = yb[index]
                    loss = lam * criterion(logits, yb) + (1.0 - lam) * criterion(logits, yb_shuffled)
                else:
                    logits = model(xb)
                    loss = criterion(logits, yb)

                loss.backward()
                if max_grad_norm is not None and max_grad_norm > 0:
                    torch.nn.utils.clip_grad_norm_(model.parameters(), max_grad_norm)
                optimizer.step()

                # EMA update post-step
                ema_update(model, ema_params, ema_decay)

                total_loss += loss.item() * xb.size(0)
                total += xb.size(0)
            return total_loss / max(1, total)

        @torch.no_grad()
        def validate_with_ema():
            backup = ema_apply_to_model(model, ema_params)
            acc = evaluate_accuracy(model, val_loader, device)
            restore_from_backup(model, backup)
            return acc

        # Training loop
        for epoch in range(epochs):
            train_one_epoch()
            val_acc = validate_with_ema()
            if val_acc > best_val_acc:
                best_val_acc = val_acc
                best_state = [p.detach().clone() for p in ema_params]
                epochs_no_improve = 0
            else:
                epochs_no_improve += 1
            scheduler.step()
            if epochs_no_improve >= patience:
                break

        # Load best EMA weights to the model
        if best_state is None:
            best_state = ema_params
        backup = ema_apply_to_model(model, best_state)
        # No BN to update; if BN existed we might run a pass to update stats
        model.eval()
        # keep best ema weights
        backup = None

        return model