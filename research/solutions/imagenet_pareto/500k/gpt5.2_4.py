import math
import copy
import os
from typing import Optional, Dict

import torch
import torch.nn as nn
from torch.utils.data import DataLoader, ConcatDataset


def _count_trainable_params(model: nn.Module) -> int:
    return sum(p.numel() for p in model.parameters() if p.requires_grad)


@torch.inference_mode()
def _accuracy(model: nn.Module, loader: DataLoader, device: torch.device) -> float:
    model.eval()
    correct = 0
    total = 0
    for xb, yb in loader:
        xb = xb.to(device, non_blocking=True)
        yb = yb.to(device, non_blocking=True)
        logits = model(xb)
        pred = logits.argmax(dim=1)
        correct += (pred == yb).sum().item()
        total += yb.numel()
    return correct / max(1, total)


class _MLPNet(nn.Module):
    def __init__(self, input_dim: int, num_classes: int, hidden1: int, hidden2: int, dropout: float = 0.12):
        super().__init__()
        self.bn0 = nn.BatchNorm1d(input_dim)
        self.fc1 = nn.Linear(input_dim, hidden1, bias=True)
        self.bn1 = nn.BatchNorm1d(hidden1)
        self.fc2 = nn.Linear(hidden1, hidden2, bias=True)
        self.bn2 = nn.BatchNorm1d(hidden2)
        self.fc3 = nn.Linear(hidden2, num_classes, bias=True)
        self.act = nn.GELU()
        self.drop1 = nn.Dropout(dropout)
        self.drop2 = nn.Dropout(dropout)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        if x.dim() == 1:
            x = x.unsqueeze(0)
        x = self.bn0(x)
        x = self.fc1(x)
        x = self.bn1(x)
        x = self.act(x)
        x = self.drop1(x)
        x = self.fc2(x)
        x = self.bn2(x)
        x = self.act(x)
        x = self.drop2(x)
        x = self.fc3(x)
        return x


class Solution:
    def solve(self, train_loader, val_loader, metadata: dict = None) -> torch.nn.Module:
        if metadata is None:
            metadata = {}

        device_str = metadata.get("device", "cpu")
        device = torch.device(device_str)

        input_dim = int(metadata.get("input_dim", 384))
        num_classes = int(metadata.get("num_classes", 128))
        param_limit = int(metadata.get("param_limit", 500_000))

        torch.set_num_threads(min(8, os.cpu_count() or 8))
        torch.manual_seed(0)

        hidden2 = 256
        dropout = 0.12

        const = 2 * input_dim + 3 * hidden2 + hidden2 * num_classes + num_classes
        denom = input_dim + hidden2 + 3
        hidden1 = (param_limit - const) // max(1, denom)
        hidden1 = int(max(64, hidden1))

        model = _MLPNet(input_dim=input_dim, num_classes=num_classes, hidden1=hidden1, hidden2=hidden2, dropout=dropout)
        model.to(device)

        params = _count_trainable_params(model)
        if params > param_limit:
            hidden1 = max(64, hidden1 - 1)
            while hidden1 >= 64:
                model = _MLPNet(input_dim=input_dim, num_classes=num_classes, hidden1=hidden1, hidden2=hidden2, dropout=dropout).to(device)
                params = _count_trainable_params(model)
                if params <= param_limit:
                    break
                hidden1 -= 1

        params = _count_trainable_params(model)
        if params > param_limit:
            model.eval()
            return model

        batch_size = getattr(train_loader, "batch_size", None) or 64
        max_epochs = 180
        patience = 25
        warmup_epochs = 5

        base_lr = 4e-3
        min_lr = 4e-5
        weight_decay = 1.5e-2

        optimizer = torch.optim.AdamW(model.parameters(), lr=base_lr, weight_decay=weight_decay, betas=(0.9, 0.99))
        criterion = nn.CrossEntropyLoss(label_smoothing=0.08)

        def lr_for_epoch(ep: int) -> float:
            if ep < warmup_epochs:
                return base_lr * float(ep + 1) / float(warmup_epochs)
            t = float(ep - warmup_epochs) / float(max(1, max_epochs - warmup_epochs - 1))
            return min_lr + 0.5 * (base_lr - min_lr) * (1.0 + math.cos(math.pi * t))

        best_state = None
        best_acc = -1.0
        bad = 0

        for epoch in range(max_epochs):
            lr = lr_for_epoch(epoch)
            for pg in optimizer.param_groups:
                pg["lr"] = lr

            model.train()
            for xb, yb in train_loader:
                xb = xb.to(device, non_blocking=True)
                yb = yb.to(device, non_blocking=True)

                optimizer.zero_grad(set_to_none=True)
                logits = model(xb)
                loss = criterion(logits, yb)
                loss.backward()
                torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
                optimizer.step()

            if val_loader is not None:
                va = _accuracy(model, val_loader, device)
                if va > best_acc + 1e-4:
                    best_acc = va
                    best_state = copy.deepcopy(model.state_dict())
                    bad = 0
                else:
                    bad += 1
                if bad >= patience:
                    break
            else:
                if best_state is None:
                    best_state = copy.deepcopy(model.state_dict())

        if best_state is not None:
            model.load_state_dict(best_state, strict=True)

        if val_loader is not None:
            try:
                ds = ConcatDataset([train_loader.dataset, val_loader.dataset])
                ft_loader = DataLoader(
                    ds,
                    batch_size=batch_size,
                    shuffle=True,
                    num_workers=getattr(train_loader, "num_workers", 0) or 0,
                    pin_memory=False,
                    drop_last=False,
                )
                ft_epochs = 25
                ft_lr = max(6e-4, base_lr * 0.25)
                ft_opt = torch.optim.AdamW(model.parameters(), lr=ft_lr, weight_decay=weight_decay, betas=(0.9, 0.99))
                for _ in range(ft_epochs):
                    model.train()
                    for xb, yb in ft_loader:
                        xb = xb.to(device, non_blocking=True)
                        yb = yb.to(device, non_blocking=True)
                        ft_opt.zero_grad(set_to_none=True)
                        logits = model(xb)
                        loss = criterion(logits, yb)
                        loss.backward()
                        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
                        ft_opt.step()
            except Exception:
                pass

        model.eval()
        return model