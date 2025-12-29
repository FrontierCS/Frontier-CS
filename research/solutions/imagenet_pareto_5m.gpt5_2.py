import math
import copy
import torch
import torch.nn as nn
import torch.optim as optim


class Standardize(nn.Module):
    def __init__(self, mean: torch.Tensor, std: torch.Tensor, eps: float = 1e-6):
        super().__init__()
        mean = mean.float()
        std = std.float().clamp_min(eps)
        invstd = 1.0 / std
        self.register_buffer("mean", mean)
        self.register_buffer("invstd", invstd)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return (x - self.mean) * self.invstd


class DropPath(nn.Module):
    def __init__(self, drop_prob: float = 0.0):
        super().__init__()
        self.drop_prob = float(drop_prob)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        if not self.training or self.drop_prob == 0.0:
            return x
        keep_prob = 1.0 - self.drop_prob
        shape = (x.shape[0],) + (1,) * (x.ndim - 1)
        random_tensor = x.new_empty(shape).bernoulli_(keep_prob)
        random_tensor.div_(keep_prob)
        return x * random_tensor


class BottleneckResidual(nn.Module):
    def __init__(self, dim: int, bottleneck_ratio: float = 0.25, dropout: float = 0.1, drop_path: float = 0.0,
                 activation: str = "silu", layerscale_init: float = 1e-3):
        super().__init__()
        hidden = max(4, int(dim * bottleneck_ratio))
        self.norm = nn.LayerNorm(dim)
        self.fc1 = nn.Linear(dim, hidden)
        self.fc2 = nn.Linear(hidden, dim)
        if activation == "gelu":
            self.act = nn.GELU()
        else:
            self.act = nn.SiLU()
        self.drop1 = nn.Dropout(dropout)
        self.drop2 = nn.Dropout(dropout)
        self.droppath = DropPath(drop_path) if drop_path > 0.0 else nn.Identity()
        if layerscale_init is not None and layerscale_init > 0:
            self.layer_scale = nn.Parameter(torch.ones(dim) * layerscale_init)
        else:
            self.layer_scale = None

        self.reset_parameters()

    def reset_parameters(self):
        nn.init.kaiming_uniform_(self.fc1.weight, a=math.sqrt(5))
        nn.init.kaiming_uniform_(self.fc2.weight, a=math.sqrt(5))
        if self.fc1.bias is not None:
            fan_in, _ = nn.init._calculate_fan_in_and_fan_out(self.fc1.weight)
            bound = 1 / math.sqrt(fan_in)
            nn.init.uniform_(self.fc1.bias, -bound, bound)
        if self.fc2.bias is not None:
            fan_in, _ = nn.init._calculate_fan_in_and_fan_out(self.fc2.weight)
            bound = 1 / math.sqrt(fan_in)
            nn.init.uniform_(self.fc2.bias, -bound, bound)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        y = self.norm(x)
        y = self.fc1(y)
        y = self.act(y)
        y = self.drop1(y)
        y = self.fc2(y)
        y = self.drop2(y)
        if self.layer_scale is not None:
            y = y * self.layer_scale
        y = self.droppath(y)
        return x + y


class MLPParetoNet(nn.Module):
    def __init__(self, input_dim: int, num_classes: int, width: int = 1024, depth: int = 8,
                 bottleneck_ratio: float = 0.25, dropout: float = 0.1, droppath_rate: float = 0.1,
                 normalizer: nn.Module = None, use_head_norm: bool = True, activation: str = "silu"):
        super().__init__()
        self.normalizer = normalizer
        self.stem = nn.Sequential(
            nn.Linear(input_dim, width),
            nn.GELU(),
            nn.Dropout(dropout)
        )
        blocks = []
        for i in range(depth):
            dp = droppath_rate * (i + 1) / max(1, depth)
            blocks.append(
                BottleneckResidual(
                    dim=width,
                    bottleneck_ratio=bottleneck_ratio,
                    dropout=dropout,
                    drop_path=dp,
                    activation=activation,
                    layerscale_init=1e-2
                )
            )
        self.blocks = nn.Sequential(*blocks)
        self.head_norm = nn.LayerNorm(width) if use_head_norm else nn.Identity()
        self.head = nn.Linear(width, num_classes)

        self._reset_stem_head()

    def _reset_stem_head(self):
        for m in [self.stem[0], self.head]:
            if isinstance(m, nn.Linear):
                nn.init.kaiming_uniform_(m.weight, a=math.sqrt(5))
                if m.bias is not None:
                    fan_in, _ = nn.init._calculate_fan_in_and_fan_out(m.weight)
                    bound = 1 / math.sqrt(fan_in)
                    nn.init.uniform_(m.bias, -bound, bound)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        if self.normalizer is not None:
            x = self.normalizer(x)
        x = self.stem(x)
        x = self.blocks(x)
        x = self.head_norm(x)
        x = self.head(x)
        return x


