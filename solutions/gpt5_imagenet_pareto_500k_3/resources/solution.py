import math
import copy
import random
import torch
import torch.nn as nn
import torch.nn.functional as F


def set_seed(seed: int = 42):
    random.seed(seed)
    torch.manual_seed(seed)


def count_trainable_params(model: nn.Module) -> int:
    return sum(p.numel() for p in model.parameters() if p.requires_grad)


class FeatureStandardize(nn.Module):
    def __init__(self, dim: int, eps: float = 1e-6):
        super().__init__()
        self.eps = eps
        self.register_buffer("mean", torch.zeros(dim))
        self.register_buffer("invstd", torch.ones(dim))

    def set_stats(self, mean: torch.Tensor, std: torch.Tensor):
        mean = mean.detach()
        std = std.detach().clamp_min(self.eps)
        with torch.no_grad():
            self.mean.copy_(mean)
            self.invstd.copy_(1.0 / std)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return (x - self.mean) * self.invstd


class ResidualMLP(nn.Module):
    def __init__(self, input_dim: int, hidden: int, num_classes: int, dropout: float = 0.1, use_feature_norm: bool = True):
        super().__init__()
        self.use_feature_norm = use_feature_norm
        if use_feature_norm:
            self.feat_norm = FeatureStandardize(input_dim)
        self.ln1 = nn.LayerNorm(input_dim)
        self.fc1 = nn.Linear(input_dim, hidden, bias=True)
        self.ln2 = nn.LayerNorm(hidden)
        self.fc2 = nn.Linear(hidden, input_dim, bias=True)
        self.ln3 = nn.LayerNorm(input_dim)
        self.head = nn.Linear(input_dim, num_classes, bias=True)
        self.act = nn.GELU()
        self.drop1 = nn.Dropout(p=dropout)
        self.drop2 = nn.Dropout(p=dropout)

    def set_feature_stats(self, mean: torch.Tensor, std: torch.Tensor):
        if self.use_feature_norm:
            self.feat_norm.set_stats(mean, std)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        if self.use_feature_norm:
            x = self.feat_norm(x)
        y = self.fc1(self.ln1(x))
        y = self.act(y)
        y = self.drop1(y)
        y = self.fc2(self.ln2(y))
        y = self.drop2(y)
        x = x + y
        out = self.head(self.ln3(x))
        return out


class LabelSmoothingCrossEntropy(nn.Module):
    def __init__(self, smoothing: float = 0.05):
        super().__init__()
        self.smoothing = smoothing

    def forward(self, logits: torch.Tensor, target: torch.Tensor) -> torch.Tensor:
        log_probs = F.log_softmax(logits, dim=-1)
        n_classes = logits.size(-1)
        nll = -log_probs.gather(dim=-1, index=target.unsqueeze(1)).squeeze(1)
        smooth_loss = -log_probs.mean(dim=-1)
        loss = (1.0 - self.smoothing) * nll + self.smoothing * smooth_loss
        return loss.mean()


def compute_feature_stats(loader, input_dim: int, device: torch.device) -> (torch.Tensor, torch.Tensor):
    total = 0
    sum_ = torch.zeros(input_dim, dtype=torch.float64)
    sumsq = torch.zeros(input_dim, dtype=torch.float64)
    with torch.no_grad():
        for inputs, _ in loader:
            x = inputs.to("cpu", dtype=torch.float32)
            sum_ += x.sum(dim=0, dtype=torch.float64)
            sumsq += (x.double() * x.double()).sum(dim=0)
            total += x.size(0)
    if total == 0:
        mean = torch.zeros(input_dim, dtype=torch.float32)
        std = torch.ones(input_dim, dtype=torch.float32)
    else:
        mean = (sum_ / total).to(torch.float32)
        var = (sumsq / total) - (mean.double() * mean.double())
        var = torch.clamp(var, min=1e-6)
        std = torch.sqrt(var).to(torch.float32)
    return mean, std


def adjust_learning_rate(optimizer, base_lr: float, epoch: int, total_epochs: int, warmup_epochs: int = 5, min_lr_ratio: float = 0.05):
    if epoch < warmup_epochs:
        lr = base_lr * float(epoch + 1) / float(max(1, warmup_epochs))
    else:
        t = (epoch - warmup_epochs) / float(max(1, total_epochs - warmup_epochs))
        cos = 0.5 * (1.0 + math.cos(math.pi * t))
        lr = min_lr_ratio * base_lr + (base_lr - min_lr_ratio * base_lr) * cos
    for pg in optimizer.param_groups:
        pg["lr"] = lr


def mixup_data(x: torch.Tensor, y: torch.Tensor, alpha: float = 0.2):
    if alpha <= 0.0:
        return x, y, None, 1.0
    beta = torch.distributions.Beta(alpha, alpha)
    lam = beta.sample().item()
    lam = max(lam, 1.0 - lam)
    index = torch.randperm(x.size(0), device=x.device)
    mixed_x = lam * x + (1.0 - lam) * x[index]
    y_a, y_b = y, y[index]
    return mixed_x, y_a, y_b, lam


