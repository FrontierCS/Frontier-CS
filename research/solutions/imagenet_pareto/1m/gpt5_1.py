import math
import random
import time
import torch
import torch.nn as nn
import torch.nn.functional as F


class PreNormResidualSingle(nn.Module):
    def __init__(self, dim, dropout=0.0, activation=nn.GELU):
        super().__init__()
        self.norm = nn.LayerNorm(dim)
        self.fc = nn.Linear(dim, dim)
        self.act = activation()
        self.drop = nn.Dropout(dropout)

    def forward(self, x):
        y = self.norm(x)
        y = self.act(y)
        y = self.fc(y)
        y = self.drop(y)
        return x + y


class PreNormResidualBottleneck(nn.Module):
    def __init__(self, dim, bottleneck_dim, dropout=0.0, activation=nn.GELU):
        super().__init__()
        self.norm = nn.LayerNorm(dim)
        self.fc1 = nn.Linear(dim, bottleneck_dim)
        self.act = activation()
        self.drop1 = nn.Dropout(dropout)
        self.fc2 = nn.Linear(bottleneck_dim, dim)
        self.drop2 = nn.Dropout(dropout)

    def forward(self, x):
        y = self.norm(x)
        y = self.fc1(y)
        y = self.act(y)
        y = self.drop1(y)
        y = self.fc2(y)
        y = self.drop2(y)
        return x + y


class MLPNet(nn.Module):
    def __init__(self, input_dim, num_classes, width_main=704, bottleneck_dim=256, num_blocks_256=2, dropout=0.1):
        super().__init__()
        self.in_norm = nn.LayerNorm(input_dim)

        self.stem = nn.Linear(input_dim, width_main)

        self.block_w = PreNormResidualBottleneck(width_main, bottleneck_dim, dropout=dropout)

        self.trans_norm = nn.LayerNorm(width_main)
        self.trans = nn.Linear(width_main, 256)
        self.trans_act = nn.GELU()
        self.trans_drop = nn.Dropout(dropout)

        self.blocks_256 = nn.ModuleList([PreNormResidualSingle(256, dropout=dropout) for _ in range(num_blocks_256)])

        self.head_norm = nn.LayerNorm(256)
        self.head = nn.Linear(256, num_classes)

    def forward(self, x):
        x = self.in_norm(x)
        x = self.stem(x)
        x = self.block_w(x)

        x = self.trans_norm(x)
        x = self.trans_act(self.trans(x))
        x = self.trans_drop(x)

        for blk in self.blocks_256:
            x = blk(x)

        x = self.head_norm(x)
        x = self.head(x)
        return x


class EMA:
    def __init__(self, model, decay=0.999):
        self.decay = decay
        self.shadow = {}
        self.backup = {}

        for name, param in model.named_parameters():
            if param.requires_grad:
                self.shadow[name] = param.data.clone()

    def update(self, model):
        for name, param in model.named_parameters():
            if not param.requires_grad:
                continue
            assert name in self.shadow
            new_average = self.decay * self.shadow[name] + (1.0 - self.decay) * param.data
            self.shadow[name] = new_average.clone()

    def store(self, model):
        self.backup = {}
        for name, param in model.named_parameters():
            if param.requires_grad:
                self.backup[name] = param.data.clone()

    def copy_to(self, model):
        for name, param in model.named_parameters():
            if param.requires_grad:
                param.data.copy_(self.shadow[name])

    def restore(self, model):
        for name, param in model.named_parameters():
            if param.requires_grad and name in self.backup:
                param.data.copy_(self.backup[name])
        self.backup = {}


def count_params(model: nn.Module):
    return sum(p.numel() for p in model.parameters() if p.requires_grad)


def param_count_formula(input_dim, num_classes, W, B, K):
    # Linear layers
    total = 0
    # input_norm params
    total += 2 * input_dim
    # stem
    total += input_dim * W + W
    # bottleneck residual at W
    total += W * B + B  # fc1
    total += B * W + W  # fc2
    # norms for W residual and transition
    total += 2 * W  # norm in block
    total += 2 * W  # norm before transition
    # transition to 256
    total += W * 256 + 256
    # activation/dropout no params
    # residual blocks at 256
    for _ in range(K):
        total += 2 * 256  # norm
        total += 256 * 256 + 256  # single linear
    # head norm and classifier
    total += 2 * 256
    total += 256 * num_classes + num_classes
    return int(total)


