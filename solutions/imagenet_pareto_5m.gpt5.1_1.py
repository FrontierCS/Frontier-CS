import torch
import torch.nn as nn
import torch.nn.functional as F
import random
import numpy as np
import copy


class ResidualBlock(nn.Module):
    def __init__(self, dim: int, dropout: float = 0.1):
        super().__init__()
        self.fc = nn.Linear(dim, dim)
        self.bn = nn.BatchNorm1d(dim)
        self.act = nn.GELU()
        self.dropout = nn.Dropout(dropout)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        residual = x
        out = self.fc(x)
        out = self.bn(out)
        out = self.act(out)
        out = self.dropout(out)
        return residual + out


class ResidualMLP(nn.Module):
    def __init__(self, input_dim: int, num_classes: int, hidden_dim: int, num_blocks: int = 2, dropout: float = 0.1):
        super().__init__()
        self.input = nn.Linear(input_dim, hidden_dim)
        self.in_bn = nn.BatchNorm1d(hidden_dim)
        self.in_act = nn.GELU()
        self.in_drop = nn.Dropout(dropout)
        self.blocks = nn.ModuleList(
            [ResidualBlock(hidden_dim, dropout=dropout) for _ in range(num_blocks)]
        )
        self.output = nn.Linear(hidden_dim, num_classes)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self.input(x)
        x = self.in_bn(x)
        x = self.in_act(x)
        x = self.in_drop(x)
        for block in self.blocks:
            x = block(x)
        x = self.output(x)
        return x


class StandardMLP(nn.Module):
    def __init__(self, input_dim: int, num_classes: int, hidden_dims, dropout: float = 0.1):
        super().__init__()
        layers = []
        last_dim = input_dim
        for h in hidden_dims:
            layers.append(nn.Linear(last_dim, h))
            layers.append(nn.BatchNorm1d(h))
            layers.append(nn.GELU())
            if dropout > 0.0:
                layers.append(nn.Dropout(dropout))
            last_dim = h
        self.features = nn.Sequential(*layers)
        self.classifier = nn.Linear(last_dim, num_classes)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self.features(x)
        x = self.classifier(x)
        return x


class Solution:
    def __init__(self):
        pass

    @staticmethod
    def _set_seeds(seed: int = 42):
        random.seed(seed)
        np.random.seed(seed)
        torch.manual_seed(seed)

    @staticmethod
    def _count_params(model: nn.Module) -> int:
        return sum(p.numel() for p in model.parameters() if p.requires_grad)

    @staticmethod
    def _evaluate(model: nn.Module, data_loader, device: torch.device) -> float:
        model.eval()
        correct = 0
        total = 0
        with torch.no_grad():
            for inputs, targets in data_loader:
                inputs = inputs.to(device)
                targets = targets.to(device)
                outputs = model(inputs)
                preds = outputs.argmax(dim=1)
                correct += (preds == targets).sum().item()
                total += targets.numel()
        if total == 0:
            return 0.0
        return correct / total

    def _train_model(
        self,
        model: nn.Module,
        train_loader,
        val_loader,
        device: torch.device,
        max_epochs: int,
    ):
        model.to(device)
        criterion = nn.CrossEntropyLoss(label_smoothing=0.1)
        optimizer = torch.optim.AdamW(model.parameters(), lr=3e-4, weight_decay=1e-2)
        scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(
            optimizer, T_max=max_epochs, eta_min=1e-5
        )

        best_state = copy.deepcopy(model.state_dict())
        best_val_acc = 0.0
        epochs_no_improve = 0
        patience = max(30, max_epochs // 4)

        for epoch in range(max_epochs):
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

            val_acc = self._evaluate(model, val_loader, device)
            if val_acc > best_val_acc + 1e-4:
                best_val_acc = val_acc
                best_state = copy.deepcopy(model.state_dict())
                epochs_no_improve = 0
            else:
                epochs_no_improve += 1

            scheduler.step()

            if epochs_no_improve >= patience:
                break

        model.load_state_dict(best_state)
        return model, best_val_acc

    def solve(self, train_loader, val_loader, metadata: dict = None) -> torch.nn.Module:
        if metadata is None:
            metadata = {}
        input_dim = int(metadata.get("input_dim", 384))
        num_classes = int(metadata.get("num_classes", 128))
        param_limit = int(metadata.get("param_limit", 5_000_000))
        device_str = metadata.get("device", "cpu")
        device = torch.device(device_str)

        self._set_seeds(42)

        train_samples = metadata.get("train_samples", None)
        if train_samples is not None and train_samples <= 4096:
            max_epochs = 500
        else:
            max_epochs = 300

        # Candidate 1: Wide residual MLP near parameter limit
        base_hidden_dim = 1536
        hidden_dim = base_hidden_dim
        best_resid_model = None
        while hidden_dim >= 256:
            candidate = ResidualMLP(
                input_dim=input_dim,
                num_classes=num_classes,
                hidden_dim=hidden_dim,
                num_blocks=2,
                dropout=0.1,
            )
            if self._count_params(candidate) <= param_limit:
                best_resid_model = candidate
                break
            hidden_dim -= 16
        if best_resid_model is None:
            # Fallback very small model if param_limit is tiny
            best_resid_model = ResidualMLP(
                input_dim=input_dim,
                num_classes=num_classes,
                hidden_dim=256,
                num_blocks=1,
                dropout=0.1,
            )

        # Candidate 2: Deeper tapered MLP (no residual)
        hidden_dims_candidate2 = [2048, 1024, 1024, 512]
        # Adjust first layer width down if exceeding param budget
        while True:
            candidate2 = StandardMLP(
                input_dim=input_dim,
                num_classes=num_classes,
                hidden_dims=hidden_dims_candidate2,
                dropout=0.1,
            )
            if self._count_params(candidate2) <= param_limit:
                break
            if hidden_dims_candidate2[0] <= 512:
                break
            hidden_dims_candidate2[0] -= 128

        models_to_try = [best_resid_model, candidate2]

        best_model = None
        best_val_acc_overall = -1.0

        for model in models_to_try:
            trained_model, val_acc = self._train_model(
                model, train_loader, val_loader, device, max_epochs=max_epochs
            )
            if val_acc > best_val_acc_overall:
                best_val_acc_overall = val_acc
                best_model = trained_model

        if best_model is None:
            best_model = best_resid_model.to(device)

        # Final safety check: ensure parameter limit
        if self._count_params(best_model) > param_limit:
            # As a last resort, return a small safe model trained briefly
            small_model = StandardMLP(
                input_dim=input_dim,
                num_classes=num_classes,
                hidden_dims=[512, 512],
                dropout=0.1,
            ).to(device)
            small_model, _ = self._train_model(
                small_model, train_loader, val_loader, device, max_epochs=200
            )
            best_model = small_model

        best_model.to(device)
        best_model.eval()
        return best_model
