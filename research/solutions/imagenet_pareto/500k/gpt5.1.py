import math
import random
from typing import List, Optional

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F


class MLPNet(nn.Module):
    def __init__(self, input_dim: int, num_classes: int, hidden_dims: List[int], dropout_probs: List[float]):
        super().__init__()
        assert len(hidden_dims) == len(dropout_probs)
        layers: List[nn.Module] = []
        prev_dim = input_dim

        for h_dim, drop in zip(hidden_dims, dropout_probs):
            layers.append(nn.Linear(prev_dim, h_dim))
            layers.append(nn.BatchNorm1d(h_dim))
            layers.append(nn.GELU())
            if drop > 1e-6:
                layers.append(nn.Dropout(drop))
            prev_dim = h_dim

        self.feature_extractor = nn.Sequential(*layers)
        self.classifier = nn.Linear(prev_dim, num_classes)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self.feature_extractor(x)
        x = self.classifier(x)
        return x


class Solution:
    def _set_seed(self, seed: int = 42) -> None:
        random.seed(seed)
        np.random.seed(seed)
        torch.manual_seed(seed)

    def _estimate_params(self, input_dim: int, num_classes: int, hidden_dims: List[int]) -> int:
        dims = [input_dim] + hidden_dims + [num_classes]
        total = 0
        # Linear layers
        for in_d, out_d in zip(dims, dims[1:]):
            total += in_d * out_d + out_d  # weights + bias
        # BatchNorm for hidden layers
        for h in hidden_dims:
            total += 2 * h  # gamma + beta
        return total

    def _build_hidden_dims(self, input_dim: int, num_classes: int, param_limit: int) -> List[int]:
        if param_limit is None or param_limit <= 0:
            param_limit = 500000

        # Initial design aimed at ~480k params for (384,128,500k)
        base_width = int(input_dim * 1.5)
        base_width = max(256, min(512, base_width))

        h1 = base_width
        h2 = min(base_width, max(input_dim, num_classes * 3))
        h3 = max(num_classes, min(256, input_dim // 3 if input_dim >= 64 else num_classes))
        h4 = h3
        hidden_dims = [h1, h2, h3, h4]

        def est(hd: List[int]) -> int:
            return self._estimate_params(input_dim, num_classes, hd)

        # If this is too big, progressively shrink widths and/or depth
        # Phase 1: shrink widths
        for _ in range(20):
            if est(hidden_dims) <= param_limit:
                break
            new_dims = []
            for d in hidden_dims:
                if d > num_classes:
                    new_d = max(num_classes, int(d * 0.85))
                else:
                    new_d = d
                new_dims.append(new_d)
            hidden_dims = new_dims

        # Phase 2: reduce depth if still too large
        while len(hidden_dims) > 1 and est(hidden_dims) > param_limit:
            hidden_dims.pop()  # drop last layer

        # Phase 3: aggressively shrink last remaining layer if needed
        while len(hidden_dims) == 1 and est(hidden_dims) > param_limit and hidden_dims[0] > num_classes:
            hidden_dims[0] = max(num_classes, hidden_dims[0] - 16)

        # If still too large, fall back to no hidden layers (logistic regression)
        if est(hidden_dims) > param_limit:
            hidden_dims = []

        return hidden_dims

    def _build_model(self, input_dim: int, num_classes: int, param_limit: Optional[int]) -> nn.Module:
        if param_limit is None:
            param_limit = 500000

        hidden_dims = self._build_hidden_dims(input_dim, num_classes, param_limit)

        if len(hidden_dims) == 0:
            model = nn.Linear(input_dim, num_classes)
        else:
            # Progressive dropout: a bit more on deeper layers
            dropout_probs = []
            base_drop = 0.15
            step = 0.05
            for i in range(len(hidden_dims)):
                p = base_drop + step * i
                p = min(0.35, max(0.0, p))
                dropout_probs.append(p)
            model = MLPNet(input_dim, num_classes, hidden_dims, dropout_probs)

        # Final safety check (should always be true)
        param_count = sum(p.numel() for p in model.parameters() if p.requires_grad)
        if param_count > param_limit:
            # As a last resort, switch to a single-layer logistic regression
            model = nn.Linear(input_dim, num_classes)

        return model

    def _evaluate(self, model: nn.Module, loader, device: torch.device, criterion: nn.Module) -> (float, float):
        model.eval()
        total_loss = 0.0
        total_correct = 0
        total_samples = 0
        with torch.no_grad():
            for inputs, targets in loader:
                inputs = inputs.to(device)
                targets = targets.to(device)
                outputs = model(inputs)
                loss = criterion(outputs, targets)
                batch_size = targets.size(0)
                total_loss += loss.item() * batch_size
                preds = outputs.argmax(dim=1)
                total_correct += (preds == targets).sum().item()
                total_samples += batch_size
        avg_loss = total_loss / max(1, total_samples)
        accuracy = total_correct / max(1, total_samples)
        return avg_loss, accuracy

    def solve(self, train_loader, val_loader, metadata: dict = None) -> torch.nn.Module:
        self._set_seed(42)

        if metadata is None:
            metadata = {}

        input_dim = int(metadata.get("input_dim", 384))
        num_classes = int(metadata.get("num_classes", 128))
        param_limit = int(metadata.get("param_limit", 500000))
        device_str = metadata.get("device", "cpu")
        device = torch.device(device_str if torch.cuda.is_available() or device_str == "cpu" else "cpu")
        train_samples = metadata.get("train_samples", None)

        model = self._build_model(input_dim, num_classes, param_limit)
        model.to(device)

        # Training hyperparameters
        if train_samples is None:
            try:
                train_samples = len(train_loader.dataset)
            except Exception:
                train_samples = 2048

        if train_samples <= 3000:
            max_epochs = 320
        elif train_samples <= 10000:
            max_epochs = 200
        else:
            max_epochs = 40

        patience = 80 if max_epochs >= 200 else max_epochs // 3

        criterion = nn.CrossEntropyLoss(label_smoothing=0.05)
        optimizer = torch.optim.AdamW(model.parameters(), lr=3e-3, weight_decay=1e-2)
        scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=max_epochs, eta_min=1e-5)

        best_val_acc = 0.0
        best_state = None
        epochs_no_improve = 0

        for epoch in range(max_epochs):
            model.train()
            total_loss = 0.0
            total_correct = 0
            total_samples_epoch = 0

            for inputs, targets in train_loader:
                inputs = inputs.to(device)
                targets = targets.to(device)

                optimizer.zero_grad(set_to_none=True)
                outputs = model(inputs)
                loss = criterion(outputs, targets)
                loss.backward()
                torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=5.0)
                optimizer.step()

                batch_size = targets.size(0)
                total_loss += loss.item() * batch_size
                preds = outputs.argmax(dim=1)
                total_correct += (preds == targets).sum().item()
                total_samples_epoch += batch_size

            scheduler.step()

            _, val_acc = self._evaluate(model, val_loader, device, criterion)

            if val_acc > best_val_acc + 1e-4:
                best_val_acc = val_acc
                best_state = {k: v.cpu().clone() for k, v in model.state_dict().items()}
                epochs_no_improve = 0
            else:
                epochs_no_improve += 1
                if epochs_no_improve >= patience:
                    break

        if best_state is not None:
            model.load_state_dict(best_state)

        model.to(device)
        return model