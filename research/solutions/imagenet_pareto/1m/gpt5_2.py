import math
import time
import random
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F


def count_parameters(model: nn.Module) -> int:
    return sum(p.numel() for p in model.parameters() if p.requires_grad)


class MLPResBlock(nn.Module):
    def __init__(self, dim: int, hidden_mult: float = 2.0, dropout: float = 0.1, activation: str = "gelu"):
        super().__init__()
        self.norm = nn.LayerNorm(dim)
        hidden_dim = int(dim * hidden_mult)
        self.fc1 = nn.Linear(dim, hidden_dim)
        self.fc2 = nn.Linear(hidden_dim, dim)
        self.drop1 = nn.Dropout(dropout)
        self.drop2 = nn.Dropout(dropout)
        if activation == "relu":
            self.act = nn.ReLU(inplace=True)
        elif activation == "silu":
            self.act = nn.SiLU(inplace=True)
        else:
            self.act = nn.GELU()

    def forward(self, x):
        y = self.norm(x)
        y = self.fc1(y)
        y = self.act(y)
        y = self.drop1(y)
        y = self.fc2(y)
        y = self.drop2(y)
        return x + y


class MLPNet(nn.Module):
    def __init__(self, in_dim: int, num_classes: int, dim: int = 320, num_blocks: int = 2, hidden_mult: float = 2.0, dropout: float = 0.1):
        super().__init__()
        self.in_dim = in_dim
        self.dim = dim
        if in_dim != dim:
            self.proj = nn.Linear(in_dim, dim)
        else:
            self.proj = nn.Identity()
        blocks = []
        for _ in range(num_blocks):
            blocks.append(MLPResBlock(dim, hidden_mult=hidden_mult, dropout=dropout, activation="gelu"))
        self.blocks = nn.Sequential(*blocks)
        self.norm_final = nn.LayerNorm(dim)
        self.head = nn.Linear(dim, num_classes)

    def forward(self, x):
        x = self.proj(x)
        x = self.blocks(x)
        x = self.norm_final(x)
        x = self.head(x)
        return x


def evaluate_accuracy(model: nn.Module, loader, device: torch.device) -> float:
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
    return correct / total if total > 0 else 0.0


def mixup_data(x, y, alpha: float):
    if alpha <= 0.0 or x.size(0) < 2:
        return x, y, y, 1.0
    lam = np.random.beta(alpha, alpha)
    index = torch.randperm(x.size(0), device=x.device)
    mixed_x = lam * x + (1 - lam) * x[index, :]
    y_a, y_b = y, y[index]
    return mixed_x, y_a, y_b, float(lam)


class Solution:
    def solve(self, train_loader, val_loader, metadata: dict = None) -> torch.nn.Module:
        if metadata is None:
            metadata = {}
        input_dim = int(metadata.get("input_dim", 384))
        num_classes = int(metadata.get("num_classes", 128))
        param_limit = int(metadata.get("param_limit", 1_000_000))
        device_str = metadata.get("device", "cpu")
        device = torch.device(device_str if torch.cuda.is_available() and device_str != "cpu" else "cpu")
        train_samples = int(metadata.get("train_samples", 2048))
        # Choose architecture under param budget
        # Prefer deeper (2 blocks) with width as large as possible
        chosen_model = None
        chosen_dim = None
        chosen_blocks = None

        def build_and_check(dim: int, blocks: int, dropout: float):
            model = MLPNet(in_dim=input_dim, num_classes=num_classes, dim=dim, num_blocks=blocks, hidden_mult=2.0, dropout=dropout)
            return model, count_parameters(model)

        # Search strategy: try 2 blocks with descending dims; then 1 block
        dims_list = [512, 480, 448, 432, 416, 400, 384, 368, 352, 336, 320, 304, 288, 272, 256, 240, 224, 208, 192]
        found = False
        for blocks in [3, 2, 1]:
            for dim in dims_list:
                # Use modest dropout; more dropout when dim smaller to regularize less capacity
                dropout = 0.12 if dim >= 320 else 0.15
                model, params = build_and_check(dim, blocks, dropout)
                if params <= param_limit:
                    chosen_model = model
                    chosen_dim = dim
                    chosen_blocks = blocks
                    found = True
                    break
            if found:
                break

        if chosen_model is None:
            # Fallback minimal model
            chosen_model = nn.Sequential(
                nn.Linear(input_dim, 512),
                nn.ReLU(),
                nn.Linear(512, num_classes),
            )

        model = chosen_model.to(device)

        # Training setup
        # Hyperparameters
        epochs = 160 if train_samples <= 4096 else 120
        lr_max = 0.003 if chosen_dim is None or chosen_dim >= 320 else 0.004
        weight_decay = 5e-4
        label_smoothing = 0.05
        grad_clip = 1.0
        use_mixup = True
        mixup_alpha = 0.2
        mixup_prob = 0.6

        optimizer = torch.optim.AdamW(model.parameters(), lr=lr_max, weight_decay=weight_decay)
        steps_per_epoch = max(1, len(train_loader))
        scheduler = torch.optim.lr_scheduler.OneCycleLR(
            optimizer,
            max_lr=lr_max,
            epochs=epochs,
            steps_per_epoch=steps_per_epoch,
            pct_start=0.15,
            anneal_strategy='cos',
            div_factor=20.0,
            final_div_factor=1000.0,
        )
        criterion = nn.CrossEntropyLoss(label_smoothing=label_smoothing)

        # Early stopping and checkpointing
        best_val_acc = -1.0
        best_state = None
        patience = 25
        epochs_no_improve = 0

        # Seed for reproducibility
        torch.manual_seed(1337)
        random.seed(1337)
        np.random.seed(1337)

        start_time = time.time()
        time_limit = 3400.0  # seconds, to be safe under 1 hour total

        for epoch in range(epochs):
            model.train()
            for inputs, targets in train_loader:
                inputs = inputs.to(device)
                targets = targets.to(device)

                if use_mixup and (epoch < int(0.75 * epochs)) and (random.random() < mixup_prob):
                    mixed_x, y_a, y_b, lam = mixup_data(inputs, targets, alpha=mixup_alpha)
                    outputs = model(mixed_x)
                    loss = lam * criterion(outputs, y_a) + (1.0 - lam) * criterion(outputs, y_b)
                else:
                    outputs = model(inputs)
                    loss = criterion(outputs, targets)

                optimizer.zero_grad(set_to_none=True)
                loss.backward()
                if grad_clip is not None and grad_clip > 0:
                    nn.utils.clip_grad_norm_(model.parameters(), grad_clip)
                optimizer.step()
                scheduler.step()

                if (time.time() - start_time) > time_limit:
                    break

            # Validation
            val_acc = evaluate_accuracy(model, val_loader, device)
            if val_acc > best_val_acc:
                best_val_acc = val_acc
                best_state = {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}
                epochs_no_improve = 0
            else:
                epochs_no_improve += 1

            if epochs_no_improve >= patience or (time.time() - start_time) > time_limit:
                break

        # Load best weights
        if best_state is not None:
            model.load_state_dict(best_state)

        # Ensure model on CPU for evaluator if device was something else
        model.to(torch.device("cpu"))
        model.eval()
        return model