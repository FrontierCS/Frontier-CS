import math
import random
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F


def set_seed(seed: int = 42):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)


def count_trainable_parameters(model: nn.Module) -> int:
    return sum(p.numel() for p in model.parameters() if p.requires_grad)


class ResidualBlock(nn.Module):
    def __init__(self, dim: int, dropout: float = 0.2, res_scale: float = 0.5):
        super().__init__()
        self.bn1 = nn.BatchNorm1d(dim)
        self.bn2 = nn.BatchNorm1d(dim)
        self.act = nn.GELU()
        self.fc1 = nn.Linear(dim, dim)
        self.fc2 = nn.Linear(dim, dim)
        self.dropout = nn.Dropout(dropout)
        self.res_scale = res_scale

    def forward(self, x):
        out = self.bn1(x)
        out = self.act(out)
        out = self.fc1(out)
        out = self.dropout(out)
        out = self.bn2(out)
        out = self.act(out)
        out = self.fc2(out)
        out = self.dropout(out)
        return x + self.res_scale * out


class TinyResMLP(nn.Module):
    def __init__(self, input_dim: int, num_classes: int, p_drop: float = 0.2):
        super().__init__()
        self.in_norm = nn.LayerNorm(input_dim)
        self.fc1 = nn.Linear(input_dim, 512)
        self.bn1 = nn.BatchNorm1d(512)
        self.fc2 = nn.Linear(512, 256)
        self.bn2 = nn.BatchNorm1d(256)
        self.act = nn.GELU()
        self.drop = nn.Dropout(p_drop)
        self.block = ResidualBlock(256, dropout=p_drop, res_scale=0.5)
        self.classifier = nn.Linear(256, num_classes)

    def forward(self, x):
        x = self.in_norm(x)
        x = self.fc1(x)
        x = self.bn1(x)
        x = self.act(x)
        x = self.drop(x)
        x = self.fc2(x)
        x = self.bn2(x)
        x = self.act(x)
        x = self.drop(x)
        x = self.block(x)
        x = self.drop(x)
        logits = self.classifier(x)
        return logits


class EMA:
    def __init__(self, model: nn.Module, decay: float = 0.999):
        self.decay = decay
        self.shadow = {}
        self.collected = None
        for name, param in model.named_parameters():
            if param.requires_grad:
                self.shadow[name] = param.detach().clone()

    def update(self, model: nn.Module):
        for name, param in model.named_parameters():
            if not param.requires_grad:
                continue
            assert name in self.shadow
            new_average = (1.0 - self.decay) * param.detach() + self.decay * self.shadow[name]
            self.shadow[name] = new_average.clone()

    def store(self, model: nn.Module):
        self.collected = {}
        for name, param in model.named_parameters():
            if param.requires_grad:
                self.collected[name] = param.detach().clone()

    def copy_to(self, model: nn.Module):
        for name, param in model.named_parameters():
            if param.requires_grad:
                param.data.copy_(self.shadow[name].data)

    def restore(self, model: nn.Module):
        if self.collected is None:
            return
        for name, param in model.named_parameters():
            if param.requires_grad:
                param.data.copy_(self.collected[name].data)
        self.collected = None

    def get_shadow_state(self):
        return {k: v.detach().clone() for k, v in self.shadow.items()}

    def load_shadow_state(self, state_dict: dict):
        for k, v in state_dict.items():
            self.shadow[k] = v.detach().clone()


def get_cosine_schedule_with_warmup(optimizer, num_warmup_steps, num_training_steps, min_lr_ratio=0.05):
    def lr_lambda(current_step: int):
        if current_step < num_warmup_steps:
            return float(current_step) / float(max(1, num_warmup_steps))
        progress = float(current_step - num_warmup_steps) / float(max(1, num_training_steps - num_warmup_steps))
        cosine = 0.5 * (1.0 + math.cos(math.pi * progress))
        return min_lr_ratio + (1.0 - min_lr_ratio) * cosine

    return torch.optim.lr_scheduler.LambdaLR(optimizer, lr_lambda)


def evaluate(model: nn.Module, data_loader, device: torch.device):
    model.eval()
    correct = 0
    total = 0
    loss_sum = 0.0
    criterion = nn.CrossEntropyLoss()
    with torch.no_grad():
        for inputs, targets in data_loader:
            inputs = inputs.to(device, non_blocking=False).float()
            targets = targets.to(device, non_blocking=False).long()
            outputs = model(inputs)
            loss = criterion(outputs, targets)
            loss_sum += loss.item() * targets.size(0)
            preds = outputs.argmax(dim=1)
            correct += (preds == targets).sum().item()
            total += targets.numel()
    acc = correct / max(1, total)
    avg_loss = loss_sum / max(1, total)
    return acc, avg_loss