def build_model_within_limit(input_dim, num_classes, param_limit, target_utilization=0.98):
    # Candidates for width and blocks
    width_candidates = [736, 720, 704, 688, 672, 656, 640, 624, 608, 592, 576, 560, 544, 528, 512, 496, 480, 464, 448, 432, 416, 400, 384]
    # Bottleneck choices will be min(256, W//2) and min(256, W//3) but at least 128
    block_candidates = [4, 3, 2, 1]

    best_cfg = None
    best_params = -1

    for W in width_candidates:
        B_opts = []
        B_opts.append(max(128, min(256, W // 2)))
        B_opts.append(max(128, min(256, W // 3)))
        B_opts.append(256 if W >= 256 else max(128, W // 2))
        # unique and sorted descending
        B_opts = sorted(set(B_opts), reverse=True)
        for K in block_candidates:
            for B in B_opts:
                p = param_count_formula(input_dim, num_classes, W, B, K)
                if p <= param_limit and p > best_params:
                    best_params = p
                    best_cfg = (W, B, K)
            # prefer larger K but ensure param fit
    if best_cfg is None:
        # fallback tiny model
        W, B, K = 512, 192, 1
    else:
        W, B, K = best_cfg

    model = MLPNet(input_dim=input_dim, num_classes=num_classes, width_main=W, bottleneck_dim=B, num_blocks_256=K, dropout=0.1)
    # Final assert: if count > limit, reduce
    actual = count_params(model)
    if actual > param_limit:
        # degrade progressively
        for W in [512, 480, 448, 416, 384]:
            for K in [2, 1]:
                for B in [192, 160, 128]:
                    model = MLPNet(input_dim=input_dim, num_classes=num_classes, width_main=W, bottleneck_dim=B, num_blocks_256=K, dropout=0.1)
                    if count_params(model) <= param_limit:
                        return model
        # ultimate fallback minimal
        model = nn.Sequential(
            nn.LayerNorm(input_dim),
            nn.Linear(input_dim, 512),
            nn.GELU(),
            nn.Linear(512, num_classes)
        )
    return model


def set_lr(optimizer, lr):
    for g in optimizer.param_groups:
        g['lr'] = lr


def evaluate_accuracy(model, data_loader, device):
    model.eval()
    correct = 0
    total = 0
    with torch.no_grad():
        for xb, yb in data_loader:
            xb = xb.to(device)
            yb = yb.to(device)
            logits = model(xb)
            preds = logits.argmax(dim=1)
            correct += (preds == yb).sum().item()
            total += yb.numel()
    return correct / max(1, total)


def mixup_batch(x, y, alpha=0.4):
    if alpha <= 0.0:
        return x, y, y, 1.0
    lam = torch.distributions.Beta(alpha, alpha).sample().item()
    batch_size = x.size(0)
    index = torch.randperm(batch_size, device=x.device)
    mixed_x = lam * x + (1.0 - lam) * x[index, :]
    y_a, y_b = y, y[index]
    return mixed_x, y_a, y_b, lam


class Solution:
    def solve(self, train_loader, val_loader, metadata: dict = None) -> torch.nn.Module:
        device = "cpu"
        num_classes = 128
        input_dim = 384
        param_limit = 1_000_000

        if metadata is not None:
            device = metadata.get("device", device)
            num_classes = metadata.get("num_classes", num_classes)
            input_dim = metadata.get("input_dim", input_dim)
            param_limit = metadata.get("param_limit", param_limit)

        torch.manual_seed(1337)
        random.seed(1337)

        model = build_model_within_limit(input_dim, num_classes, param_limit)
        model.to(device)

        # Safety check for parameter limit
        params = count_params(model)
        if params > param_limit:
            # Fallback very small model to avoid disqualification
            model = nn.Sequential(
                nn.LayerNorm(input_dim),
                nn.Linear(input_dim, 512),
                nn.GELU(),
                nn.Dropout(0.1),
                nn.Linear(512, num_classes)
            ).to(device)

        # Optimizer and criterion
        base_lr = 0.0035
        weight_decay = 0.02
        optimizer = torch.optim.AdamW(model.parameters(), lr=base_lr, weight_decay=weight_decay)
        criterion = nn.CrossEntropyLoss(label_smoothing=0.1)

        # Training config
        steps_per_epoch = max(1, len(train_loader))
        target_steps = 7000
        max_epochs = int(min(250, max(80, math.ceil(target_steps / steps_per_epoch))))
        warmup_epochs = max(3, int(0.05 * max_epochs))
        min_lr = base_lr * 0.05

        ema = EMA(model, decay=0.999)

        best_val_acc = 0.0
        best_state = None
        epochs_no_improve = 0
        patience = 40

        def lr_at_epoch(ep):
            if ep < warmup_epochs:
                return base_lr * (ep + 1) / warmup_epochs
            t = (ep - warmup_epochs) / max(1, (max_epochs - warmup_epochs))
            cos_lr = min_lr + 0.5 * (base_lr - min_lr) * (1 + math.cos(math.pi * t))
            return float(cos_lr)

        for epoch in range(max_epochs):
            model.train()
            set_lr(optimizer, lr_at_epoch(epoch))
            for xb, yb in train_loader:
                xb = xb.to(device)
                yb = yb.to(device)

                use_mix = random.random() < 0.65
                if use_mix and xb.size(0) > 1:
                    xb_mix, ya, yb2, lam = mixup_batch(xb, yb, alpha=0.4)
                    logits = model(xb_mix)
                    loss = lam * criterion(logits, ya) + (1.0 - lam) * criterion(logits, yb2)
                else:
                    logits = model(xb)
                    loss = criterion(logits, yb)

                optimizer.zero_grad(set_to_none=True)
                loss.backward()
                nn.utils.clip_grad_norm_(model.parameters(), max_norm=5.0)
                optimizer.step()
                ema.update(model)

            # Evaluate with EMA weights
            ema.store(model)
            ema.copy_to(model)
            val_acc = evaluate_accuracy(model, val_loader, device)
            ema.restore(model)

            if val_acc > best_val_acc + 1e-5:
                best_val_acc = val_acc
                best_state = {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}
                epochs_no_improve = 0
            else:
                epochs_no_improve += 1

            if epochs_no_improve >= patience:
                break

        # Load best weights if available
        if best_state is not None:
            model.load_state_dict(best_state)

        # Apply EMA to final model for evaluation
        ema.copy_to(model)
        model.to(device)
        model.eval()
        return model