class ModelEMA:
    def __init__(self, model: nn.Module, decay: float = 0.997):
        self.ema = copy.deepcopy(model).eval()
        for p in self.ema.parameters():
            p.requires_grad_(False)
        self.decay = decay

    @torch.no_grad()
    def update(self, model: nn.Module):
        msd = model.state_dict()
        for k, v in self.ema.state_dict().items():
            m = msd[k]
            if v.dtype.is_floating_point:
                v.mul_(self.decay).add_(m, alpha=1.0 - self.decay)
            else:
                v.copy_(m)


def count_trainable_params(model: nn.Module) -> int:
    return sum(p.numel() for p in model.parameters() if p.requires_grad)


def compute_dataset_stats(loader, device: str = "cpu"):
    # Compute per-feature mean and std
    sum_x = None
    sum_x2 = None
    n = 0
    with torch.no_grad():
        for xb, _ in loader:
            xb = xb.to("cpu", non_blocking=False).float()
            if sum_x is None:
                sum_x = xb.sum(dim=0)
                sum_x2 = (xb * xb).sum(dim=0)
            else:
                sum_x += xb.sum(dim=0)
                sum_x2 += (xb * xb).sum(dim=0)
            n += xb.shape[0]
    mean = sum_x / max(1, n)
    var = (sum_x2 / max(1, n)) - mean.pow(2)
    std = torch.sqrt(torch.clamp(var, min=1e-6))
    mean = mean.to(device)
    std = std.to(device)
    return mean, std


def build_optimizer(model: nn.Module, base_lr: float = 0.002, weight_decay: float = 0.02):
    decay_params = []
    no_decay_params = []
    for name, param in model.named_parameters():
        if not param.requires_grad:
            continue
        if name.endswith("bias") or "norm" in name.lower() or "layer_scale" in name.lower():
            no_decay_params.append(param)
        else:
            no_decay_params.append(param) if param.ndim <= 1 else decay_params.append(param)
    param_groups = [
        {"params": decay_params, "weight_decay": weight_decay},
        {"params": no_decay_params, "weight_decay": 0.0},
    ]
    optimizer = optim.AdamW(param_groups, lr=base_lr, betas=(0.9, 0.999))
    return optimizer


def evaluate(model: nn.Module, loader, device: str = "cpu"):
    model.eval()
    correct = 0
    total = 0
    with torch.no_grad():
        for xb, yb in loader:
            xb = xb.to(device)
            yb = yb.to(device)
            logits = model(xb)
            pred = logits.argmax(dim=1)
            correct += (pred == yb).sum().item()
            total += yb.numel()
    acc = correct / max(1, total)
    return acc


