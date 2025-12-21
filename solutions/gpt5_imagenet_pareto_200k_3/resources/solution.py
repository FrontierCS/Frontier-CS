import math
import random
import copy
import torch
import torch.nn as nn
import torch.nn.functional as F


def count_parameters(model: nn.Module) -> int:
    return sum(p.numel() for p in model.parameters() if p.requires_grad)


def soft_cross_entropy(logits: torch.Tensor, target_probs: torch.Tensor) -> torch.Tensor:
    log_probs = F.log_softmax(logits, dim=1)
    loss = -(target_probs * log_probs).sum(dim=1).mean()
    return loss


def get_param_groups(model: nn.Module, weight_decay: float):
    decay, no_decay = [], []
    for name, param in model.named_parameters():
        if not param.requires_grad:
            continue
        if param.ndim == 1 or name.endswith(".bias"):
            no_decay.append(param)
        else:
            decay.append(param)
    return [
        {"params": decay, "weight_decay": weight_decay},
        {"params": no_decay, "weight_decay": 0.0},
    ]


class ResidualSingle(nn.Module):
    def __init__(self, dim: int, dropout: float = 0.15, layerscale_init: float = 0.1):
        super().__init__()
        self.bn = nn.BatchNorm1d(dim)
        self.act = nn.GELU()
        self.dropout = nn.Dropout(dropout)
        self.fc = nn.Linear(dim, dim, bias=False)
        self.gamma = nn.Parameter(torch.ones(dim) * layerscale_init)

        nn.init.kaiming_normal_(self.fc.weight, nonlinearity="linear")

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        y = self.bn(x)
        y = self.act(y)
        y = self.dropout(y)
        y = self.fc(y)
        y = y * self.gamma
        return x + y


class MLPNet(nn.Module):
    def __init__(self, input_dim: int, num_classes: int, hidden_dim: int, dropout: float = 0.15):
        super().__init__()
        self.in_bn = nn.BatchNorm1d(input_dim)
        self.fc_in = nn.Linear(input_dim, hidden_dim, bias=False)
        self.block = ResidualSingle(hidden_dim, dropout=dropout, layerscale_init=0.1)
        self.bn_head = nn.BatchNorm1d(hidden_dim)
        self.act = nn.GELU()
        self.dropout = nn.Dropout(dropout)
        self.fc_out = nn.Linear(hidden_dim, num_classes, bias=True)

        self.reset_parameters()

    def reset_parameters(self):
        nn.init.kaiming_normal_(self.fc_in.weight, nonlinearity="linear")
        nn.init.kaiming_normal_(self.fc_out.weight, nonlinearity="linear")
        nn.init.zeros_(self.fc_out.bias)
        # BatchNorms are initialized by default (weight=1, bias=0)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self.in_bn(x)
        x = self.fc_in(x)
        x = self.block(x)
        y = self.bn_head(x)
        y = self.act(y)
        y = self.dropout(y)
        out = self.fc_out(y)
        return out


