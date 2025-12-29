import math
import copy
import random
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F


class MLPNet(nn.Module):
    def __init__(self, input_dim, num_classes, hidden_dim, n_hidden, dropout=0.1):
        super().__init__()
        self.input_layer = nn.Linear(input_dim, hidden_dim)
        self.input_bn = nn.BatchNorm1d(hidden_dim)
        self.hidden_layers = nn.ModuleList(
            [nn.Linear(hidden_dim, hidden_dim) for _ in range(n_hidden - 1)]
        )
        self.hidden_bns = nn.ModuleList(
            [nn.BatchNorm1d(hidden_dim) for _ in range(n_hidden - 1)]
        )
        self.output_layer = nn.Linear(hidden_dim, num_classes)
        self.dropout = nn.Dropout(dropout)

    def forward(self, x):
        x = self.input_layer(x)
        x = self.input_bn(x)
        x = F.relu(x)
        x = self.dropout(x)

        for layer, bn in zip(self.hidden_layers, self.hidden_bns):
            residual = x
            x = layer(x)
            x = bn(x)
            x = F.relu(x)
            x = self.dropout(x)
            if x.shape == residual.shape:
                x = x + residual

        logits = self.output_layer(x)
        return logits


def count_parameters(model: nn.Module) -> int:
    return sum(p.numel() for p in model.parameters() if p.requires_grad)


def evaluate(model, loader, device):
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
            total += targets.size(0)
    avg_loss = loss_sum / max(total, 1)
    acc = correct / max(total, 1)
    return acc, avg_loss


class Solution:
    def _max_hidden_dim_for_n(self, input_dim, num_classes, param_limit, n_hidden):
        # Parameters for general MLPNet with n_hidden hidden layers and BN on each
        # P = (n_hidden-1)*h^2 + (input_dim + 3*n_hidden + num_classes)*h + num_classes
        a = n_hidden - 1
        b = input_dim + 3 * n_hidden + num_classes
        c = num_classes
        if a == 0:
            # Linear inequality: b*h + c <= param_limit
            if b == 0:
                return 1
            h_max = (param_limit - c) // b
            return max(int(h_max), 1)
        else:
            # Quadratic inequality: a*h^2 + b*h + c - param_limit <= 0
            disc = b * b - 4 * a * (c - param_limit)
            if disc <= 0:
                return 1
            root = math.sqrt(disc)
            h_max = int((-b + root) // (2 * a))
            return max(h_max, 1)

    def _build_model_under_limit(self, input_dim, num_classes, param_limit):
        # Try deeper first, then shallower if needed
        # Prefer 4 hidden layers if possible
        candidate_n_hidden = [4, 3, 5, 2, 1]
        for n_hidden in candidate_n_hidden:
            h = self._max_hidden_dim_for_n(input_dim, num_classes, param_limit, n_hidden)
            # Require a reasonable width unless forced
            if n_hidden > 1 and h < 64:
                continue
            # Cap extremely large widths (shouldn't happen at given limit, but guard anyway)
            h = min(h, 2048)
            # Small safety margin
            if param_limit > 100000:
                margin = int(0.005 * param_limit)
            else:
                margin = 0
            effective_limit = param_limit - margin
            # Adjust down if just over limit
            while h > 1:
                model = MLPNet(input_dim, num_classes, h, n_hidden, dropout=0.1)
                p = count_parameters(model)
                if p <= param_limit:
                    return model
                # If slightly over effective_limit, shrink h a bit faster
                if p > effective_limit:
                    h -= 4
                else:
                    h -= 1
        # Fallback tiny model
        h = 32
        model = MLPNet(input_dim, num_classes, h, 1, dropout=0.1)
        return model

    def solve(self, train_loader, val_loader, metadata: dict = None) -> torch.nn.Module:
        if metadata is None:
            metadata = {}
        input_dim = metadata.get("input_dim", 384)
        num_classes = metadata.get("num_classes", 128)
        param_limit = metadata.get("param_limit", 2_500_000)
        device = metadata.get("device", "cpu")

        # Reproducibility
        seed = 42
        random.seed(seed)
        np.random.seed(seed)
        torch.manual_seed(seed)

        model = self._build_model_under_limit(input_dim, num_classes, param_limit)
        model.to(device)

        # Double-check parameter constraint
        param_count = count_parameters(model)
        if param_count > param_limit:
            # As a hard safety fallback, shrink hidden dim by half and rebuild
            # (should not occur given construction)
            if isinstance(model, MLPNet):
                hidden_dim = model.input_layer.out_features
                n_hidden = len(model.hidden_layers) + 1
                hidden_dim = max(hidden_dim // 2, 1)
                model = MLPNet(input_dim, num_classes, hidden_dim, n_hidden, dropout=0.1)
                model.to(device)

        # Training setup
        lr = 1e-3
        weight_decay = 1e-4
        num_epochs = 200
        patience = 40

        optimizer = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=weight_decay)
        scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(
            optimizer, T_max=num_epochs, eta_min=1e-5
        )
        criterion = nn.CrossEntropyLoss(label_smoothing=0.1)

        best_state = copy.deepcopy(model.state_dict())
        best_val_acc = -1.0
        epochs_no_improve = 0

        for epoch in range(num_epochs):
            model.train()
            for inputs, targets in train_loader:
                inputs = inputs.to(device)
                targets = targets.to(device)

                optimizer.zero_grad(set_to_none=True)
                outputs = model(inputs)
                loss = criterion(outputs, targets)
                loss.backward()
                torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=5.0)
                optimizer.step()

            scheduler.step()

            if val_loader is not None:
                val_acc, _ = evaluate(model, val_loader, device)
                if val_acc > best_val_acc + 1e-4:
                    best_val_acc = val_acc
                    best_state = copy.deepcopy(model.state_dict())
                    epochs_no_improve = 0
                else:
                    epochs_no_improve += 1
                    if epochs_no_improve >= patience:
                        break

        if best_state is not None:
            model.load_state_dict(best_state)

        model.to(device)
        model.eval()
        return model