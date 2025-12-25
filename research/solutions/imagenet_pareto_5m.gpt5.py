import math
import copy
import time
import torch
import torch.nn as nn
import torch.nn.functional as F


class Standardize(nn.Module):
    def __init__(self, dim, eps=1e-6):
        super().__init__()
        self.register_buffer("mean", torch.zeros(dim))
        self.register_buffer("std", torch.ones(dim))
        self.eps = eps

    def set_stats(self, mean, std):
        std = std.clone()
        std[std < self.eps] = 1.0
        self.mean.copy_(mean)
        self.std.copy_(std)

    def forward(self, x):
        return (x - self.mean) / self.std


class ResidualLinearBlock(nn.Module):
    def __init__(self, dim, p_drop=0.1, activation="gelu", scale=1.0, use_layernorm=True):
        super().__init__()
        self.use_layernorm = use_layernorm
        if use_layernorm:
            self.norm = nn.LayerNorm(dim)
        else:
            self.norm = nn.BatchNorm1d(dim)
        self.drop1 = nn.Dropout(p_drop)
        self.fc = nn.Linear(dim, dim)
        self.drop2 = nn.Dropout(p_drop)
        if activation == "gelu":
            self.act = nn.GELU()
        elif activation == "relu":
            self.act = nn.ReLU(inplace=True)
        else:
            self.act = nn.GELU()
        self.scale = nn.Parameter(torch.tensor(scale, dtype=torch.float32))

    def forward(self, x):
        if isinstance(self.norm, nn.BatchNorm1d):
            y = self.norm(x)
        else:
            y = self.norm(x)
        y = self.act(y)
        y = self.drop1(y)
        y = self.fc(y)
        y = self.drop2(y)
        return x + y * self.scale


class MLPNet(nn.Module):
    def __init__(self, input_dim, num_classes, hidden_dim, dropout_in=0.1, dropout_block=0.1, use_layernorm=True):
        super().__init__()
        self.standardize = Standardize(input_dim)
        self.stem = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.GELU(),
            nn.Dropout(dropout_in),
        )
        self.block1 = ResidualLinearBlock(hidden_dim, p_drop=dropout_block, activation="gelu", scale=1.0, use_layernorm=use_layernorm)
        self.block2 = ResidualLinearBlock(hidden_dim, p_drop=dropout_block, activation="gelu", scale=1.0, use_layernorm=use_layernorm)
        self.pre_head_norm = nn.LayerNorm(hidden_dim) if use_layernorm else nn.BatchNorm1d(hidden_dim)
        self.head_drop = nn.Dropout(dropout_in)
        self.head = nn.Linear(hidden_dim, num_classes)

    def forward(self, x):
        x = self.standardize(x)
        x = self.stem(x)
        x = self.block1(x)
        x = self.block2(x)
        if isinstance(self.pre_head_norm, nn.BatchNorm1d):
            x = self.pre_head_norm(x)
        else:
            x = self.pre_head_norm(x)
        x = self.head_drop(x)
        x = self.head(x)
        return x


def count_trainable_params(model: nn.Module) -> int:
    return sum(p.numel() for p in model.parameters() if p.requires_grad)


def compute_dataset_stats(loader, device, input_dim):
    total = 0
    mean = torch.zeros(input_dim, dtype=torch.float64, device=device)
    M2 = torch.zeros(input_dim, dtype=torch.float64, device=device)
    for inputs, _ in loader:
        inputs = inputs.to(device, non_blocking=True)
        inputs = inputs.view(inputs.size(0), -1).to(torch.float32)
        batch = inputs.shape[0]
        total_new = total + batch
        delta = inputs.double().sum(dim=0) / batch - mean
        mean = mean + delta * (batch / total_new) if total_new > 0 else inputs.double().mean(dim=0)
        x_centered = inputs.double() - mean
        M2 = M2 + (x_centered ** 2).sum(dim=0)
        total = total_new
    mean = mean.float().cpu()
    var = (M2 / max(total, 1)).float().cpu()
    std = torch.sqrt(var + 1e-6)
    return mean, std