class Solution:
    def solve(self, train_loader, val_loader, metadata: dict = None) -> torch.nn.Module:
        set_seed(42)
        input_dim = int(metadata.get("input_dim", 384))
        num_classes = int(metadata.get("num_classes", 128))
        device_str = metadata.get("device", "cpu")
        device = torch.device(device_str)
        param_limit = int(metadata.get("param_limit", 500000))

        model = TinyResMLP(input_dim=input_dim, num_classes=num_classes, p_drop=0.2)
        model.to(device)

        # Ensure parameter constraint
        param_count = count_trainable_parameters(model)
        if param_count > param_limit:
            # Fallback to narrower configuration if needed
            # Narrow residual block to 224 and hidden1 to 448 to reduce params
            class NarrowResMLP(nn.Module):
                def __init__(self, input_dim: int, num_classes: int, p_drop: float = 0.2):
                    super().__init__()
                    self.in_norm = nn.LayerNorm(input_dim)
                    self.fc1 = nn.Linear(input_dim, 448)
                    self.bn1 = nn.BatchNorm1d(448)
                    self.fc2 = nn.Linear(448, 224)
                    self.bn2 = nn.BatchNorm1d(224)
                    self.act = nn.GELU()
                    self.drop = nn.Dropout(p_drop)
                    self.block = ResidualBlock(224, dropout=p_drop, res_scale=0.5)
                    self.classifier = nn.Linear(224, num_classes)

                def forward(self, x):
                    x = self.in_norm(x)
                    x = self.fc1(x)
                    x = self.bn1(x)
                    x = self.act(x)
                    x = self.drop(x)
                    x = self.fc2(x)
                    x = self.bn2(x)
                    x = self.act(x)
                    x = self.drop(x)
                    x = self.block(x)
                    x = self.drop(x)
                    logits = self.classifier(x)
                    return logits

            model = NarrowResMLP(input_dim=input_dim, num_classes=num_classes, p_drop=0.2).to(device)
            param_count = count_trainable_parameters(model)
            if param_count > param_limit:
                # Final safe fallback: very compact MLP
                model = nn.Sequential(
                    nn.LayerNorm(input_dim),
                    nn.Linear(input_dim, 384),
                    nn.ReLU(),
                    nn.Dropout(0.15),
                    nn.Linear(384, 256),
                    nn.ReLU(),
                    nn.Dropout(0.15),
                    nn.Linear(256, num_classes),
                ).to(device)
                # No further checks; this will certainly be under the limit

        # Training setup
        base_lr = 0.002
        weight_decay = 0.02
        max_epochs = 200
        if isinstance(metadata, dict):
            train_samples = int(metadata.get("train_samples", 2048))
            if train_samples <= 2048:
                max_epochs = 220
            elif train_samples <= 8192:
                max_epochs = 160
            else:
                max_epochs = 120

        optimizer = torch.optim.AdamW(model.parameters(), lr=base_lr, weight_decay=weight_decay, betas=(0.9, 0.999))
        steps_per_epoch = max(1, len(train_loader))
        total_steps = max_epochs * steps_per_epoch
        warmup_steps = max(10, int(0.1 * total_steps))
        scheduler = get_cosine_schedule_with_warmup(optimizer, num_warmup_steps=warmup_steps, num_training_steps=total_steps, min_lr_ratio=0.05)
        criterion = nn.CrossEntropyLoss(label_smoothing=0.05)

        ema = EMA(model, decay=0.999)
        best_acc = -1.0
        best_ema_shadow = ema.get_shadow_state()
        patience = 30
        epochs_no_improve = 0

        for epoch in range(max_epochs):
            model.train()
            for inputs, targets in train_loader:
                inputs = inputs.to(device, non_blocking=False).float()
                targets = targets.to(device, non_blocking=False).long()

                optimizer.zero_grad(set_to_none=True)
                outputs = model(inputs)
                loss = criterion(outputs, targets)
                loss.backward()
                torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
                optimizer.step()
                ema.update(model)
                scheduler.step()

            # Validate using EMA weights
            ema.store(model)
            ema.copy_to(model)
            val_acc, _ = evaluate(model, val_loader, device)
            ema.restore(model)

            if val_acc > best_acc:
                best_acc = val_acc
                best_ema_shadow = ema.get_shadow_state()
                epochs_no_improve = 0
            else:
                epochs_no_improve += 1

            if epochs_no_improve >= patience:
                break

        # Load best EMA weights into model for final evaluation
        for name, param in model.named_parameters():
            if param.requires_grad and name in best_ema_shadow:
                param.data.copy_(best_ema_shadow[name].data)

        model.eval()
        return model