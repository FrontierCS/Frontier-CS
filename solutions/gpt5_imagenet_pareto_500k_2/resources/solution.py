import math
import copy
import time
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


class InputStandardizer(nn.Module):
    def __init__(self, dim: int):
        super().__init__()
        self.dim = dim
        self.register_buffer("mean", torch.zeros(dim))
        self.register_buffer("invstd", torch.ones(dim))

    @torch.no_grad()
    def set_stats(self, mean: torch.Tensor, std: torch.Tensor, eps: float = 1e-6):
        std = std.clone()
        std[std < eps] = eps
        self.mean.copy_(mean)
        self.invstd.copy_(1.0 / std)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return (x - self.mean) * self.invstd


class ResidualMLPBlock(nn.Module):
    def __init__(self, dim: int, dropout: float = 0.2, act: str = "silu", bias: bool = False):
        super().__init__()
        self.fc1 = nn.Linear(dim, dim, bias=bias)
        self.bn1 = nn.BatchNorm1d(dim)
        self.fc2 = nn.Linear(dim, dim, bias=bias)
        self.bn2 = nn.BatchNorm1d(dim)
        self.dropout = nn.Dropout(dropout)
        if act == "relu":
            self.act = nn.ReLU(inplace=True)
        elif act == "gelu":
            self.act = nn.GELU()
        else:
            self.act = nn.SiLU()

        self._init_weights()

    def _init_weights(self):
        nn.init.kaiming_normal_(self.fc1.weight, nonlinearity='relu')
        nn.init.kaiming_normal_(self.fc2.weight, nonlinearity='relu')
        if self.fc1.bias is not None:
            nn.init.zeros_(self.fc1.bias)
        if self.fc2.bias is not None:
            nn.init.zeros_(self.fc2.bias)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        y = self.fc1(x)
        y = self.bn1(y)
        y = self.act(y)
        y = self.dropout(y)
        y = self.fc2(y)
        y = self.bn2(y)
        y = y + x
        y = self.act(y)
        y = self.dropout(y)
        return y


class MLPClassifier(nn.Module):
    def __init__(self, input_dim: int, num_classes: int, width1: int = 512, width2: int = 256,
                 hidden_blocks: int = 1, dropout: float = 0.2, act: str = "silu", bias: bool = False):
        super().__init__()
        self.input_norm = InputStandardizer(input_dim)

        self.fc1 = nn.Linear(input_dim, width1, bias=bias)
        self.bn1 = nn.BatchNorm1d(width1)

        self.fc2 = nn.Linear(width1, width2, bias=bias)
        self.bn2 = nn.BatchNorm1d(width2)

        blocks = []
        for _ in range(hidden_blocks):
            blocks.append(ResidualMLPBlock(width2, dropout=dropout, act=act, bias=bias))
        self.resblocks = nn.Sequential(*blocks)

        self.dropout = nn.Dropout(dropout)
        self.out = nn.Linear(width2, num_classes)

        self.act_name = act
        if act == "relu":
            self.act = nn.ReLU(inplace=True)
        elif act == "gelu":
            self.act = nn.GELU()
        else:
            self.act = nn.SiLU()

        self._init_weights()

    def _init_weights(self):
        nn.init.kaiming_normal_(self.fc1.weight, nonlinearity='relu')
        nn.init.kaiming_normal_(self.fc2.weight, nonlinearity='relu')
        if self.fc1.bias is not None:
            nn.init.zeros_(self.fc1.bias)
        if self.fc2.bias is not None:
            nn.init.zeros_(self.fc2.bias)
        nn.init.zeros_(self.out.bias)
        nn.init.kaiming_normal_(self.out.weight, nonlinearity='linear')

    @torch.no_grad()
    def set_input_stats(self, mean: torch.Tensor, std: torch.Tensor):
        self.input_norm.set_stats(mean, std)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self.input_norm(x)
        x = self.fc1(x)
        x = self.bn1(x)
        x = self.act(x)
        x = self.dropout(x)
        x = self.fc2(x)
        x = self.bn2(x)
        x = self.act(x)
        x = self.dropout(x)
        if len(self.resblocks) > 0:
            x = self.resblocks(x)
        x = self.out(x)
        return x


class ModelEMA:
    def __init__(self, model: nn.Module, decay: float = 0.995):
        self.ema = copy.deepcopy(model)
        self.ema.eval()
        for p in self.ema.parameters():
            p.requires_grad_(False)
        self.decay = decay

    @torch.no_grad()
    def update(self, model: nn.Module):
        d = self.decay
        msd = model.state_dict()
        for k, v in self.ema.state_dict().items():
            if k in msd:
                if v.dtype.is_floating_point:
                    v.mul_(d).add_(msd[k].detach(), alpha=(1.0 - d))
                else:
                    v.copy_(msd[k].detach())

    def to(self, device):
        self.ema.to(device)

    def state_dict(self):
        return self.ema.state_dict()

    def load_state_dict(self, state_dict):
        self.ema.load_state_dict(state_dict)

    def model(self):
        return self.ema


