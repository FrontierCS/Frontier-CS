import torch
import torch.nn as nn
import torch.optim as optim
from copy import deepcopy
from typing import Dict, Any


class ResidualBlock(nn.Module):
    def __init__(self, dim: int, dropout: float = 0.1):
        super().__init__()
        self.bn1 = nn.BatchNorm1d(dim)
        self.fc1 = nn.Linear(dim, dim)
        self.bn2 = nn.BatchNorm1d(dim)
        self.fc2 = nn.Linear(dim, dim)
        self.act = nn.ReLU(inplace=True)
        self.dropout = nn.Dropout(dropout) if dropout and dropout > 0.0 else nn.Identity()

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        residual = x
        out = self.bn1(x)
        out = self.act(out)
        out = self.fc1(out)
        out = self.dropout(out)
        out = self.bn2(out)
        out = self.act(out)
        out = self.fc2(out)
        return out + residual


class MLPResNet(nn.Module):
    def __init__(
        self,
        input_dim: int,
        num_classes: int,
        width: int = 512,
        num_blocks: int = 4,
        dropout: float = 0.1,
    ):
        super().__init__()
        self.stem = nn.Sequential(
            nn.Linear(input_dim, width),
            nn.BatchNorm1d(width),
            nn.ReLU(inplace=True),
        )

        blocks = []
        for _ in range(num_blocks):
            blocks.append(ResidualBlock(width, dropout=dropout))
        self.blocks = nn.Sequential(*blocks)

        self.head = nn.Sequential(
            nn.BatchNorm1d(width),
            nn.ReLU(inplace=True),
            nn.Linear(width, num_classes),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self.stem(x)
        x = self.blocks(x)
        x = self.head(x)
        return x


def count_trainable_parameters(model: nn.Module) -> int:
    return sum(p.numel() for p in model.parameters() if p.requires_grad)


def build_optimizer(model: nn.Module, lr: float = 3e-3, weight_decay: float = 1e-4):
    decay_params = []
    no_decay_params = []
    for name, param in model.named_parameters():
        if not param.requires_grad:
            continue
        if param.ndim == 1 or name.endswith(".bias"):
            no_decay_params.append(param)
        else:
            decay_params.append(param)

    param_groups = [
        {"params": decay_params, "weight_decay": weight_decay},
        {"params": no_decay_params, "weight_decay": 0.0},
    ]
    optimizer = optim.AdamW(param_groups, lr=lr)
    return optimizer


class Solution:
    def solve(self, train_loader, val_loader, metadata: Dict[str, Any] = None) -> torch.nn.Module:
        if metadata is None:
            metadata = {}

        device_str = metadata.get("device", "cpu")
        device = torch.device(device_str)

        input_dim = int(metadata.get("input_dim", 384))
        num_classes = int(metadata.get("num_classes", 128))
        param_limit = int(metadata.get("param_limit", 2500000))

        # Fixed architecture designed to stay within 2.5M parameters
        width = 512
        num_blocks = 4
        dropout = 0.1

        model = MLPResNet(
            input_dim=input_dim,
            num_classes=num_classes,
            width=width,
            num_blocks=num_blocks,
            dropout=dropout,
        )

        param_count = count_trainable_parameters(model)
        if param_count > param_limit:
            # Fallback to a smaller configuration if metadata param_limit is smaller than expected
            width = 384
            num_blocks = 3
            model = MLPResNet(
                input_dim=input_dim,
                num_classes=num_classes,
                width=width,
                num_blocks=num_blocks,
                dropout=dropout,
            )
            param_count = count_trainable_parameters(model)
            if param_count > param_limit:
                # Final fallback: very small model
                width = 256
                num_blocks = 2
                model = MLPResNet(
                    input_dim=input_dim,
                    num_classes=num_classes,
                    width=width,
                    num_blocks=num_blocks,
                    dropout=dropout,
                )

        model.to(device)

        # Training hyperparameters
        train_samples = metadata.get("train_samples", None)
        if train_samples is not None and train_samples <= 4096:
            max_epochs = 300
        else:
            max_epochs = 200

        patience = 40  # early stopping patience based on validation accuracy

        # Loss and optimizer
        try:
            criterion = nn.CrossEntropyLoss(label_smoothing=0.1)
        except TypeError:
            # Fallback if label_smoothing not supported (for older PyTorch, though env should support it)
            criterion = nn.CrossEntropyLoss()

        optimizer = build_optimizer(model, lr=3e-3, weight_decay=1e-4)
        scheduler = optim.lr_scheduler.CosineAnnealingLR(
            optimizer, T_max=max_epochs, eta_min=3e-5
        )

        if val_loader is not None:
            best_state = deepcopy(model.state_dict())
            best_val_acc = 0.0
            epochs_no_improve = 0

            for epoch in range(max_epochs):
                model.train()
                for inputs, targets in train_loader:
                    if inputs.dim() > 2:
                        inputs = inputs.view(inputs.size(0), -1)
                    inputs = inputs.to(device)
                    targets = targets.to(device)

                    optimizer.zero_grad(set_to_none=True)
                    outputs = model(inputs)
                    loss = criterion(outputs, targets)
                    loss.backward()
                    nn.utils.clip_grad_norm_(model.parameters(), max_norm=5.0)
                    optimizer.step()

                model.eval()
                correct = 0
                total = 0
                with torch.no_grad():
                    for inputs, targets in val_loader:
                        if inputs.dim() > 2:
                            inputs = inputs.view(inputs.size(0), -1)
                        inputs = inputs.to(device)
                        targets = targets.to(device)
                        outputs = model(inputs)
                        preds = outputs.argmax(dim=1)
                        correct += (preds == targets).sum().item()
                        total += targets.numel()

                val_acc = correct / total if total > 0 else 0.0
                if val_acc > best_val_acc + 1e-4:
                    best_val_acc = val_acc
                    best_state = deepcopy(model.state_dict())
                    epochs_no_improve = 0
                else:
                    epochs_no_improve += 1

                scheduler.step()

                if epochs_no_improve >= patience:
                    break

            model.load_state_dict(best_state)
        else:
            # No validation loader; train for full number of epochs without early stopping
            for epoch in range(max_epochs):
                model.train()
                for inputs, targets in train_loader:
                    if inputs.dim() > 2:
                        inputs = inputs.view(inputs.size(0), -1)
                    inputs = inputs.to(device)
                    targets = targets.to(device)

                    optimizer.zero_grad(set_to_none=True)
                    outputs = model(inputs)
                    loss = criterion(outputs, targets)
                    loss.backward()
                    nn.utils.clip_grad_norm_(model.parameters(), max_norm=5.0)
                    optimizer.step()
                scheduler.step()

        model.to(device)
        model.eval()
        return model
