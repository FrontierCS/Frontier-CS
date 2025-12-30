import torch
import torch.nn as nn
import torch.optim as optim
import random
import numpy as np
import copy


class InputNormalizer(nn.Module):
    def __init__(self, mean, std):
        super().__init__()
        mean = mean.to(torch.float32)
        std = std.to(torch.float32)
        self.register_buffer("mean", mean)
        self.register_buffer("std", std)

    def forward(self, x):
        return (x - self.mean) / self.std


class MLPNet(nn.Module):
    def __init__(self, input_dim, num_classes, hidden_dims, dropout=0.0, use_bn=True):
        super().__init__()
        layers = []
        in_features = input_dim
        for h in hidden_dims:
            layers.append(nn.Linear(in_features, h))
            if use_bn:
                layers.append(nn.BatchNorm1d(h))
            layers.append(nn.ReLU(inplace=True))
            if dropout > 0.0:
                layers.append(nn.Dropout(dropout))
            in_features = h
        layers.append(nn.Linear(in_features, num_classes))
        self.net = nn.Sequential(*layers)

    def forward(self, x):
        return self.net(x)


class Solution:
    def __init__(self):
        pass

    def _count_params(self, model: nn.Module) -> int:
        return sum(p.numel() for p in model.parameters() if p.requires_grad)

    def _create_mlp(self, input_dim: int, num_classes: int, hidden_dims):
        if len(hidden_dims) == 0:
            # Logistic regression baseline (no BN, no dropout)
            return MLPNet(input_dim, num_classes, hidden_dims, dropout=0.0, use_bn=False)
        num_hidden = len(hidden_dims)
        if num_hidden >= 3:
            dropout = 0.3
        elif num_hidden == 2:
            dropout = 0.25
        else:
            dropout = 0.2
        return MLPNet(input_dim, num_classes, hidden_dims, dropout=dropout, use_bn=True)

    def _build_best_mlp(self, input_dim: int, num_classes: int, param_limit: int) -> nn.Module:
        hidden_layer_options = [3, 2, 1]
        max_width_cap = 1024

        best_hidden = None
        best_params = -1

        for num_hidden in hidden_layer_options:
            low, high = 1, max_width_cap
            best_width = None
            while low <= high:
                mid = (low + high) // 2
                hidden_dims = [mid] * num_hidden
                model = self._create_mlp(input_dim, num_classes, hidden_dims)
                params = self._count_params(model)
                if params <= param_limit:
                    best_width = mid
                    low = mid + 1
                else:
                    high = mid - 1
            if best_width is not None:
                hidden_dims = [best_width] * num_hidden
                model = self._create_mlp(input_dim, num_classes, hidden_dims)
                params = self._count_params(model)
                if params <= param_limit and params > best_params:
                    best_params = params
                    best_hidden = hidden_dims

        if best_hidden is None:
            model = self._create_mlp(input_dim, num_classes, [])
            # In the unlikely event even logistic regression violates the limit,
            # we still return it (constraint should handle externally).
            return model

        return self._create_mlp(input_dim, num_classes, best_hidden)

    def _compute_input_stats(self, loader, input_dim: int):
        with torch.no_grad():
            sum_ = torch.zeros(input_dim, dtype=torch.float64)
            sum_sq = torch.zeros(input_dim, dtype=torch.float64)
            n = 0
            for batch in loader:
                if isinstance(batch, (list, tuple)):
                    x = batch[0]
                else:
                    x = batch
                x = x.view(x.size(0), -1).to(torch.float64)
                sum_ += x.sum(dim=0)
                sum_sq += (x * x).sum(dim=0)
                n += x.size(0)
            if n == 0:
                mean = torch.zeros(input_dim, dtype=torch.float32)
                std = torch.ones(input_dim, dtype=torch.float32)
            else:
                mean = sum_ / n
                var = sum_sq / n - mean * mean
                var.clamp_(min=1e-6)
                std = torch.sqrt(var)
                mean = mean.to(torch.float32)
                std = std.to(torch.float32)
        return mean, std

    def _train_model(self, model: nn.Module, train_loader, val_loader, device: torch.device):
        max_epochs = 200
        patience = 25
        base_lr = 3e-3
        weight_decay = 1e-4

        criterion = nn.CrossEntropyLoss(label_smoothing=0.05)
        optimizer = optim.AdamW(model.parameters(), lr=base_lr, weight_decay=weight_decay)
        scheduler = optim.lr_scheduler.ReduceLROnPlateau(
            optimizer,
            mode="max",
            factor=0.5,
            patience=5,
            min_lr=1e-5,
            verbose=False,
        )

        best_state = copy.deepcopy(model.state_dict())
        best_val_acc = 0.0
        epochs_no_improve = 0

        for _ in range(max_epochs):
            model.train()
            for batch in train_loader:
                inputs, targets = batch
                inputs = inputs.to(device)
                targets = targets.to(device)
                optimizer.zero_grad()
                outputs = model(inputs)
                loss = criterion(outputs, targets)
                loss.backward()
                torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=5.0)
                optimizer.step()

            if val_loader is not None:
                model.eval()
                val_correct = 0
                val_total = 0
                with torch.no_grad():
                    for batch in val_loader:
                        inputs, targets = batch
                        inputs = inputs.to(device)
                        targets = targets.to(device)
                        outputs = model(inputs)
                        _, preds = torch.max(outputs, dim=1)
                        val_correct += (preds == targets).sum().item()
                        val_total += targets.size(0)
                val_acc = val_correct / val_total if val_total > 0 else 0.0
                scheduler.step(val_acc)

                if val_acc > best_val_acc + 1e-4:
                    best_val_acc = val_acc
                    best_state = copy.deepcopy(model.state_dict())
                    epochs_no_improve = 0
                else:
                    epochs_no_improve += 1
                    if epochs_no_improve >= patience:
                        break
            else:
                scheduler.step(0.0)

        model.load_state_dict(best_state)

    def solve(self, train_loader, val_loader, metadata: dict = None) -> torch.nn.Module:
        if metadata is None:
            metadata = {}

        # Reproducibility
        seed = 42
        random.seed(seed)
        np.random.seed(seed)
        torch.manual_seed(seed)

        input_dim = metadata.get("input_dim", None)
        num_classes = metadata.get("num_classes", None)
        param_limit = metadata.get("param_limit", 500_000)
        device_str = metadata.get("device", "cpu")
        device = torch.device(device_str)

        if input_dim is None or num_classes is None:
            for batch in train_loader:
                inputs, targets = batch
                input_dim = inputs.view(inputs.size(0), -1).size(1)
                num_classes = int(targets.max().item()) + 1
                break

        mean_1d, std_1d = self._compute_input_stats(train_loader, input_dim)
        mlp = self._build_best_mlp(input_dim, num_classes, param_limit)

        # Safety check against parameter limit
        param_count = self._count_params(mlp)
        if param_count > param_limit:
            mlp = self._create_mlp(input_dim, num_classes, [])

        mean = mean_1d.unsqueeze(0)
        std = std_1d.unsqueeze(0)
        input_norm = InputNormalizer(mean, std)

        model = nn.Sequential(input_norm, mlp)
        model.to(device)

        self._train_model(model, train_loader, val_loader, device)

        return model