def compute_feature_stats(loader, input_dim: int, device: torch.device):
    cnt = 0
    mean = torch.zeros(input_dim, dtype=torch.float64)
    m2 = torch.zeros(input_dim, dtype=torch.float64)
    with torch.no_grad():
        for x, _ in loader:
            x = x.to('cpu', dtype=torch.float64)
            batch = x.shape[0]
            cnt += batch
            mean += x.sum(dim=0)
            m2 += (x * x).sum(dim=0)
    if cnt == 0:
        mean_f = torch.zeros(input_dim, dtype=torch.float32)
        std_f = torch.ones(input_dim, dtype=torch.float32)
        return mean_f.to(device), std_f.to(device)
    mean = mean / cnt
    var = m2 / cnt - mean.pow(2)
    var.clamp_(min=1e-8)
    std = var.sqrt()
    return mean.to(device, dtype=torch.float32), std.to(device, dtype=torch.float32)


def adjust_learning_rate(optimizer, base_lr, epoch, epochs, warmup_epochs=10, min_lr_ratio=0.05):
    if epoch < warmup_epochs:
        lr = base_lr * float(epoch + 1) / float(max(1, warmup_epochs))
    else:
        t = (epoch - warmup_epochs) / float(max(1, epochs - warmup_epochs))
        lr_min = base_lr * min_lr_ratio
        lr = lr_min + (base_lr - lr_min) * 0.5 * (1.0 + math.cos(math.pi * t))
    for pg in optimizer.param_groups:
        pg['lr'] = lr
    return lr


@torch.no_grad()
def evaluate(model: nn.Module, loader, device: torch.device):
    model.eval()
    correct = 0
    total = 0
    for x, y in loader:
        x = x.to(device)
        y = y.to(device)
        logits = model(x)
        pred = logits.argmax(dim=1)
        correct += (pred == y).sum().item()
        total += y.numel()
    acc = correct / total if total > 0 else 0.0
    return acc


class Solution:
    def solve(self, train_loader, val_loader, metadata: dict = None) -> torch.nn.Module:
        set_seed(42)
        if metadata is None:
            metadata = {}
        input_dim = int(metadata.get("input_dim", 384))
        num_classes = int(metadata.get("num_classes", 128))
        param_limit = int(metadata.get("param_limit", 500000))
        device = torch.device(metadata.get("device", "cpu"))

        # Model configuration aiming to be near the parameter budget without exceeding it
        width1 = 512
        width2 = 256
        hidden_blocks = 1
        dropout = 0.18
        act = "silu"
        bias = False

        # Build model ensuring parameter constraint
        while True:
            model = MLPClassifier(input_dim, num_classes, width1=width1, width2=width2,
                                  hidden_blocks=hidden_blocks, dropout=dropout, act=act, bias=bias)
            if count_parameters(model) <= param_limit:
                break
            # Fallback reductions if somehow over budget
            if hidden_blocks > 0:
                hidden_blocks -= 1
                continue
            if width1 > 480:
                width1 = 480
                continue
            if width2 > 224:
                width2 -= 32
                continue
            # As a last resort, reduce width1 further
            if width1 > 384:
                width1 -= 32
                continue
            break

        model.to(device)

        # Compute and set input normalization stats
        mean, std = compute_feature_stats(train_loader, input_dim, device)
        model.set_input_stats(mean, std)

        # Verify parameter constraint strictly
        params = count_parameters(model)
        if params > param_limit:
            raise RuntimeError(f"Model parameters exceed limit: {params} > {param_limit}")

        # Optimizer and loss
        base_lr = 3e-3
        weight_decay = 1e-4
        criterion = nn.CrossEntropyLoss(label_smoothing=0.05)
        optimizer = torch.optim.AdamW(model.parameters(), lr=base_lr, weight_decay=weight_decay)

        # EMA for better generalization
        ema = ModelEMA(model, decay=0.995)
        ema.to(device)

        # Training configuration
        epochs = 160
        warmup_epochs = 8
        patience = 30
        best_val = -1.0
        best_state = copy.deepcopy(ema.state_dict())
        no_improve = 0

        for epoch in range(epochs):
            lr = adjust_learning_rate(optimizer, base_lr, epoch, epochs, warmup_epochs=warmup_epochs, min_lr_ratio=0.05)
            model.train()
            for xb, yb in train_loader:
                xb = xb.to(device)
                yb = yb.to(device)

                logits = model(xb)
                loss = criterion(logits, yb)

                optimizer.zero_grad(set_to_none=True)
                loss.backward()
                nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
                optimizer.step()
                ema.update(model)

            # Validation with EMA weights
            val_acc = evaluate(ema.model(), val_loader, device) if val_loader is not None else evaluate(ema.model(), train_loader, device)

            if val_acc > best_val:
                best_val = val_acc
                best_state = copy.deepcopy(ema.state_dict())
                no_improve = 0
            else:
                no_improve += 1
                if no_improve >= patience:
                    break

        # Load best EMA weights and return the EMA model
        ema.load_state_dict(best_state)
        final_model = ema.model()
        final_model.to(device)
        final_model.eval()
        return final_model
