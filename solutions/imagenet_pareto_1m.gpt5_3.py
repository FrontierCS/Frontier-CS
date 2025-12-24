import math
import random
import copy
import torch
import torch.nn as nn
import torch.nn.functional as F


class ResidualBottleneckBlock(nn.Module):
    def __init__(self, d_model: int, hidden_dim: int, dropout: float = 0.2):
        super().__init__()
        self.norm = nn.LayerNorm(d_model)
        self.fc1 = nn.Linear(d_model, hidden_dim, bias=True)
        self.act = nn.GELU()
        self.fc2 = nn.Linear(hidden_dim, d_model, bias=True)
        self.drop = nn.Dropout(dropout)

    def forward(self, x):
        y = self.norm(x)
        y = self.fc1(y)
        y = self.act(y)
        y = self.drop(y)
        y = self.fc2(y)
        y = self.drop(y)
        return x + y


class ResidualMLP(nn.Module):
    def __init__(
        self,
        input_dim: int,
        num_classes: int,
        d_model: int = 576,
        num_blocks: int = 2,
        bottleneck_ratio: float = 0.5,
        dropout: float = 0.2,
        input_dropout: float = 0.05,
        use_ln_out: bool = True,
    ):
        super().__init__()
        self.in_drop = nn.Dropout(input_dropout) if input_dropout and input_dropout > 0 else nn.Identity()
        self.input_proj = nn.Linear(input_dim, d_model, bias=True)
        self.act = nn.GELU()
        hidden_dim = max(1, int(d_model * bottleneck_ratio))
        self.blocks = nn.ModuleList(
            [ResidualBottleneckBlock(d_model, hidden_dim, dropout=dropout) for _ in range(num_blocks)]
        )
        self.ln_out = nn.LayerNorm(d_model) if use_ln_out else nn.Identity()
        self.head = nn.Linear(d_model, num_classes, bias=True)

    def forward(self, x):
        x = self.in_drop(x)
        x = self.input_proj(x)
        x = self.act(x)
        for blk in self.blocks:
            x = blk(x)
        x = self.ln_out(x)
        x = self.head(x)
        return x


def count_trainable_params(model: nn.Module) -> int:
    return sum(p.numel() for p in model.parameters() if p.requires_grad)


def choose_model_under_budget(input_dim, num_classes, param_limit, target_blocks=2, bottleneck_ratio=0.5):
    # Search for the largest d_model under budget
    # Start from a high width and go down
    candidate_ds = list(range(640, 255, -16))
    best_model = None
    best_d = None
    for d in candidate_ds:
        model = ResidualMLP(
            input_dim=input_dim,
            num_classes=num_classes,
            d_model=d,
            num_blocks=target_blocks,
            bottleneck_ratio=bottleneck_ratio,
            dropout=0.2,
            input_dropout=0.05,
            use_ln_out=True,
        )
        n_params = count_trainable_params(model)
        if n_params <= param_limit:
            best_model = model
            best_d = d
            break
    if best_model is None:
        # Fallback to a compact baseline
        # 2-layer MLP 384->512->128 with ReLU
        model = nn.Sequential(
            nn.Linear(input_dim, 512),
            nn.ReLU(),
            nn.Dropout(0.1),
            nn.Linear(512, num_classes),
        )
        return model, count_trainable_params(model), 512
    return best_model, count_trainable_params(best_model), best_d


def mixup_data(x, y, alpha=0.2):
    if alpha <= 0.0:
        return x, y, None
    lam = np_beta(alpha, alpha)
    batch_size = x.size(0)
    index = torch.randperm(batch_size, device=x.device)
    mixed_x = lam * x + (1 - lam) * x[index, :]
    y_a, y_b = y, y[index]
    return mixed_x, y_a, (y_b, lam)


def np_beta(a, b):
    # Lightweight Beta sampler using torch to avoid numpy dependency
    # Sample two Gamma and normalize
    ga = torch.distributions.Gamma(a, 1.0).sample()
    gb = torch.distributions.Gamma(b, 1.0).sample()
    lam = ga / (ga + gb)
    return float(lam)


def evaluate_accuracy(model: nn.Module, data_loader, device):
    model.eval()
    correct = 0
    total = 0
    with torch.no_grad():
        for xb, yb in data_loader:
            xb = xb.to(device, non_blocking=False).float()
            yb = yb.to(device, non_blocking=False).long()
            logits = model(xb)
            preds = logits.argmax(dim=1)
            correct += (preds == yb).sum().item()
            total += yb.numel()
    return correct / total if total > 0 else 0.0