class Solution:
    def _build_model_under_limit(self, input_dim, num_classes, param_limit, prefer_layernorm=True):
        # Try descending widths to fit within param budget
        # Start from a high width and step down
        # Use step of 16 to align with typical vectorization
        candidate_widths = list(range(1600, 512 - 1, -16))
        best_model = None
        best_width = None
        for H in candidate_widths:
            model = MLPNet(input_dim, num_classes, H, dropout_in=0.15, dropout_block=0.15, use_layernorm=prefer_layernorm)
            params = count_trainable_params(model)
            if params <= param_limit:
                best_model = model
                best_width = H
                break
        if best_model is None:
            # Fallback to minimal width ensuring it's under limit
            H = 512
            best_model = MLPNet(input_dim, num_classes, H, dropout_in=0.15, dropout_block=0.15, use_layernorm=prefer_layernorm)
            best_width = H
        return best_model, best_width

    def _evaluate(self, model, loader, device):
        model.eval()
        correct = 0
        total = 0
        with torch.no_grad():
            for inputs, targets in loader:
                inputs = inputs.to(device, non_blocking=True)
                targets = targets.to(device, non_blocking=True)
                inputs = inputs.view(inputs.size(0), -1).to(torch.float32)
                logits = model(inputs)
                preds = logits.argmax(dim=1)
                correct += (preds == targets).sum().item()
                total += targets.numel()
        acc = correct / max(total, 1)
        return acc

    def solve(self, train_loader, val_loader, metadata: dict = None) -> torch.nn.Module:
        if metadata is None:
            metadata = {}
        # Device handling
        device = metadata.get("device", "cpu")
        torch.manual_seed(42)
        if torch.cuda.is_available() and device == "cuda":
            torch.cuda.manual_seed_all(42)
        input_dim = int(metadata.get("input_dim", 384))
        num_classes = int(metadata.get("num_classes", 128))
        param_limit = int(metadata.get("param_limit", 5_000_000))

        # Build model under parameter limit
        model, width = self._build_model_under_limit(input_dim, num_classes, param_limit, prefer_layernorm=True)
        model.to(device)

        # Compute dataset statistics for input standardization
        with torch.no_grad():
            mean, std = compute_dataset_stats(train_loader, device, input_dim)
        model.standardize.set_stats(mean, std)

        # Training setup
        epochs = 180
        # Good starting LR for large MLPs on CPU
        base_lr = 3e-3
        weight_decay = 5e-4
        betas = (0.9, 0.99)
        optimizer = torch.optim.AdamW(model.parameters(), lr=base_lr, weight_decay=weight_decay, betas=betas)

        steps_per_epoch = max(1, len(train_loader))
        total_steps = epochs * steps_per_epoch
        # OneCycleLR for reliable convergence
        scheduler = torch.optim.lr_scheduler.OneCycleLR(
            optimizer,
            max_lr=base_lr,
            total_steps=total_steps,
            pct_start=0.15,
            anneal_strategy="cos",
            div_factor=10.0,
            final_div_factor=1e3,
        )

        # Label smoothing for robustness
        criterion = nn.CrossEntropyLoss(label_smoothing=0.05)

        best_acc = 0.0
        best_state = copy.deepcopy(model.state_dict())
        epochs_no_improve = 0
        patience = 30

        for epoch in range(epochs):
            model.train()
            for inputs, targets in train_loader:
                inputs = inputs.to(device, non_blocking=True)
                targets = targets.to(device, non_blocking=True)
                inputs = inputs.view(inputs.size(0), -1).to(torch.float32)

                optimizer.zero_grad(set_to_none=True)
                logits = model(inputs)
                loss = criterion(logits, targets)
                loss.backward()
                nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
                optimizer.step()
                scheduler.step()

            # Validation
            val_acc = self._evaluate(model, val_loader, device)

            if val_acc > best_acc + 1e-5:
                best_acc = val_acc
                best_state = copy.deepcopy(model.state_dict())
                epochs_no_improve = 0
            else:
                epochs_no_improve += 1

            if epochs_no_improve >= patience:
                break

        # Load best weights
        model.load_state_dict(best_state)
        model.eval()
        return model
