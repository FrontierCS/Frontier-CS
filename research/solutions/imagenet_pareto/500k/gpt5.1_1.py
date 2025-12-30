import torch
import torch.nn as nn
import torch.nn.functional as F
import random
import numpy as np
from copy import deepcopy


class Solution:
    def _set_seed(self, seed: int = 42):
        torch.manual_seed(seed)
        random.seed(seed)
        np.random.seed(seed)
        if torch.cuda.is_available():
            torch.cuda.manual_seed_all(seed)

    def _make_mlp(self, input_dim, num_classes, hidden_sizes, dropout: float = 0.15):
        if not hidden_sizes:
            return nn.Linear(input_dim, num_classes)

        layers = []
        in_dim = input_dim
        for h in hidden_sizes:
            layers.append(nn.Linear(in_dim, h))
            layers.append(nn.BatchNorm1d(h))
            layers.append(nn.GELU())
            if dropout and dropout > 0:
                layers.append(nn.Dropout(dropout))
            in_dim = h
        layers.append(nn.Linear(in_dim, num_classes))
        return nn.Sequential(*layers)

    def _build_model(self, input_dim, num_classes, param_limit):
        # Largest-to-smallest candidate configurations
        candidate_configs = [
            [622, 256, 256],  # ~499,914 params with BN
            [576, 256, 256],
            [512, 256, 256],
            [512, 256],
            [384, 256],
            [384, 128],
            [256, 128],
            [256],
            [128],
            [],
        ]
        dropout = 0.15
        for cfg in candidate_configs:
            model = self._make_mlp(input_dim, num_classes, cfg, dropout=dropout)
            param_count = sum(p.numel() for p in model.parameters() if p.requires_grad)
            if param_count <= param_limit:
                return model
        # Fallback (should not normally be needed)
        return self._make_mlp(input_dim, num_classes, [], dropout=0.0)

    def solve(self, train_loader, val_loader, metadata: dict = None) -> torch.nn.Module:
        if metadata is None:
            metadata = {}
        input_dim = metadata.get("input_dim", 384)
        num_classes = metadata.get("num_classes", 128)
        param_limit = metadata.get("param_limit", 500000)
        device_str = metadata.get("device", "cpu")
        device = torch.device(device_str)

        self._set_seed(42)

        # Build model under param_limit (and implicitly under 500k hard limit)
        model = self._build_model(input_dim, num_classes, param_limit)
        model.to(device)

        # Enforce hard 500k parameter limit defensively
        hard_limit = 500000
        param_count = sum(p.numel() for p in model.parameters() if p.requires_grad)
        if param_count > hard_limit:
            # Fallback to a smaller model if metadata was misleading
            model = self._make_mlp(input_dim, num_classes, [], dropout=0.0)
            model.to(device)

        # Training hyperparameters
        max_epochs = 200
        patience = 25
        base_lr = 1e-3
        weight_decay = 1e-2

        optimizer = torch.optim.AdamW(model.parameters(), lr=base_lr, weight_decay=weight_decay)

        try:
            criterion = nn.CrossEntropyLoss(label_smoothing=0.1)
        except TypeError:
            criterion = nn.CrossEntropyLoss()

        scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(
            optimizer, T_max=max_epochs, eta_min=1e-5
        )

        best_state = deepcopy(model.state_dict())
        best_val_acc = 0.0
        epochs_no_improve = 0
        has_val = val_loader is not None

        for epoch in range(max_epochs):
            # Training phase
            model.train()
            train_loss = 0.0
            train_correct = 0
            train_total = 0

            for batch in train_loader:
                if isinstance(batch, (list, tuple)) and len(batch) >= 2:
                    inputs, targets = batch[:2]
                else:
                    continue

                inputs = inputs.to(device)
                targets = targets.to(device)

                optimizer.zero_grad(set_to_none=True)
                outputs = model(inputs)
                loss = criterion(outputs, targets)
                loss.backward()
                nn.utils.clip_grad_norm_(model.parameters(), max_norm=5.0)
                optimizer.step()

                batch_size = targets.size(0)
                train_loss += loss.item() * batch_size
                train_total += batch_size
                train_correct += (outputs.argmax(dim=1) == targets).sum().item()

            if train_total > 0:
                train_loss /= train_total

            # Validation phase
            if has_val:
                model.eval()
                val_loss = 0.0
                val_correct = 0
                val_total = 0
                with torch.no_grad():
                    for batch in val_loader:
                        if isinstance(batch, (list, tuple)) and len(batch) >= 2:
                            inputs, targets = batch[:2]
                        else:
                            continue

                        inputs = inputs.to(device)
                        targets = targets.to(device)

                        outputs = model(inputs)
                        loss = criterion(outputs, targets)

                        batch_size = targets.size(0)
                        val_loss += loss.item() * batch_size
                        val_total += batch_size
                        val_correct += (outputs.argmax(dim=1) == targets).sum().item()

                if val_total > 0:
                    val_loss /= val_total
                    val_acc = val_correct / val_total
                else:
                    val_loss = 0.0
                    val_acc = 0.0

                if val_acc > best_val_acc + 1e-4:
                    best_val_acc = val_acc
                    best_state = deepcopy(model.state_dict())
                    epochs_no_improve = 0
                else:
                    epochs_no_improve += 1
            else:
                # No validation set: keep last model
                best_state = deepcopy(model.state_dict())

            scheduler.step()

            if has_val and epochs_no_improve >= patience:
                break

        model.load_state_dict(best_state)
        model.to(device)
        model.eval()
        return model