def update_ema(ema_model: nn.Module, model: nn.Module, decay: float):
    with torch.no_grad():
        msd = model.state_dict()
        for k, v in ema_model.state_dict().items():
            # Only update floating tensors
            if v.dtype.is_floating_point:
                v.mul_(decay).add_(msd[k].to(v.device), alpha=(1.0 - decay))
            else:
                v.copy_(msd[k])


class Solution:
    def solve(self, train_loader, val_loader, metadata: dict = None) -> torch.nn.Module:
        if metadata is None:
            metadata = {}
        input_dim = int(metadata.get("input_dim", 384))
        num_classes = int(metadata.get("num_classes", 128))
        param_limit = int(metadata.get("param_limit", 1_000_000))
        device_str = metadata.get("device", "cpu")
        device = torch.device(device_str)

        # Reproducibility
        seed = 42
        random.seed(seed)
        torch.manual_seed(seed)

        # Choose model architecture under budget
        model, n_params, used_d = choose_model_under_budget(
            input_dim=input_dim, num_classes=num_classes, param_limit=param_limit, target_blocks=2, bottleneck_ratio=0.5
        )

        # Safety check
        if count_trainable_params(model) > param_limit:
            # As a final guard, reduce to a minimal baseline
            model = nn.Sequential(
                nn.Linear(input_dim, 512),
                nn.GELU(),
                nn.Dropout(0.1),
                nn.Linear(512, num_classes),
            )
        model.to(device)

        # EMA model
        ema_model = copy.deepcopy(model).to(device)
        for p in ema_model.parameters():
            p.requires_grad_(False)

        # Optimizer and scheduler
        train_samples = int(metadata.get("train_samples", 2048))
        batches_per_epoch = max(1, len(train_loader))
        # Epochs: scale modestly with data size
        epochs = 160 if train_samples >= 2048 else 120
        max_lr = 0.003
        base_lr = max_lr / 10.0
        optimizer = torch.optim.AdamW(model.parameters(), lr=base_lr, weight_decay=0.05, betas=(0.9, 0.999))
        scheduler = torch.optim.lr_scheduler.OneCycleLR(
            optimizer,
            max_lr=max_lr,
            epochs=epochs,
            steps_per_epoch=batches_per_epoch,
            pct_start=0.15,
            anneal_strategy="cos",
            div_factor=max_lr / base_lr,
            final_div_factor=100.0,
        )

        # Loss functions
        criterion = nn.CrossEntropyLoss(label_smoothing=0.08)
        criterion_plain = nn.CrossEntropyLoss()

        # Training utilities
        patience = 25
        best_val = -1.0
        best_state = None
        best_ema_state = None
        ema_decay = 0.995
        mixup_alpha = 0.2
        mixup_prob = 0.5

        # Some DataLoaders may not have pinned memory; keep default

        for epoch in range(epochs):
            model.train()
            for xb, yb in train_loader:
                xb = xb.to(device, non_blocking=False).float()
                yb = yb.to(device, non_blocking=False).long()

                use_mix = (random.random() < mixup_prob) and (mixup_alpha > 0.0)
                if use_mix:
                    mixed_x, y_a, mix_info = mixup_data(xb, yb, alpha=mixup_alpha)
                    y_b, lam = mix_info
                    logits = model(mixed_x)
                    loss = lam * criterion_plain(logits, y_a) + (1.0 - lam) * criterion_plain(logits, y_b)
                else:
                    logits = model(xb)
                    loss = criterion(logits, yb)

                optimizer.zero_grad(set_to_none=True)
                loss.backward()
                nn.utils.clip_grad_norm_(model.parameters(), max_norm=2.0)
                optimizer.step()
                scheduler.step()

                update_ema(ema_model, model, decay=ema_decay)

            # Validation at epoch end for base and EMA
            val_acc_base = evaluate_accuracy(model, val_loader, device)
            val_acc_ema = evaluate_accuracy(ema_model, val_loader, device)

            if val_acc_ema >= val_acc_base:
                current_best_acc = val_acc_ema
                current_best_state = copy.deepcopy(ema_model.state_dict())
                from_ema = True
            else:
                current_best_acc = val_acc_base
                current_best_state = copy.deepcopy(model.state_dict())
                from_ema = False

            if current_best_acc > best_val:
                best_val = current_best_acc
                if from_ema:
                    best_ema_state = current_best_state
                    best_state = None
                else:
                    best_state = current_best_state
                    best_ema_state = None
                patience_counter = 0
            else:
                patience_counter = locals().get("patience_counter", 0) + 1
            if patience_counter >= patience:
                break

        # Load the best state
        if best_ema_state is not None:
            ema_model.load_state_dict(best_ema_state)
            final_model = ema_model
        elif best_state is not None:
            model.load_state_dict(best_state)
            final_model = model
        else:
            # Fallback load EMA
            final_model = ema_model

        final_model.to(device)
        final_model.eval()
        return final_model