class Solution:
    def solve(self, train_loader, val_loader, metadata: dict = None) -> torch.nn.Module:
        if metadata is None:
            metadata = {}
        device = metadata.get("device", "cpu")
        input_dim = int(metadata.get("input_dim", 384))
        num_classes = int(metadata.get("num_classes", 128))
        param_limit = int(metadata.get("param_limit", 5_000_000))

        torch.manual_seed(1337)
        try:
            import random
            random.seed(1337)
        except Exception:
            pass

        # Compute normalization stats
        mean, std = compute_dataset_stats(train_loader, device=device)
        normalizer = Standardize(mean, std)

        # Select architecture within parameter budget
        width_candidates = [1216, 1152, 1088, 1024, 960, 896, 832, 768, 704, 640, 576, 512]
        depth_candidates = [10, 9, 8, 7, 6, 5]
        chosen_model = None
        chosen_width = None
        chosen_depth = None

        for w in width_candidates:
            for d in depth_candidates:
                model_try = MLPParetoNet(
                    input_dim=input_dim,
                    num_classes=num_classes,
                    width=w,
                    depth=d,
                    bottleneck_ratio=0.25,
                    dropout=0.1,
                    droppath_rate=0.10,
                    normalizer=normalizer,
                    use_head_norm=True,
                    activation="silu",
                ).to(device)
                nparams = count_trainable_params(model_try)
                if nparams <= param_limit:
                    if chosen_model is None:
                        chosen_model = model_try
                        chosen_width = w
                        chosen_depth = d
                    else:
                        # Prefer configuration with param count closest to limit
                        if nparams > count_trainable_params(chosen_model):
                            chosen_model = model_try
                            chosen_width = w
                            chosen_depth = d
                else:
                    del model_try
            if chosen_model is not None:
                break

        if chosen_model is None:
            # Fallback minimal model if above search fails
            chosen_model = MLPParetoNet(
                input_dim=input_dim,
                num_classes=num_classes,
                width=512,
                depth=5,
                bottleneck_ratio=0.25,
                dropout=0.1,
                droppath_rate=0.05,
                normalizer=normalizer,
                use_head_norm=True,
                activation="silu",
            ).to(device)

        model = chosen_model
        param_count = count_trainable_params(model)
        if param_count > param_limit:
            # Ensure under limit by reducing depth if needed
            # This is a last safeguard; reduce depth iteratively
            depth = getattr(model, "blocks").__len__() if hasattr(model, "blocks") else 5
            width = chosen_width if chosen_width is not None else 512
            while param_count > param_limit and depth > 3:
                depth -= 1
                model = MLPParetoNet(
                    input_dim=input_dim,
                    num_classes=num_classes,
                    width=width,
                    depth=depth,
                    bottleneck_ratio=0.25,
                    dropout=0.1,
                    droppath_rate=0.10,
                    normalizer=normalizer,
                    use_head_norm=True,
                    activation="silu",
                ).to(device)
                param_count = count_trainable_params(model)

        # Training settings
        total_train = metadata.get("train_samples", None)
        epochs = 140
        if total_train is not None and total_train < 1500:
            epochs = 160
        elif total_train is not None and total_train > 5000:
            epochs = 120

        criterion = nn.CrossEntropyLoss(label_smoothing=0.05)
        base_lr = 0.0020
        weight_decay = 0.02
        optimizer = build_optimizer(model, base_lr=base_lr, weight_decay=weight_decay)

        warmup_epochs = max(3, min(8, epochs // 10))
        cosine_epochs = max(1, epochs - warmup_epochs)
        scheduler = optim.lr_scheduler.SequentialLR(
            optimizer,
            schedulers=[
                optim.lr_scheduler.LinearLR(optimizer, start_factor=0.2, total_iters=warmup_epochs),
                optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=cosine_epochs, eta_min=base_lr * 0.05),
            ],
            milestones=[warmup_epochs],
        )

        ema = ModelEMA(model, decay=0.997)

        best_acc = 0.0
        best_state = copy.deepcopy(model.state_dict())
        best_ema_acc = 0.0
        best_ema_state = copy.deepcopy(ema.ema.state_dict())
        patience = 28
        no_improve = 0

        def run_eval_models():
            nonlocal best_acc, best_state, best_ema_acc, best_ema_state, no_improve
            # Evaluate base model
            val_acc = evaluate(model, val_loader, device=device)
            if val_acc > best_acc:
                best_acc = val_acc
                best_state = copy.deepcopy(model.state_dict())
                better = True
            else:
                better = False
            # Evaluate EMA model
            ema_acc = evaluate(ema.ema, val_loader, device=device)
            if ema_acc > best_ema_acc:
                best_ema_acc = ema_acc
                best_ema_state = copy.deepcopy(ema.ema.state_dict())
                better = True or better
            if not better:
                no_improve += 1
            else:
                no_improve = 0

        for epoch in range(epochs):
            model.train()
            for xb, yb in train_loader:
                xb = xb.to(device)
                yb = yb.to(device)
                logits = model(xb)
                loss = criterion(logits, yb)
                optimizer.zero_grad(set_to_none=True)
                loss.backward()
                nn.utils.clip_grad_norm_(model.parameters(), max_norm=2.0)
                optimizer.step()
                ema.update(model)

            scheduler.step()
            run_eval_models()
            if no_improve >= patience:
                break

        # Load best among model and EMA by validation accuracy
        # Prefer EMA if it has better validation
        if best_ema_acc >= best_acc:
            model.load_state_dict(best_ema_state, strict=True)
        else:
            model.load_state_dict(best_state, strict=True)

        model.eval()
        return model