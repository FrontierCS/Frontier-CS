import math
import copy
from typing import Dict, Any

import torch
import torch.nn as nn
import torch.nn.functional as F


class LabelSmoothingCrossEntropy(nn.Module):
    def __init__(self, smoothing: float = 0.1):
        super().__init__()
        self.smoothing = float(smoothing)

    def forward(self, preds: torch.Tensor, target: torch.Tensor) -> torch.Tensor:
        log_probs = F.log_softmax(preds, dim=-1)
        n_classes = preds.size(-1)
        with torch.no_grad():
            true_dist = torch.empty_like(log_probs)
            true_dist.fill_(self.smoothing / (n_classes - 1))
            true_dist.scatter_(1, target.unsqueeze(1), 1.0 - self.smoothing)
        return torch.mean(torch.sum(-true_dist * log_probs, dim=-1))


class ResidualMLP(nn.Module):
    def __init__(
        self,
        input_dim: int,
        hidden_dim: int,
        num_classes: int,
        num_residual_layers: int = 2,
        dropout: float = 0.1,
    ):
        super().__init__()
        self.input_dim = input_dim
        self.hidden_dim = hidden_dim
        self.num_classes = num_classes
        self.num_residual_layers = num_residual_layers

        self.fc_in = nn.Linear(input_dim, hidden_dim)
        self.bn_in = nn.BatchNorm1d(hidden_dim)
        self.act = nn.GELU()
        self.dropout_in = nn.Dropout(dropout) if dropout > 0.0 else nn.Identity()

        layers = []
        for _ in range(num_residual_layers):
            layers.append(
                nn.Sequential(
                    nn.BatchNorm1d(hidden_dim),
                    nn.GELU(),
                    nn.Dropout(dropout) if dropout > 0.0 else nn.Identity(),
                    nn.Linear(hidden_dim, hidden_dim),
                )
            )
        self.res_layers = nn.ModuleList(layers)
        self.fc_out = nn.Linear(hidden_dim, num_classes)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self.fc_in(x)
        x = self.bn_in(x)
        x = self.act(x)
        x = self.dropout_in(x)
        for layer in self.res_layers:
            out = layer(x)
            x = x + out
        x = self.fc_out(x)
        return x


