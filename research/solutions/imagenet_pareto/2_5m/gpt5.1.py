import torch
import torch.nn as nn
import torch.optim as optim
import random
import numpy as np
import copy


class ResidualBlock(nn.Module):
    def __init__(self, hidden_dim: int, dropout: float = 0.1):
        super().__init__()
        self.fc = nn.Linear(hidden_dim, hidden_dim)
        self.norm = nn.LayerNorm(hidden_dim)
        self.act = nn.GELU()
        self.dropout = nn.Dropout(dropout)

    def forward(self, x):
        residual = x
        out = self.fc(x)
        out = self.norm(out)
        out = self.act(out)
        out = self.dropout(out)
        out = out + residual
        return out


class ResidualMLP(nn.Module):
    def __init__(self, input_dim: int, num_classes: int, hidden_dim: int, num_blocks: int, dropout: float = 0.1):
        super().__init__()
        self.fc_in = nn.Linear(input_dim, hidden_dim)
        self.norm_in = nn.LayerNorm(hidden_dim)
        self.act_in = nn.GELU()
        self.dropout_in = nn.Dropout(dropout)

        self.blocks = nn.ModuleList(
            [ResidualBlock(hidden_dim, dropout=dropout) for _ in range(num_blocks)]
        )

        self.norm_final = nn.LayerNorm(hidden_dim)
        self.fc_out = nn.Linear(hidden_dim, num_classes)

    def forward(self, x):
        x = self.fc_in(x)
        x = self.norm_in(x)
        x = self.act_in(x)
        x = self.dropout_in(x)

        for block in self.blocks:
            x = block(x)

        x = self.norm_final(x)
        x = self.fc_out(x)
        return x


class Solution:
    def __init__(self):
        pass

    def _set_seed(self, seed: int = 42):
        random.seed(seed)
        np.random.seed(seed)
        torch.manual_seed(seed)
        if torch.cuda.is_available():
            torch.cuda.manual_seed_all(seed)

    def _count_params(self, model: nn.Module) -> int:
        return sum(p.numel() for p in model.parameters() if p.requires_grad)

    def _build_model(self, input_dim: int, num_classes: int, param_limit: int) -> nn.Module:
        # Search over a small grid of widths and number of residual blocks
        width_candidates = list(range(256, 1217, 32))  # 256..1216 step 32
        block_candidates = [2, 3, 4, 5]

        best_model = None
        best_params = -1

        for num_blocks in block_candidates:
            for hidden_dim in width_candidates:
                model = ResidualMLP(
                    input_dim=input_dim,
                    num_classes=num_classes,
                    hidden_dim=hidden_dim,
                    num_blocks=num_blocks,
                    dropout=0.1,
                )
                n_params = self._count_params(model)
                if n_params <= param_limit and n_params > best_params:
                    best_params = n_params
                    best_model = model

        # Fallback: if for some reason nothing fits, use a simple smaller MLP
        if best_model is None:
            hidden_dim = min(512, max(128, param_limit // (input_dim + num_classes + 10)))
            model = nn.Sequential(
                nn.Linear(input_dim, hidden_dim),
                nn.ReLU(),
                nn.Linear(hidden_dim, num_classes),
            )
            if self._count_params(model) > param_limit:
                # As a last resort, logistic regression
                model = nn.Linear(input_dim, num_classes)
            best_model = model

        return best_model

    def _evaluate(self, model: nn.Module, data_loader, device: torch.device):
        model.eval()
        correct = 0
        total = 0
        loss_sum = 0.0
        criterion = nn.CrossEntropyLoss(label_smoothing=0.0)

        with torch.no_grad():
            for inputs, targets in data_loader:
                inputs = inputs.to(device).float()
                targets = targets.to(device).long()
                outputs = model(inputs)
                loss = criterion(outputs, targets)
                loss_sum += loss.item() * targets.size(0)
                preds = outputs.argmax(dim=1)
                correct += (preds == targets).sum().item()
                total += targets.numel()

        avg_loss = loss_sum / max(total, 1)
        accuracy = correct / max(total, 1)
        return avg_loss, accuracy

    def solve(self, train_loader, val_loader, metadata: dict = None) -> torch.nn.Module:
        if metadata is None:
            metadata = {}
        input_dim = int(metadata.get("input_dim", 384))
        num_classes = int(metadata.get("num_classes", 128))
        param_limit = int(metadata.get("param_limit", 2_500_000))
        device_str = metadata.get("device", "cpu")
        if "cuda" in device_str and not torch.cuda.is_available():
            device_str = "cpu"
        device = torch.device(device_str)

        self._set_seed(42)

        model = self._build_model(input_dim, num_classes, param_limit)
        model.to(device)

        # Ensure we respect the parameter limit
        n_params = self._count_params(model)
        if n_params > param_limit:
            # As a safety fallback, use a smaller simple model
            model = nn.Sequential(
                nn.Linear(input_dim, 512),
                nn.ReLU(),
                nn.Linear(512, num_classes),
            ).to(device)

        criterion = nn.CrossEntropyLoss(label_smoothing=0.05)
        optimizer = optim.AdamW(model.parameters(), lr=1e-3, weight_decay=5e-4)

        max_epochs = 120
        min_epochs = 30
        patience = 20
        best_val_acc = 0.0
        best_state = None
        no_improve_epochs = 0

        for epoch in range(max_epochs):
            model.train()
            for inputs, targets in train_loader:
                inputs = inputs.to(device).float()
                targets = targets.to(device).long()

                optimizer.zero_grad()
                outputs = model(inputs)
                loss = criterion(outputs, targets)
                loss.backward()
                torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=5.0)
                optimizer.step()

            # Validation
            val_loss, val_acc = self._evaluate(model, val_loader, device)

            if val_acc > best_val_acc + 1e-4:
                best_val_acc = val_acc
                best_state = copy.deepcopy(model.state_dict())
                no_improve_epochs = 0
            else:
                no_improve_epochs += 1

            if epoch + 1 >= min_epochs and no_improve_epochs >= patience:
                break

        if best_state is not None:
            model.load_state_dict(best_state)

        model.to(torch.device("cpu"))
        model.eval()
        return model