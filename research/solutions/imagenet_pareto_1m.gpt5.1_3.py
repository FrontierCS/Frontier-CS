import torch
import torch.nn as nn
import numpy as np
import random
import copy


class MLPNet(nn.Module):
    def __init__(self, input_dim, num_classes, hidden_sizes, dropout=0.1):
        super().__init__()
        layers = []
        in_features = input_dim
        for h in hidden_sizes:
            layers.append(nn.Linear(in_features, h))
            layers.append(nn.BatchNorm1d(h))
            layers.append(nn.GELU())
            if dropout and dropout > 0.0:
                layers.append(nn.Dropout(p=dropout))
            in_features = h
        layers.append(nn.Linear(in_features, num_classes))
        self.net = nn.Sequential(*layers)

    def forward(self, x):
        x = x.view(x.size(0), -1)
        return self.net(x)


class Solution:
    def __init__(self):
        pass

    def _set_seed(self, seed: int = 42):
        torch.manual_seed(seed)
        random.seed(seed)
        np.random.seed(seed)

    def _count_trainable_params(self, model: nn.Module) -> int:
        return sum(p.numel() for p in model.parameters() if p.requires_grad)

    def _evaluate(self, model: nn.Module, data_loader, device: torch.device) -> float:
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
        max_epochs: int = 200,
        es_patience: int = 40,
    ):
        criterion = nn.CrossEntropyLoss()
        optimizer = torch.optim.AdamW(model.parameters(), lr=3e-3, weight_decay=1e-4)
        scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
            optimizer,
            mode="max",
            factor=0.5,
            patience=10,
            threshold=1e-4,
            min_lr=1e-5,
            verbose=False,
        )

        best_state = copy.deepcopy(model.state_dict())
        best_val_acc = 0.0
        epochs_no_improve = 0

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

            if val_loader is not None:
                val_acc = self._evaluate(model, val_loader, device)
                scheduler.step(val_acc)

                if val_acc > best_val_acc + 1e-4:
                    best_val_acc = val_acc
                    best_state = copy.deepcopy(model.state_dict())
                    epochs_no_improve = 0
                else:
                    epochs_no_improve += 1
                    if epochs_no_improve >= es_patience:
                        break

        if val_loader is not None and best_state is not None:
            model.load_state_dict(best_state)

    def solve(self, train_loader, val_loader, metadata: dict = None) -> torch.nn.Module:
        self._set_seed(42)

        if metadata is None:
            input_dim = 384
            num_classes = 128
            param_limit = 1_000_000
            device_str = "cpu"
        else:
            input_dim = int(metadata.get("input_dim", 384))
            num_classes = int(metadata.get("num_classes", 128))
            param_limit = int(metadata.get("param_limit", 1_000_000))
            device_str = metadata.get("device", "cpu")

        device = torch.device(device_str)

        candidate_archs = [
            [1024, 1024],
            [1024],
            [896, 896],
            [768, 768],
            [512, 512, 512],
            [512, 512],
            [512],
            [384, 384, 384],
            [384, 384],
            [384],
        ]

        dropout = 0.1
        best_model = None
        best_param_count = -1

        for hidden_sizes in candidate_archs:
            model = MLPNet(input_dim, num_classes, hidden_sizes, dropout=dropout)
            param_count = self._count_trainable_params(model)
            if param_count <= param_limit and param_count > best_param_count:
                best_param_count = param_count
                best_model = model

        if best_model is None:
            # Fallback to a very small model if param_limit is extremely low
            fallback_hidden = [128]
            best_model = MLPNet(input_dim, num_classes, fallback_hidden, dropout=0.0)
            if self._count_trainable_params(best_model) > param_limit:
                # Last-resort tiny model
                best_model = MLPNet(input_dim, num_classes, [], dropout=0.0)

        best_model.to(device)

        max_epochs = 200
        es_patience = 40
        self._train_model(best_model, train_loader, val_loader, device, max_epochs, es_patience)

        return best_model