def validate(model: nn.Module, loader, device: torch.device) -> float:
    model.eval()
    correct = 0
    total = 0
    with torch.no_grad():
        for inputs, targets in loader:
            inputs = inputs.to(device=device, dtype=torch.float32)
            targets = targets.to(device=device, dtype=torch.long)
            outputs = model(inputs)
            preds = outputs.argmax(dim=1)
            correct += (preds == targets).sum().item()
            total += targets.numel()
    acc = correct / total if total > 0 else 0.0
    return acc


def calc_params_for_arch(input_dim: int, hidden: int, num_classes: int) -> int:
    # Architecture: LN(in), FC(in->hidden), LN(hidden), FC(hidden->in), LN(in), FC(in->num_classes)
    # Params:
    # FC1: in*hidden + hidden
    # FC2: hidden*in + in
    # FC3: in*num_classes + num_classes
    # LN1(in): 2*in
    # LN2(hidden): 2*hidden
    # LN3(in): 2*in
    return (
        input_dim * hidden + hidden +
        hidden * input_dim + input_dim +
        input_dim * num_classes + num_classes +
        2 * input_dim + 2 * hidden + 2 * input_dim
    )


class Solution:
    def solve(self, train_loader, val_loader, metadata: dict = None) -> torch.nn.Module:
        set_seed(42)

        if metadata is None:
            metadata = {}
        input_dim = int(metadata.get("input_dim", 384))
        num_classes = int(metadata.get("num_classes", 128))
        param_limit = int(metadata.get("param_limit", 500000))
        device_str = metadata.get("device", "cpu")
        device = torch.device(device_str)

        # Compute feature normalization stats
        mean, std = compute_feature_stats(train_loader, input_dim, device)

        # Choose the largest hidden size under the param limit for the architecture
        # Solve: params = 2*in*hidden + in*num_classes + other_terms <= param_limit
        # Using exact calculation helper
        # Start from theoretical upper bound, then decrement until valid
        # Use safe start: compute from closed form for our chosen design
        const_terms = input_dim * num_classes + num_classes + 4 * input_dim  # FC3 + LN1+LN3 + FC2 bias
        # This is only a heuristic start; we'll still check with exact calc
        # Use exact bound derived earlier:
        # params = 771*h + 51200 for in=384, classes=128 (but generalize with calc helper)
        # We will binary search for hidden
        lo, hi = 16, 2048
        best_h = 16
        while lo <= hi:
            mid = (lo + hi) // 2
            p = calc_params_for_arch(input_dim, mid, num_classes)
            if p <= param_limit:
                best_h = mid
                lo = mid + 1
            else:
                hi = mid - 1

        hidden = best_h

        model = ResidualMLP(input_dim=input_dim, hidden=hidden, num_classes=num_classes, dropout=0.1, use_feature_norm=True)
        model.set_feature_stats(mean, std)
        model.to(device)

        # Safety check: ensure param count under limit; otherwise decrement hidden until it fits
        param_count = count_trainable_params(model)
        while param_count > param_limit and hidden > 16:
            hidden -= 1
            model = ResidualMLP(input_dim=input_dim, hidden=hidden, num_classes=num_classes, dropout=0.1, use_feature_norm=True)
            model.set_feature_stats(mean, std)
            model.to(device)
            param_count = count_trainable_params(model)

        # Training setup
        lr = 3e-3
        weight_decay = 2e-4
        smoothing = 0.06
        epochs = 240
        warmup_epochs = 6
        patience = 50
        mixup_alpha = 0.2
        mixup_epochs = epochs // 2  # apply mixup in first half

        optimizer = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=weight_decay)
        criterion = LabelSmoothingCrossEntropy(smoothing=smoothing)

        best_val_acc = 0.0
        best_state = None
        no_improve = 0

        for epoch in range(epochs):
            adjust_learning_rate(optimizer, lr, epoch, epochs, warmup_epochs=warmup_epochs, min_lr_ratio=0.05)
            model.train()
            running_loss = 0.0
            total_batches = 0
            for inputs, targets in train_loader:
                inputs = inputs.to(device=device, dtype=torch.float32)
                targets = targets.to(device=device, dtype=torch.long)

                use_mixup = (mixup_alpha > 0.0) and (epoch < mixup_epochs) and (inputs.size(0) > 1)
                if use_mixup:
                    inputs, y_a, y_b, lam = mixup_data(inputs, targets, alpha=mixup_alpha)

                optimizer.zero_grad()
                outputs = model(inputs)
                if use_mixup:
                    loss = lam * criterion(outputs, y_a) + (1.0 - lam) * criterion(outputs, y_b)
                else:
                    loss = criterion(outputs, targets)
                loss.backward()
                torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
                optimizer.step()

                running_loss += loss.item()
                total_batches += 1

            # Validation
            val_acc = validate(model, val_loader, device)

            if val_acc > best_val_acc + 1e-6:
                best_val_acc = val_acc
                best_state = copy.deepcopy(model.state_dict())
                no_improve = 0
            else:
                no_improve += 1
                if no_improve >= patience:
                    break

        if best_state is not None:
            model.load_state_dict(best_state)

        model.eval()
        return model
