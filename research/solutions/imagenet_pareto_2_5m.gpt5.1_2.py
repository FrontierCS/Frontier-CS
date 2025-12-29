import torch
import torch.nn as nn
import torch.nn.functional as F
from typing import Dict, Any, Optional


class LargeMLP(nn.Module):
    def __init__(self, input_dim: int, num_classes: int, dropout: float = 0.2):
        super().__init__()
        self.input_dim = input_dim
        self.net = nn.Sequential(
            nn.LayerNorm(input_dim),
            nn.Linear(input_dim, 1024),
            nn.GELU(),
            nn.Dropout(dropout),

            nn.LayerNorm(1024),
            nn.Linear(1024, 1024),
            nn.GELU(),
            nn.Dropout(dropout),

            nn.LayerNorm(1024),
            nn.Linear(1024, 512),
            nn.GELU(),
            nn.Dropout(dropout),

            nn.LayerNorm(512),
            nn.Linear(512, 512),
            nn.GELU(),
            nn.Dropout(dropout),

            nn.LayerNorm(512),
            nn.Linear(512, 256),
            nn.GELU(),
            nn.Dropout(dropout),

            nn.LayerNorm(256),
            nn.Linear(256, num_classes),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = x.view(x.size(0), -1)
        return self.net(x)


class BaselineMLP(nn.Module):
    def __init__(self, input_dim: int, num_classes: int, hidden_dim: int = 1024, dropout: float = 0.1):
        super().__init__()
        self.input_dim = input_dim
        self.net = nn.Sequential(
            nn.LayerNorm(input_dim),
            nn.Linear(input_dim, hidden_dim),
            nn.GELU(),
            nn.Dropout(dropout),

            nn.LayerNorm(hidden_dim),
            nn.Linear(hidden_dim, hidden_dim),
            nn.GELU(),
            nn.Dropout(dropout),

            nn.LayerNorm(hidden_dim),
            nn.Linear(hidden_dim, num_classes),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = x.view(x.size(0), -1)
        return self.net(x)


class Solution:
    def __init__(self):
        pass

    @staticmethod
    def _count_params(model: nn.Module) -> int:
        return sum(p.numel() for p in model.parameters() if p.requires_grad)

    def _build_model(self, input_dim: int, num_classes: int, param_limit: int, device: torch.device) -> nn.Module:
        # Try large MLP first
        model = LargeMLP(input_dim, num_classes, dropout=0.2).to(device)
        if self._count_params(model) <= param_limit:
            return model

        # Fallback: search for largest baseline MLP within limit
        best_model: Optional[nn.Module] = None
        best_hidden = 0
        for hidden_dim in range(1024, 63, -64):
            candidate = BaselineMLP(input_dim, num_classes, hidden_dim=hidden_dim, dropout=0.1).to(device)
            if self._count_params(candidate) <= param_limit:
                best_model = candidate
                best_hidden = hidden_dim
                break

        if best_model is None:
            # Very small limit: use single hidden layer
            for hidden_dim in range(512, 15, -16):
                candidate = nn.Sequential(
                    nn.LayerNorm(input_dim),
                    nn.Linear(input_dim, hidden_dim),
                    nn.GELU(),
                    nn.Linear(hidden_dim, num_classes),
                ).to(device)
                if self._count_params(candidate) <= param_limit:
                    best_model = candidate
                    break

        if best_model is None:
            # As an extreme fallback, a linear classifier
            best_model = nn.Linear(input_dim, num_classes).to(device)

        return best_model

    def solve(self, train_loader, val_loader, metadata: dict = None) -> torch.nn.Module:
        if metadata is None:
            metadata = {}

        torch.manual_seed(42)

        device_str = metadata.get("device", "cpu")
        device = torch.device(device_str)

        # Extract metadata with fallbacks
        if "input_dim" in metadata:
            input_dim = int(metadata["input_dim"])
        else:
            sample_batch = next(iter(train_loader))[0]
            input_dim = int(sample_batch.view(sample_batch.size(0), -1).size(1))

        if "num_classes" in metadata:
            num_classes = int(metadata["num_classes"])
        else:
            # Fallback: infer from train_loader targets
            classes = set()
            for _, y in train_loader:
                classes.update(y.view(-1).tolist())
            num_classes = max(classes) + 1 if classes else 1

        param_limit = int(metadata.get("param_limit", 2500000))

        model = self._build_model(input_dim, num_classes, param_limit, device)

        # Training setup
        lr = 3e-3
        weight_decay = 1e-2
        max_epochs = 160
        patience = 20

        criterion_train = nn.CrossEntropyLoss(label_smoothing=0.05)
        optimizer = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=weight_decay)
        scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=max_epochs, eta_min=1e-4)

        best_val_acc = 0.0
        best_state = None
        epochs_no_improve = 0

        for epoch in range(max_epochs):
            model.train()
            for inputs, targets in train_loader:
                inputs = inputs.to(device, dtype=torch.float32)
                targets = targets.to(device, dtype=torch.long)

                optimizer.zero_grad()
                outputs = model(inputs)
                loss = criterion_train(outputs, targets)
                loss.backward()
                nn.utils.clip_grad_norm_(model.parameters(), max_norm=5.0)
                optimizer.step()

            # Validation
            model.eval()
            correct = 0
            total = 0
            with torch.no_grad():
                for inputs, targets in val_loader:
                    inputs = inputs.to(device, dtype=torch.float32)
                    targets = targets.to(device, dtype=torch.long)
                    outputs = model(inputs)
                    preds = outputs.argmax(dim=1)
                    correct += (preds == targets).sum().item()
                    total += targets.numel()

            val_acc = correct / total if total > 0 else 0.0

            if val_acc > best_val_acc + 1e-4:
                best_val_acc = val_acc
                best_state = {k: v.cpu().clone() for k, v in model.state_dict().items()}
                epochs_no_improve = 0
            else:
                epochs_no_improve += 1

            scheduler.step()

            if epochs_no_improve >= patience:
                break

        if best_state is not None:
            model.load_state_dict(best_state)

        model.to(device)
        model.eval()
        return model