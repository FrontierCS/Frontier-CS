import math
import copy
import random
from typing import List, Tuple, Optional, Dict

import torch
import torch.nn as nn
import torch.nn.functional as F


def set_seed(seed: int = 1337):
    random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)


def count_trainable_params(model: nn.Module) -> int:
    return sum(p.numel() for p in model.parameters() if p.requires_grad)


class MLPNet(nn.Module):
    def __init__(
        self,
        input_dim: int,
        num_classes: int,
        hidden_dims: List[int],
        dropout: float = 0.15,
        use_layernorm: bool = True,
        input_layernorm: bool = True,
        activation: str = "gelu",
    ):
        super().__init__()
        self.input_dim = input_dim
        self.num_classes = num_classes
        self.hidden_dims = hidden_dims
        self.use_layernorm = use_layernorm
        self.input_layernorm = input_layernorm
        self.dropout_p = dropout

        act = nn.GELU if activation.lower() == "gelu" else nn.ReLU

        layers = []
        in_dim = input_dim

        if self.input_layernorm:
            self.input_ln = nn.LayerNorm(in_dim)
        else:
            self.input_ln = None

        for h in hidden_dims:
            layers.append(nn.Linear(in_dim, h))
            if self.use_layernorm:
                layers.append(nn.LayerNorm(h))
            layers.append(act())
            if dropout > 0.0:
                layers.append(nn.Dropout(dropout))
            in_dim = h

        self.features = nn.Sequential(*layers)
        self.head = nn.Linear(in_dim, num_classes)

        self._init_weights()

    def _init_weights(self):
        for m in self.modules():
            if isinstance(m, nn.Linear):
                nn.init.kaiming_normal_(m.weight, nonlinearity="relu")
                if m.bias is not None:
                    nn.init.zeros_(m.bias)
            elif isinstance(m, nn.LayerNorm):
                nn.init.ones_(m.weight)
                nn.init.zeros_(m.bias)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        if self.input_ln is not None:
            x = self.input_ln(x)
        x = self.features(x)
        x = self.head(x)
        return x


