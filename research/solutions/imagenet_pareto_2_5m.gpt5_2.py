import math
import os
import random
import torch
import torch.nn as nn
import torch.optim as optim


def set_seed(seed: int = 1337):
    random.seed(seed)
    os.environ["PYTHONHASHSEED"] = str(seed)
    torch.manual_seed(seed)


def count_params(model: nn.Module) -> int:
    return sum(p.numel() for p in model.parameters() if p.requires_grad)


class ResidualBlock(nn.Module):
    def __init__(self, dim: int, dropout: float = 0.1):
        super().__init__()
        self.ln1 = nn.LayerNorm(dim)
        self.fc1 = nn.Linear(dim, dim, bias=True)
        self.act = nn.GELU()
        self.drop1 = nn.Dropout(dropout)
        self.ln2 = nn.LayerNorm(dim)
        self.fc2 = nn.Linear(dim, dim, bias=True)
        self.drop2 = nn.Dropout(dropout)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        h = self.ln1(x)
        h = self.fc1(self.act(h))
        h = self.drop1(h)
        h = self.ln2(h)
        h = self.fc2(self.act(h))
        h = self.drop2(h)
        return x + h


class MLPClassifier(nn.Module):
    def __init__(self, input_dim: int, num_classes: int, width: int, num_blocks: int = 2, dropout: float = 0.1):
        super().__init__()
        self.in_norm = nn.LayerNorm(input_dim)
        self.stem = nn.Linear(input_dim, width)
        blocks = []
        for _ in range(num_blocks):
            blocks.append(ResidualBlock(width, dropout=dropout))
        self.blocks = nn.Sequential(*blocks)
        self.head_norm = nn.LayerNorm(width)
        self.head_drop = nn.Dropout(dropout * 0.5)
        self.head = nn.Linear(width, num_classes)

        self.apply(self._init_weights)

    @staticmethod
    def _init_weights(m):
        if isinstance(m, nn.Linear):
            nn.init.kaiming_uniform_(m.weight, a=math.sqrt(5))
            if m.bias is not None:
                fan_in, _ = nn.init._calculate_fan_in_and_fan_out(m.weight)
                bound = 1 / math.sqrt(fan_in) if fan_in > 0 else 0
                nn.init.uniform_(m.bias, -bound, bound)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self.in_norm(x)
        x = self.stem(x)
        x = self.blocks(x)
        x = self.head_norm(x)
        x = self.head_drop(x)
        x = self.head(x)
        return x


def evaluate(model: nn.Module, loader, device: torch.device):
    model.eval()
    total = 0
    correct = 0
    loss_sum = 0.0
    criterion = nn.CrossEntropyLoss()
    with torch.no_grad():
        for inputs, targets in loader:
            inputs = inputs.to(device)
            targets = targets.to(device)
            outputs = model(inputs)
            loss = criterion(outputs, targets)
            loss_sum += loss.item() * targets.size(0)
            preds = outputs.argmax(dim=1)
            correct += (preds == targets).sum().item()
            total += targets.numel()
    acc = correct / total if total > 0 else 0.0
    avg_loss = loss_sum / total if total > 0 else 0.0
    return acc, avg_loss


class Solution:
    def solve(self, train_loader, val_loader, metadata: dict = None) -> torch.nn.Module:
        set_seed(1337)
        device = torch.device(metadata.get("device", "cpu") if metadata is not None else "cpu")
        torch.set_num_threads(min(8, os.cpu_count() or 8))

        input_dim = int(metadata.get("input_dim", 384))
        num_classes = int(metadata.get("num_classes", 128))
        param_limit = int(metadata.get("param_limit", 2_500_000))

        # Architecture search under parameter limit
        # Start with 2 residual blocks and width target near maximal under limit
        target_blocks = 2
        width = 736  # start high and reduce if needed
        dropout = 0.10

        def build(width_val, blocks_val):
            return MLPClassifier(input_dim, num_classes, width=width_val, num_blocks=blocks_val, dropout=dropout)

        model = build(width, target_blocks)
        pcount = count_params(model)
        while pcount > param_limit:
            width -= 16
            if width < 128:
                if target_blocks > 1:
                    target_blocks -= 1
                    width = 896  # reset width high and re-check
                else:
                    width = 128
                    break
            model = build(width, target_blocks)
            pcount = count_params(model)

        # Safety: ensure within limit
        if pcount > param_limit:
            # Fall back to simpler baseline within limit
            hidden_dim = 768
            while True:
                baseline = nn.Sequential(
                    nn.LayerNorm(input_dim),
                    nn.Linear(input_dim, hidden_dim),
                    nn.GELU(),
                    nn.LayerNorm(hidden_dim),
                    nn.Linear(hidden_dim, hidden_dim),
                    nn.GELU(),
                    nn.LayerNorm(hidden_dim),
                    nn.Linear(hidden_dim, num_classes),
                )
                if count_params(baseline) <= param_limit or hidden_dim <= 256:
                    model = baseline
                    break
                hidden_dim -= 64

        model.to(device)

        # Training setup
        epochs = 140
        patience = 25
        criterion = nn.CrossEntropyLoss(label_smoothing=0.08)
        optimizer = optim.AdamW(model.parameters(), lr=3e-3, weight_decay=0.05)
        steps_per_epoch = max(1, len(train_loader))
        scheduler = optim.lr_scheduler.OneCycleLR(
            optimizer,
            max_lr=3e-3,
            epochs=epochs,
            steps_per_epoch=steps_per_epoch,
            pct_start=0.12,
            anneal_strategy='cos',
            div_factor=10.0,
            final_div_factor=100.0
        )

        best_acc = -1.0
        best_state = None
        no_improve = 0

        val_loader_use = val_loader if val_loader is not None else train_loader

        for epoch in range(epochs):
            model.train()
            for inputs, targets in train_loader:
                inputs = inputs.to(device)
                targets = targets.to(device)

                optimizer.zero_grad(set_to_none=True)
                outputs = model(inputs)
                loss = criterion(outputs, targets)
                loss.backward()
                nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
                optimizer.step()
                scheduler.step()

            val_acc, _ = evaluate(model, val_loader_use, device)
            if val_acc > best_acc:
                best_acc = val_acc
                best_state = {k: v.cpu().clone() for k, v in model.state_dict().items()}
                no_improve = 0
            else:
                no_improve += 1

            if no_improve >= patience:
                break

        if best_state is not None:
            model.load_state_dict(best_state)

        model.to(device)
        model.eval()
        return model