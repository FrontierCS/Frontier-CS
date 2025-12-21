import math
import random
import copy
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim


class MLPBlock(nn.Module):
    def __init__(self, in_dim: int, out_dim: int, dropout: float = 0.1):
        super().__init__()
        self.linear = nn.Linear(in_dim, out_dim)
        self.norm = nn.LayerNorm(out_dim)
        self.act = nn.GELU()
        self.dropout = nn.Dropout(dropout)
        self.use_residual = in_dim == out_dim

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        out = self.linear(x)
        out = self.norm(out)
        out = self.act(out)
        out = self.dropout(out)
        if self.use_residual:
            out = out + x
        return out


class ClassifierMLP(nn.Module):
    def __init__(self, input_dim: int, num_classes: int, hidden_dims, dropout: float = 0.1):
        super().__init__()
        layers = []
        prev_dim = input_dim
        for h in hidden_dims:
            layers.append(MLPBlock(prev_dim, h, dropout))
            prev_dim = h
        self.features = nn.Sequential(*layers)
        self.head = nn.Linear(prev_dim, num_classes)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self.features(x)
        x = self.head(x)
        return x


def count_parameters(model: nn.Module) -> int:
    return sum(p.numel() for p in model.parameters() if p.requires_grad)


class Solution:
    def _build_best_model(self, input_dim: int, num_classes: int, param_limit: int) -> nn.Module:
        # Candidate architectures (hidden layer sizes)
        candidate_hidden_layers = [
            [1152, 1152, 512],
            [1024, 1024, 512, 512],
            [1024, 1024, 512],
            [960, 960, 960],
            [896, 896, 896],
            [896, 896, 512, 512],
            [768, 768, 768, 512, 512],
            [768, 768, 768],
            [768, 768, 512, 512],
            [768, 768, 512],
            [768, 768],
            [512, 512, 512, 512],
            [512, 512, 512],
            [512, 512],
        ]

        best_model = None
        best_params = -1

        for hidden in candidate_hidden_layers:
            model = ClassifierMLP(input_dim, num_classes, hidden_dims=hidden, dropout=0.1)
            n_params = count_parameters(model)
            if n_params <= param_limit and n_params > best_params:
                best_params = n_params
                best_model = model

        if best_model is None:
            # Fallback: simple linear classifier, guaranteed to fit under the limit for this task
            best_model = nn.Sequential(nn.Linear(input_dim, num_classes))
            # Safety check (should always pass with given constraints)
            if count_parameters(best_model) > param_limit:
                # As an extreme fallback, use a tiny projection before classifier
                proj_dim = max(8, param_limit // (num_classes + 8) - 1)
                best_model = nn.Sequential(
                    nn.Linear(input_dim, proj_dim, bias=False),
                    nn.Linear(proj_dim, num_classes, bias=True),
                )

        return best_model

    def _evaluate_accuracy(self, model: nn.Module, data_loader, device: torch.device) -> float:
        model_was_training = model.training
        model.eval()
        correct = 0
        total = 0
        with torch.no_grad():
            for inputs, targets in data_loader:
                inputs = inputs.to(device=device, dtype=torch.float32)
                targets = targets.to(device=device, dtype=torch.long)
                outputs = model(inputs)
                preds = outputs.argmax(dim=1)
                correct += (preds == targets).sum().item()
                total += targets.numel()
        if model_was_training:
            model.train()
        return correct / total if total > 0 else 0.0

    def _train_model(
        self,
        model: nn.Module,
        train_loader,
        val_loader,
        device: torch.device,
        max_epochs: int = 200,
        lr: float = 1e-3,
        weight_decay: float = 1e-4,
    ) -> nn.Module:
        model.to(device)
        criterion = nn.CrossEntropyLoss(label_smoothing=0.05)
        optimizer = optim.AdamW(model.parameters(), lr=lr, weight_decay=weight_decay)

        best_state = copy.deepcopy(model.state_dict())
        best_val_acc = -math.inf
        patience = 25
        epochs_no_improve = 0

        for _ in range(max_epochs):
            model.train()
            for inputs, targets in train_loader:
                inputs = inputs.to(device=device, dtype=torch.float32)
                targets = targets.to(device=device, dtype=torch.long)

                optimizer.zero_grad()
                outputs = model(inputs)
                loss = criterion(outputs, targets)
                loss.backward()
                torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=5.0)
                optimizer.step()

            val_acc = self._evaluate_accuracy(model, val_loader, device)

            if val_acc > best_val_acc + 1e-4:
                best_val_acc = val_acc
                best_state = copy.deepcopy(model.state_dict())
                epochs_no_improve = 0
            else:
                epochs_no_improve += 1
                if epochs_no_improve >= patience:
                    break

        model.load_state_dict(best_state)
        return model

    def solve(self, train_loader, val_loader, metadata: dict = None) -> torch.nn.Module:
        if metadata is None:
            raise ValueError("metadata dict is required")

        # Reproducibility
        seed = 42
        random.seed(seed)
        np.random.seed(seed)
        torch.manual_seed(seed)

        input_dim = int(metadata.get("input_dim", 384))
        num_classes = int(metadata.get("num_classes", 128))
        param_limit = int(metadata.get("param_limit", 2_500_000))
        device_str = metadata.get("device", "cpu")
        device = torch.device(device_str)

        model = self._build_best_model(input_dim, num_classes, param_limit)
        # Final safety check on parameter count
        if count_parameters(model) > param_limit:
            # Should not happen, but enforce constraint
            model = nn.Sequential(nn.Linear(input_dim, num_classes))

        model = self._train_model(
            model=model,
            train_loader=train_loader,
            val_loader=val_loader,
            device=device,
            max_epochs=200,
            lr=1e-3,
            weight_decay=1e-4,
        )

        model.eval()
        return model