class Solution:
    def _build_candidates(self, input_dim: int, num_classes: int) -> List[List[int]]:
        # High-to-low capacity candidates; ensure a diverse set while controlling parameter budget
        candidates = [
            [1024, 512],
            [960, 512],
            [896, 512],
            [896, 448],
            [832, 512],
            [832, 448],
            [768, 512, 256],
            [768, 512],
            [768, 384],
            [704, 512, 256],
            [704, 384],
            [640, 512, 256],
            [640, 384],
            [640, 320, 256],
            [576, 512, 256],
            [576, 384, 256],
            [512, 512, 512],
            [512, 512],
            [512, 384, 256],
            [512, 384],
            [512, 320, 256, 256],
            [448, 384, 256, 256],
            [384, 384, 384],
            [384, 320, 256, 256],
            [384, 256, 256, 256],
            [320, 256, 256, 256],
        ]
        return candidates

    def _build_best_model_under_limit(
        self,
        input_dim: int,
        num_classes: int,
        param_limit: int,
        device: str,
    ) -> Tuple[nn.Module, List[int]]:
        best_model = None
        best_dims = None
        best_params = -1

        # Try candidates
        for dims in self._build_candidates(input_dim, num_classes):
            model = MLPNet(
                input_dim=input_dim,
                num_classes=num_classes,
                hidden_dims=dims,
                dropout=0.15,
                use_layernorm=True,
                input_layernorm=True,
                activation="gelu",
            ).to(device)
            n_params = count_trainable_params(model)
            if n_params <= param_limit and n_params > best_params:
                best_model = model
                best_dims = dims
                best_params = n_params

        # Fallback progressive search if none fit (shouldn't happen with 1M limit)
        if best_model is None:
            # Try decreasing widths until fit
            width = 512
            dims = [width, width]
            while True:
                model = MLPNet(
                    input_dim=input_dim,
                    num_classes=num_classes,
                    hidden_dims=dims,
                    dropout=0.1,
                    use_layernorm=True,
                    input_layernorm=True,
                    activation="gelu",
                ).to(device)
                if count_trainable_params(model) <= param_limit:
                    best_model = model
                    best_dims = dims
                    break
                width = max(128, width - 64)
                dims = [width, width]

        return best_model, best_dims

    @torch.no_grad()
    def _evaluate(self, model: nn.Module, loader, device: str) -> Tuple[float, float]:
        model.eval()
        total_loss = 0.0
        total = 0
        correct = 0
        for inputs, targets in loader:
            inputs = inputs.to(device, non_blocking=False)
            targets = targets.to(device, non_blocking=False)
            outputs = model(inputs)
            loss = F.cross_entropy(outputs, targets)
            total_loss += loss.item() * targets.size(0)
            preds = outputs.argmax(dim=1)
            correct += (preds == targets).sum().item()
            total += targets.numel()
        avg_loss = total_loss / max(1, total)
        acc = correct / max(1, total)
        return acc, avg_loss

    def _train(
        self,
        model: nn.Module,
        train_loader,
        val_loader,
        device: str,
        epochs: int,
        lr: float,
        weight_decay: float,
        label_smoothing: float,
        patience: int,
        max_grad_norm: float = 2.0,
    ) -> nn.Module:
        optimizer = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=weight_decay)
        scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=epochs, eta_min=lr * 0.01)

        best_state = copy.deepcopy(model.state_dict())
        best_acc = -1.0
        epochs_no_improve = 0

        for epoch in range(epochs):
            model.train()
            for inputs, targets in train_loader:
                inputs = inputs.to(device, non_blocking=False)
                targets = targets.to(device, non_blocking=False)
                optimizer.zero_grad(set_to_none=True)
                outputs = model(inputs)
                loss = F.cross_entropy(outputs, targets, label_smoothing=label_smoothing)
                loss.backward()
                if max_grad_norm is not None and max_grad_norm > 0:
                    torch.nn.utils.clip_grad_norm_(model.parameters(), max_grad_norm)
                optimizer.step()

            scheduler.step()

            if val_loader is not None:
                val_acc, _ = self._evaluate(model, val_loader, device)
                if val_acc > best_acc:
                    best_acc = val_acc
                    best_state = copy.deepcopy(model.state_dict())
                    epochs_no_improve = 0
                else:
                    epochs_no_improve += 1
                    if epochs_no_improve >= patience:
                        break

        model.load_state_dict(best_state)
        return model

    def solve(self, train_loader, val_loader, metadata: dict = None) -> torch.nn.Module:
        set_seed(1337)

        if metadata is None:
            metadata = {}
        input_dim = int(metadata.get("input_dim", 384))
        num_classes = int(metadata.get("num_classes", 128))
        param_limit = int(metadata.get("param_limit", 1_000_000))
        device = str(metadata.get("device", "cpu"))

        model, dims = self._build_best_model_under_limit(input_dim, num_classes, param_limit, device)

        # Hyperparameters based on model size
        n_params = count_trainable_params(model)
        if n_params > 900_000:
            lr = 3e-3
            epochs = 140
            dropout = 0.15
        elif n_params > 700_000:
            lr = 3e-3
            epochs = 150
            dropout = 0.15
        else:
            lr = 2.5e-3
            epochs = 160
            dropout = 0.12

        # Adjust dropout if needed
        if isinstance(model, MLPNet):
            model.dropout_p = dropout
            # Rebuild features with adjusted dropout if different from initial
            if abs(dropout - 0.15) > 1e-6:
                model = MLPNet(
                    input_dim=input_dim,
                    num_classes=num_classes,
                    hidden_dims=dims,
                    dropout=dropout,
                    use_layernorm=True,
                    input_layernorm=True,
                    activation="gelu",
                ).to(device)

        weight_decay = 1e-4
        label_smoothing = 0.05
        patience = max(20, epochs // 5)

        trained_model = self._train(
            model=model,
            train_loader=train_loader,
            val_loader=val_loader,
            device=device,
            epochs=epochs,
            lr=lr,
            weight_decay=weight_decay,
            label_smoothing=label_smoothing,
            patience=patience,
            max_grad_norm=2.0,
        )

        trained_model.eval()
        return trained_model