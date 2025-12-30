import math
import random
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F


def set_seed(seed: int = 1337):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)


class InputStandardizer(nn.Module):
    def __init__(self, mean: torch.Tensor, std: torch.Tensor):
        super().__init__()
        self.register_buffer("mean", mean.clone().detach())
        inv_std = 1.0 / torch.clamp(std.clone().detach(), min=1e-6)
        self.register_buffer("inv_std", inv_std)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return (x - self.mean) * self.inv_std


class ResMLPBlock(nn.Module):
    def __init__(self, width: int, dropout: float = 0.1):
        super().__init__()
        self.norm = nn.LayerNorm(width)
        self.fc1 = nn.Linear(width, width)
        self.fc2 = nn.Linear(width, width)
        self.act = nn.GELU()
        self.drop1 = nn.Dropout(dropout)
        self.drop2 = nn.Dropout(dropout)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        h = self.norm(x)
        h = self.fc1(h)
        h = self.act(h)
        h = self.drop1(h)
        h = self.fc2(h)
        h = self.drop2(h)
        return x + h


class ResMLP(nn.Module):
    def __init__(self, input_dim: int, num_classes: int, width: int, num_blocks: int,
                 dropout: float, mean: torch.Tensor, std: torch.Tensor):
        super().__init__()
        self.input_norm = InputStandardizer(mean, std)
        self.inp = nn.Linear(input_dim, width)
        self.act = nn.GELU()
        self.blocks = nn.Sequential(*[ResMLPBlock(width, dropout) for _ in range(num_blocks)])
        self.final_norm = nn.LayerNorm(width)
        self.head = nn.Linear(width, num_classes)
        self.apply(self._init_weights)

    @staticmethod
    def _init_weights(m):
        if isinstance(m, nn.Linear):
            nn.init.kaiming_normal_(m.weight, nonlinearity='relu')
            if m.bias is not None:
                nn.init.zeros_(m.bias)
        elif isinstance(m, nn.LayerNorm):
            nn.init.ones_(m.weight)
            nn.init.zeros_(m.bias)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self.input_norm(x)
        x = self.inp(x)
        x = self.act(x)
        x = self.blocks(x)
        x = self.final_norm(x)
        x = self.head(x)
        return x


def count_trainable_params(model: nn.Module) -> int:
    return sum(p.numel() for p in model.parameters() if p.requires_grad)


def compute_dataset_stats(loader, input_dim: int) -> (torch.Tensor, torch.Tensor):
    n = 0
    sum_x = torch.zeros(input_dim, dtype=torch.float32)
    sum_x2 = torch.zeros(input_dim, dtype=torch.float32)
    for batch in loader:
        x = batch[0].detach().to('cpu', dtype=torch.float32)
        b = x.size(0)
        n += b
        sum_x += x.sum(dim=0)
        sum_x2 += (x * x).sum(dim=0)
    if n == 0:
        mean = torch.zeros(input_dim, dtype=torch.float32)
        std = torch.ones(input_dim, dtype=torch.float32)
        return mean, std
    mean = sum_x / float(n)
    var = (sum_x2 / float(n)) - mean.pow(2)
    std = torch.sqrt(torch.clamp(var, min=1e-6))
    return mean, std


def evaluate(model: nn.Module, loader) -> float:
    model.eval()
    correct = 0
    total = 0
    with torch.no_grad():
        for inputs, targets in loader:
            inputs = inputs.to('cpu', dtype=torch.float32)
            targets = targets.to('cpu', dtype=torch.long)
            outputs = model(inputs)
            preds = outputs.argmax(dim=1)
            correct += (preds == targets).sum().item()
            total += targets.numel()
    if total == 0:
        return 0.0
    return correct / total


def mixup_data(x: torch.Tensor, y: torch.Tensor, alpha: float = 0.2):
    if alpha > 0.0:
        lam = np.random.beta(alpha, alpha)
    else:
        lam = 1.0
    batch_size = x.size(0)
    index = torch.randperm(batch_size)
    mixed_x = lam * x + (1 - lam) * x[index, :]
    y_a, y_b = y, y[index]
    return mixed_x, y_a, y_b, lam


class Solution:
    def solve(self, train_loader, val_loader, metadata: dict = None) -> torch.nn.Module:
        set_seed(1337)

        if metadata is None:
            metadata = {}
        input_dim = int(metadata.get("input_dim", 384))
        num_classes = int(metadata.get("num_classes", 128))
        param_limit = int(metadata.get("param_limit", 5_000_000))
        device = str(metadata.get("device", "cpu"))

        torch.set_num_threads(max(1, torch.get_num_threads()))

        mean, std = compute_dataset_stats(train_loader, input_dim)

        # Architecture search within parameter limit
        target_blocks = 2
        init_width = 1048
        min_width = 512
        step = 8

        best_model = None
        width = init_width
        dropout = 0.15

        while width >= min_width:
            candidate = ResMLP(input_dim, num_classes, width, target_blocks, dropout, mean, std)
            params = count_trainable_params(candidate)
            if params <= param_limit:
                best_model = candidate
                break
            width -= step

        if best_model is None:
            # Fallback small model
            width = 768
            best_model = ResMLP(input_dim, num_classes, width, 1, 0.1, mean, std)

        model = best_model.to(device)

        # Training configuration
        epochs = 180
        steps_per_epoch = max(1, len(train_loader))
        total_steps = epochs * steps_per_epoch

        # Learning rate tuned for CPU training and model size
        max_lr = 0.003 if width >= 960 else 0.004
        weight_decay = 0.01

        optimizer = torch.optim.AdamW(model.parameters(), lr=max_lr, weight_decay=weight_decay)
        scheduler = torch.optim.lr_scheduler.OneCycleLR(
            optimizer,
            max_lr=max_lr,
            epochs=epochs,
            steps_per_epoch=steps_per_epoch,
            pct_start=0.15,
            anneal_strategy='cos'
        )
        criterion = nn.CrossEntropyLoss(label_smoothing=0.05)

        best_val_acc = -1.0
        best_state = None
        patience = 50
        epochs_no_improve = 0

        use_mixup = True
        mixup_alpha = 0.2
        mixup_disable_epoch = int(epochs * 0.75)

        for epoch in range(epochs):
            model.train()
            for inputs, targets in train_loader:
                inputs = inputs.to(device, dtype=torch.float32)
                targets = targets.to(device, dtype=torch.long)

                if use_mixup and epoch < mixup_disable_epoch and inputs.size(0) > 1:
                    mixed_x, y_a, y_b, lam = mixup_data(inputs, targets, mixup_alpha)
                    outputs = model(mixed_x)
                    loss = lam * criterion(outputs, y_a) + (1.0 - lam) * criterion(outputs, y_b)
                else:
                    outputs = model(inputs)
                    loss = criterion(outputs, targets)

                optimizer.zero_grad()
                loss.backward()
                torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
                optimizer.step()
                scheduler.step()

            # Validation
            val_acc = evaluate(model, val_loader)

            if val_acc > best_val_acc:
                best_val_acc = val_acc
                best_state = {k: v.cpu().clone() for k, v in model.state_dict().items()}
                epochs_no_improve = 0
            else:
                epochs_no_improve += 1

            if epochs_no_improve >= patience:
                break

        if best_state is not None:
            model.load_state_dict(best_state, strict=True)

        model.to('cpu')
        model.eval()
        return model