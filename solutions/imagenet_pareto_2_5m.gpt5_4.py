import math
import random
import torch
import torch.nn as nn
import torch.nn.functional as F


def set_seed(seed=42):
    random.seed(seed)
    torch.manual_seed(seed)


class DropPath(nn.Module):
    def __init__(self, drop_prob: float = 0.0):
        super().__init__()
        self.drop_prob = float(drop_prob)

    def forward(self, x):
        if self.drop_prob == 0.0 or not self.training:
            return x
        keep_prob = 1.0 - self.drop_prob
        shape = (x.shape[0],) + (1,) * (x.ndim - 1)
        random_tensor = x.new_empty(shape).bernoulli_(keep_prob)
        output = x / keep_prob * random_tensor
        return output


class SwiGLUBlock(nn.Module):
    def __init__(self, dim, expansion=1, dropout=0.0, drop_path=0.0, layerscale_init=1e-4):
        super().__init__()
        hidden = expansion * dim
        self.norm = nn.LayerNorm(dim)
        self.fc1 = nn.Linear(dim, 2 * hidden, bias=True)
        self.fc2 = nn.Linear(hidden, dim, bias=True)
        self.drop1 = nn.Dropout(dropout)
        self.drop2 = nn.Dropout(dropout)
        self.drop_path = DropPath(drop_path) if drop_path > 0.0 else nn.Identity()
        if layerscale_init is not None and layerscale_init > 0.0:
            self.gamma = nn.Parameter(layerscale_init * torch.ones(dim))
        else:
            self.gamma = None

    def forward(self, x):
        y = self.norm(x)
        y = self.fc1(y)
        a, b = y.chunk(2, dim=-1)
        y = F.silu(a) * b
        y = self.drop1(y)
        y = self.fc2(y)
        y = self.drop2(y)
        if self.gamma is not None:
            y = y * self.gamma
        y = self.drop_path(y)
        return x + y


class MLPClassifier(nn.Module):
    def __init__(self, input_dim, num_classes, num_blocks=5, expansion=1, dropout=0.1, drop_path_rate=0.05):
        super().__init__()
        self.dim = input_dim
        dpr = [x.item() for x in torch.linspace(0, drop_path_rate, num_blocks)]
        blocks = []
        for i in range(num_blocks):
            blocks.append(SwiGLUBlock(input_dim, expansion=expansion, dropout=dropout, drop_path=dpr[i], layerscale_init=1e-4))
        self.blocks = nn.Sequential(*blocks)
        self.norm_final = nn.LayerNorm(input_dim)
        self.head = nn.Linear(input_dim, num_classes, bias=True)

    def forward(self, x):
        x = self.blocks(x)
        x = self.norm_final(x)
        x = self.head(x)
        return x


def count_params(model: nn.Module):
    return sum(p.numel() for p in model.parameters() if p.requires_grad)


def build_model_under_limit(input_dim, num_classes, param_limit, start_blocks=6, expansion=1, dropout=0.1, drop_path_rate=0.05):
    # Try from start_blocks down to 1 to fit limit
    blocks = start_blocks
    best_model = None
    while blocks >= 1:
        model = MLPClassifier(input_dim, num_classes, num_blocks=blocks, expansion=expansion, dropout=dropout, drop_path_rate=drop_path_rate)
        params = count_params(model)
        if params <= param_limit:
            best_model = model
            break
        blocks -= 1
    if best_model is None:
        # As a fallback, build a very small model
        best_model = MLPClassifier(input_dim, num_classes, num_blocks=1, expansion=1, dropout=0.0, drop_path_rate=0.0)
    return best_model


def param_groups_weight_decay(model: nn.Module, weight_decay: float = 0.05):
    decay = []
    no_decay = []
    for name, param in model.named_parameters():
        if not param.requires_grad:
            continue
        if len(param.shape) == 1 or name.endswith(".bias") or "norm" in name.lower() or "ln" in name.lower() or "layerscale" in name.lower():
            no_decay.append(param)
        else:
            decay.append(param)
    return [
        {"params": decay, "weight_decay": weight_decay},
        {"params": no_decay, "weight_decay": 0.0},
    ]


def evaluate(model, loader, device):
    model.eval()
    correct = 0
    total = 0
    with torch.no_grad():
        for inputs, targets in loader:
            inputs = inputs.to(device)
            targets = targets.to(device)
            outputs = model(inputs)
            preds = outputs.argmax(dim=1)
            correct += (preds == targets).sum().item()
            total += targets.numel()
    acc = correct / total if total > 0 else 0.0
    return acc


class Solution:
    def solve(self, train_loader, val_loader, metadata: dict = None) -> torch.nn.Module:
        set_seed(42)
        device = metadata.get("device", "cpu") if metadata is not None else "cpu"
        input_dim = metadata.get("input_dim", 384)
        num_classes = metadata.get("num_classes", 128)
        param_limit = metadata.get("param_limit", 2_500_000)

        # Build model near the limit
        # Start from 6 blocks; the logic will reduce to fit the hard limit
        model = build_model_under_limit(
            input_dim=input_dim,
            num_classes=num_classes,
            param_limit=param_limit,
            start_blocks=6,
            expansion=1,
            dropout=0.1,
            drop_path_rate=0.05,
        )
        model.to(device)

        # Double-check parameter constraint
        params = count_params(model)
        if params > param_limit:
            # As a last resort, reduce the number of blocks to minimum
            model = build_model_under_limit(
                input_dim=input_dim,
                num_classes=num_classes,
                param_limit=param_limit,
                start_blocks=3,
                expansion=1,
                dropout=0.0,
                drop_path_rate=0.0,
            )
            model.to(device)

        # Training setup
        epochs = 200
        steps_per_epoch = max(1, len(train_loader))
        # Use slightly conservative LR for stability
        base_lr = 3e-3
        wd = 0.05
        criterion = nn.CrossEntropyLoss(label_smoothing=0.05)

        optimizer = torch.optim.AdamW(param_groups_weight_decay(model, wd), lr=base_lr, betas=(0.9, 0.999))
        scheduler = torch.optim.lr_scheduler.OneCycleLR(
            optimizer,
            max_lr=base_lr,
            epochs=epochs,
            steps_per_epoch=steps_per_epoch,
            pct_start=0.15,
            anneal_strategy="cos",
            div_factor=10.0,
            final_div_factor=1000.0,
        )

        best_acc = 0.0
        best_state = None
        patience = 40
        no_improve = 0

        for epoch in range(epochs):
            model.train()
            for inputs, targets in train_loader:
                inputs = inputs.to(device)
                targets = targets.to(device)

                optimizer.zero_grad(set_to_none=True)
                outputs = model(inputs)
                loss = criterion(outputs, targets)
                loss.backward()
                torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=2.0)
                optimizer.step()
                scheduler.step()

            # Validation
            val_acc = evaluate(model, val_loader, device)

            if val_acc > best_acc:
                best_acc = val_acc
                best_state = {k: v.cpu().clone() for k, v in model.state_dict().items()}
                no_improve = 0
            else:
                no_improve += 1
                if no_improve >= patience:
                    break

        if best_state is not None:
            model.load_state_dict(best_state, strict=True)
        model.eval()
        return model