class Solution:
    def _compute_params_for_hidden(self, input_dim, num_classes, hidden_dim, include_layerscale=True, include_input_bn=True):
        # Linear in (no bias)
        p = input_dim * hidden_dim
        # Residual single (no bias), plus BN and gamma
        p += hidden_dim * hidden_dim  # fc in block
        p += 2 * hidden_dim  # bn weight+bias in block
        if include_layerscale:
            p += hidden_dim  # gamma
        # Output head: BN + Linear out (with bias)
        p += 2 * hidden_dim  # head BN
        p += hidden_dim * num_classes + num_classes  # out layer weights + bias
        # Input BN
        if include_input_bn:
            p += 2 * input_dim
        return p

    def _select_hidden_dim(self, input_dim, num_classes, param_limit):
        # Search for the largest hidden_dim multiple of 8 within the limit (practical constraint)
        max_h = min(512, max(64, (param_limit // (input_dim + num_classes + 1))))
        if max_h % 8 != 0:
            max_h = (max_h // 8) * 8
        best_h = 64
        for h in range(max_h, 63, -8):
            p = self._compute_params_for_hidden(input_dim, num_classes, h, include_layerscale=True, include_input_bn=True)
            if p <= param_limit:
                best_h = h
                break
        return best_h

    def solve(self, train_loader, val_loader, metadata: dict = None) -> torch.nn.Module:
        if metadata is None:
            metadata = {}
        input_dim = int(metadata.get("input_dim", 384))
        num_classes = int(metadata.get("num_classes", 128))
        param_limit = int(metadata.get("param_limit", 200_000))
        device = torch.device(metadata.get("device", "cpu"))

        torch.manual_seed(42)
        random.seed(42)

        hidden_dim = self._select_hidden_dim(input_dim, num_classes, param_limit)
        model = MLPNet(input_dim=input_dim, num_classes=num_classes, hidden_dim=hidden_dim, dropout=0.15)
        model.to(device)

        # Safety check: ensure within param limit; if not, reduce hidden dim
        while count_parameters(model) > param_limit and hidden_dim >= 64:
            hidden_dim = max(64, hidden_dim - 8)
            model = MLPNet(input_dim=input_dim, num_classes=num_classes, hidden_dim=hidden_dim, dropout=0.15).to(device)

        # Optimizer with proper param groups
        base_lr = 0.002
        weight_decay = 2e-4
        optimizer = torch.optim.AdamW(get_param_groups(model, weight_decay), lr=base_lr, betas=(0.9, 0.999))

        # Scheduler with warmup + cosine
        total_epochs = 200
        warmup_epochs = 8
        min_lr_ratio = 0.05

        def lr_lambda(epoch):
            if epoch < warmup_epochs:
                return (epoch + 1) / float(warmup_epochs)
            progress = (epoch - warmup_epochs) / max(1, (total_epochs - warmup_epochs))
            cosine = 0.5 * (1.0 + math.cos(math.pi * progress))
            return min_lr_ratio + (1.0 - min_lr_ratio) * cosine

        scheduler = torch.optim.lr_scheduler.LambdaLR(optimizer, lr_lambda=lr_lambda)

        # Training setup
        label_smoothing = 0.05
        mixup_alpha = 0.2
        mixup_prob = 0.25

        def make_soft_targets(targets, num_classes, smoothing):
            with torch.no_grad():
                true_dist = torch.full((targets.size(0), num_classes), smoothing / num_classes, device=targets.device)
                true_dist.scatter_(1, targets.unsqueeze(1), 1.0 - smoothing)
            return true_dist

        def mixup_data(x, y, alpha):
            if alpha <= 0:
                return x, y, None
            m = torch.distributions.Beta(alpha, alpha).sample().item()
            lam = float(m)
            indices = torch.randperm(x.size(0), device=x.device)
            x_mix = lam * x + (1.0 - lam) * x[indices]
            y1 = y
            y2 = y[indices]
            return x_mix, (y1, y2), lam

        def train_one_epoch():
            model.train()
            total_loss = 0.0
            total_samples = 0
            for inputs, targets in train_loader:
                inputs = inputs.to(device, non_blocking=False)
                targets = targets.to(device, non_blocking=False)

                do_mix = (random.random() < mixup_prob)
                if do_mix and mixup_alpha > 0.0:
                    inputs, y_mix, lam = mixup_data(inputs, targets, mixup_alpha)
                    y1, y2 = y_mix
                    # Construct soft targets with optional smoothing
                    t1 = F.one_hot(y1, num_classes=num_classes).float()
                    t2 = F.one_hot(y2, num_classes=num_classes).float()
                    mixed = lam * t1 + (1.0 - lam) * t2
                    if label_smoothing > 0.0:
                        mixed = mixed * (1.0 - label_smoothing) + label_smoothing / num_classes
                    logits = model(inputs)
                    loss = soft_cross_entropy(logits, mixed)
                else:
                    logits = model(inputs)
                    if label_smoothing > 0.0:
                        loss = F.cross_entropy(logits, targets, label_smoothing=label_smoothing)
                    else:
                        loss = F.cross_entropy(logits, targets)

                optimizer.zero_grad(set_to_none=True)
                loss.backward()
                nn.utils.clip_grad_norm_(model.parameters(), max_norm=3.0)
                optimizer.step()

                bs = targets.size(0)
                total_loss += loss.item() * bs
                total_samples += bs

            return total_loss / max(1, total_samples)

        @torch.no_grad()
        def evaluate(loader):
            model.eval()
            correct = 0
            total = 0
            for inputs, targets in loader:
                inputs = inputs.to(device, non_blocking=False)
                targets = targets.to(device, non_blocking=False)
                outputs = model(inputs)
                preds = outputs.argmax(dim=1)
                correct += (preds == targets).sum().item()
                total += targets.numel()
            acc = correct / max(1, total)
            return acc

        if val_loader is None:
            val_loader = train_loader

        best_state = copy.deepcopy(model.state_dict())
        best_acc = 0.0
        patience = 30
        epochs_no_improve = 0

        for epoch in range(total_epochs):
            train_one_epoch()
            scheduler.step()
            val_acc = evaluate(val_loader)
            if val_acc > best_acc + 1e-5:
                best_acc = val_acc
                best_state = copy.deepcopy(model.state_dict())
                epochs_no_improve = 0
            else:
                epochs_no_improve += 1
                if epochs_no_improve >= patience:
                    break

        model.load_state_dict(best_state)
        model.to(device)
        return model