class Solution:
    def _estimate_params(
        self,
        hidden_dim: int,
        input_dim: int,
        num_classes: int,
        num_res_layers: int,
    ) -> int:
        L = num_res_layers
        # Total trainable parameters for ResidualMLP as defined above
        # fc_in: input_dim*hidden_dim + hidden_dim
        # bn_in: 2*hidden_dim
        # each residual layer: bn(2*hidden_dim) + linear(hidden_dim^2 + hidden_dim) = hidden_dim^2 + 3*hidden_dim
        # fc_out: hidden_dim*num_classes + num_classes
        return (
            input_dim * hidden_dim
            + hidden_dim
            + 2 * hidden_dim
            + L * (hidden_dim * hidden_dim + 3 * hidden_dim)
            + hidden_dim * num_classes
            + num_classes
        )

    def _choose_hidden_dim(
        self,
        input_dim: int,
        num_classes: int,
        param_limit: int,
        num_res_layers: int,
    ) -> int:
        # Start from a heuristic upper bound and decrease until within limit
        L = max(num_res_layers, 1)
        approx = int(math.sqrt(max(param_limit // L, 1)))
        hidden_dim = max(min(approx, 4096), 16)

        while (
            hidden_dim > 16
            and self._estimate_params(
                hidden_dim, input_dim, num_classes, num_res_layers
            )
            > param_limit
        ):
            hidden_dim -= 1

        if (
            self._estimate_params(hidden_dim, input_dim, num_classes, num_res_layers)
            <= param_limit
        ):
            return hidden_dim

        # If we still can't satisfy, fall back to smaller search
        for h in range(16, 512):
            if (
                self._estimate_params(h, input_dim, num_classes, num_res_layers)
                <= param_limit
            ):
                return h

        # As an ultimate fallback (for extremely tight budgets), return a small dim;
        # caller may later decide to use a simpler model.
        return 32

    def _evaluate(
        self,
        model: nn.Module,
        data_loader,
        device: torch.device,
        criterion: nn.Module,
    ):
        model.eval()
        total_loss = 0.0
        total_correct = 0
        total = 0
        with torch.no_grad():
            for inputs, targets in data_loader:
                inputs = inputs.to(device)
                targets = targets.to(device)
                outputs = model(inputs)
                loss = criterion(outputs, targets)
                total_loss += loss.item() * targets.size(0)
                preds = outputs.argmax(dim=1)
                total_correct += (preds == targets).sum().item()
                total += targets.size(0)
        if total == 0:
            return 0.0, 0.0
        return total_loss / total, total_correct / total

    def _train(
        self,
        model: nn.Module,
        train_loader,
        val_loader,
        device: torch.device,
        metadata: Dict[str, Any],
    ):
        train_samples = metadata.get("train_samples", None) if metadata else None
        if train_samples is not None and train_samples <= 4096:
            num_epochs = 220
        else:
            num_epochs = 160

        patience = max(20, num_epochs // 5)
        base_lr = 3e-3
        weight_decay = 1e-4

        criterion = LabelSmoothingCrossEntropy(smoothing=0.1)
        optimizer = torch.optim.AdamW(
            model.parameters(), lr=base_lr, weight_decay=weight_decay
        )
        scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(
            optimizer, T_max=num_epochs, eta_min=1e-5
        )

        best_state = copy.deepcopy(model.state_dict())
        best_val_acc = 0.0
        epochs_no_improve = 0

        for _ in range(num_epochs):
            model.train()
            for inputs, targets in train_loader:
                inputs = inputs.to(device)
                targets = targets.to(device)

                optimizer.zero_grad()
                outputs = model(inputs)
                loss = criterion(outputs, targets)
                loss.backward()
                torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=5.0)
                optimizer.step()

            _, val_acc = self._evaluate(model, val_loader, device, criterion)

            if val_acc > best_val_acc:
                best_val_acc = val_acc
                best_state = copy.deepcopy(model.state_dict())
                epochs_no_improve = 0
            else:
                epochs_no_improve += 1
                if epochs_no_improve >= patience:
                    break

            scheduler.step()

        model.load_state_dict(best_state)

    def solve(self, train_loader, val_loader, metadata: dict = None) -> torch.nn.Module:
        if metadata is None:
            metadata = {}
        device_str = metadata.get("device", "cpu")
        device = torch.device(device_str)

        input_dim = int(metadata.get("input_dim", 384))
        num_classes = int(metadata.get("num_classes", 128))
        param_limit = int(metadata.get("param_limit", 2_500_000))

        # Prefer a 2-residual-layer MLP if budget allows
        num_res_layers = 2
        hidden_dim = self._choose_hidden_dim(
            input_dim, num_classes, param_limit, num_res_layers
        )

        # If even a small hidden_dim with residual MLP doesn't fit, fall back to linear
        estimated_params = self._estimate_params(
            hidden_dim, input_dim, num_classes, num_res_layers
        )
        if estimated_params > param_limit:
            model = nn.Linear(input_dim, num_classes)
        else:
            model = ResidualMLP(
                input_dim=input_dim,
                hidden_dim=hidden_dim,
                num_classes=num_classes,
                num_residual_layers=num_res_layers,
                dropout=0.1,
            )

        model.to(device)

        # Final safety check on parameter count, shrink hidden_dim if needed
        param_count = sum(p.numel() for p in model.parameters() if p.requires_grad)
        if param_count > param_limit and isinstance(model, ResidualMLP):
            # Iteratively decrease hidden_dim until under limit
            hidden_dim = model.hidden_dim
            while hidden_dim > 16 and param_count > param_limit:
                hidden_dim -= 8
                model = ResidualMLP(
                    input_dim=input_dim,
                    hidden_dim=hidden_dim,
                    num_classes=num_classes,
                    num_residual_layers=num_res_layers,
                    dropout=0.1,
                ).to(device)
                param_count = sum(
                    p.numel() for p in model.parameters() if p.requires_grad
                )
            if param_count > param_limit:
                model = nn.Linear(input_dim, num_classes).to(device)

        # Train the model
        self._train(model, train_loader, val_loader, device, metadata)

        model.eval()
        return model