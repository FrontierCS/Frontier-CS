import torch
import torch.nn as nn
import torch.nn.functional as F
import copy
from typing import Dict, Any, Optional, Tuple


class MLPNet(nn.Module):
    def __init__(self, input_dim: int, num_classes: int, h1: int, h2: int, dropout: float = 0.2):
        super().__init__()
        self.fc1 = nn.Linear(input_dim, h1)
        self.bn1 = nn.BatchNorm1d(h1)
        self.fc2 = nn.Linear(h1, h2)
        self.bn2 = nn.BatchNorm1d(h2)
        self.fc3 = nn.Linear(h2, num_classes)
        self.dropout = dropout

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        if x.dim() > 2:
            x = x.view(x.size(0), -1)
        x = self.fc1(x)
        x = self.bn1(x)
        x = F.relu(x, inplace=True)
        x = F.dropout(x, p=self.dropout, training=self.training)
        x = self.fc2(x)
        x = self.bn2(x)
        x = F.relu(x, inplace=True)
        x = F.dropout(x, p=self.dropout, training=self.training)
        x = self.fc3(x)
        return x


class Solution:
    def __init__(self):
        # Ensure deterministic-ish behavior
        torch.manual_seed(42)

    @staticmethod
    def _count_params(model: nn.Module) -> int:
        return sum(p.numel() for p in model.parameters() if p.requires_grad)

    def _build_model(
        self,
        input_dim: int,
        num_classes: int,
        param_limit: int,
    ) -> nn.Module:
        # Candidate (h1, h2) pairs ordered from highest to lower capacity
        candidates = [
            (512, 468),  # ~499k params for 384x128
            (512, 384),
            (640, 320),
            (512, 320),
            (384, 384),
            (384, 256),
            (256, 256),
            (256, 192),
            (192, 192),
            (128, 128),
        ]

        dropout = 0.2

        for h1, h2 in candidates:
            model = MLPNet(input_dim, num_classes, h1, h2, dropout=dropout)
            if self._count_params(model) <= param_limit:
                return model

        # Fallback: simple 1-hidden-layer MLP well under budget
        # Hidden size chosen based on limit and dimensions
        approx_hidden = max(64, min(256, param_limit // (input_dim + num_classes + 64)))
        model = nn.Sequential(
            nn.Linear(input_dim, approx_hidden),
            nn.ReLU(inplace=True),
            nn.Linear(approx_hidden, num_classes),
        )
        return model

    def solve(self, train_loader, val_loader, metadata: Dict[str, Any] = None) -> torch.nn.Module:
        if metadata is None:
            metadata = {}

        input_dim = int(metadata.get("input_dim", 384))
        num_classes = int(metadata.get("num_classes", 128))
        param_limit = int(metadata.get("param_limit", 500_000))
        device = metadata.get("device", "cpu")

        train_samples = metadata.get("train_samples", None)

        # Build model under parameter budget
        model = self._build_model(input_dim, num_classes, param_limit)
        model.to(device)

        # Training hyperparameters
        if train_samples is not None:
            if train_samples <= 4096:
                max_epochs = 220
            elif train_samples <= 16384:
                max_epochs = 140
            else:
                max_epochs = 80
        else:
            max_epochs = 180

        patience = min(40, max(10, max_epochs // 5))

        # Optimizer, scheduler, loss
        # Slight weight decay and label smoothing to regularize big model on small data
        optimizer = torch.optim.AdamW(model.parameters(), lr=2.5e-3, weight_decay=3e-4)
        scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=max_epochs, eta_min=1e-5)

        try:
            criterion = nn.CrossEntropyLoss(label_smoothing=0.05)
        except TypeError:
            # In case of very old PyTorch without label_smoothing (shouldn't happen in stated environment)
            criterion = nn.CrossEntropyLoss()

        def evaluate(m: nn.Module, loader) -> Tuple[float, float]:
            if loader is None:
                return 0.0, 0.0
            m.eval()
            total_loss = 0.0
            correct = 0
            total = 0
            with torch.no_grad():
                for inputs, targets in loader:
                    inputs = inputs.to(device)
                    targets = targets.to(device)
                    outputs = m(inputs)
                    loss = criterion(outputs, targets)
                    bs = targets.size(0)
                    total_loss += loss.item() * bs
                    preds = outputs.argmax(dim=1)
                    correct += (preds == targets).sum().item()
                    total += bs
            if total == 0:
                return 0.0, 0.0
            return total_loss / total, correct / total

        best_state: Optional[dict] = None
        best_val_acc = -1.0
        best_val_loss = float("inf")
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
                nn.utils.clip_grad_norm_(model.parameters(), max_norm=5.0)
                optimizer.step()

            # Validation
            if val_loader is not None:
                val_loss, val_acc = evaluate(model, val_loader)

                improved = False
                if val_acc > best_val_acc:
                    improved = True
                elif val_acc == best_val_acc and val_loss < best_val_loss:
                    improved = True

                if improved:
                    best_val_acc = val_acc
                    best_val_loss = val_loss
                    best_state = copy.deepcopy(model.state_dict())
                    epochs_no_improve = 0
                else:
                    epochs_no_improve += 1
                    if epochs_no_improve >= patience:
                        scheduler.step()
                        break
            scheduler.step()

        # Load best validation model if available
        if best_state is not None and val_loader is not None:
            model.load_state_dict(best_state)

        model.to("cpu")
        return model
