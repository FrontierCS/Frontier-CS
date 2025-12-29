import math
import torch
import torch.nn as nn
import torch.nn.functional as F


class MLPNet(nn.Module):
    def __init__(self, input_dim: int, num_classes: int, hidden_dim: int, dropout: float = 0.1):
        super().__init__()
        self.fc1 = nn.Linear(input_dim, hidden_dim)
        self.bn1 = nn.BatchNorm1d(hidden_dim)

        self.fc2 = nn.Linear(hidden_dim, hidden_dim)
        self.bn2 = nn.BatchNorm1d(hidden_dim)

        self.fc3 = nn.Linear(hidden_dim, hidden_dim)
        self.bn3 = nn.BatchNorm1d(hidden_dim)

        self.fc4 = nn.Linear(hidden_dim, hidden_dim)
        self.bn4 = nn.BatchNorm1d(hidden_dim)

        self.fc_out = nn.Linear(hidden_dim, num_classes)

        self.dropout = nn.Dropout(dropout)

    def forward(self, x):
        x = self.fc1(x)
        x = self.bn1(x)
        x = F.gelu(x)
        x = self.dropout(x)

        x = self.fc2(x)
        x = self.bn2(x)
        x = F.gelu(x)
        x = self.dropout(x)

        x = self.fc3(x)
        x = self.bn3(x)
        x = F.gelu(x)
        x = self.dropout(x)

        x = self.fc4(x)
        x = self.bn4(x)
        x = F.gelu(x)
        x = self.dropout(x)

        x = self.fc_out(x)
        return x


class Solution:
    def _compute_hidden_dim(self, input_dim: int, num_classes: int, param_limit: int) -> int:
        """
        Compute maximum hidden width for a 4-hidden-layer MLP with BatchNorm under param_limit.

        Param count formula for architecture used:
            3*W^2 + (input_dim + num_classes + 12)*W + num_classes
        where:
            - 3*W^2 : 3 hidden Linear W->W layers
            - (input_dim+1)*W : first Linear
            - (W+1)*num_classes : output Linear
            - +8W : 4 BatchNorm1d layers (weight+bias each)
            -> combined linear term coefficient is (input_dim + num_classes + 12)
        """
        if param_limit <= 0:
            return 32

        a = input_dim + num_classes + 12  # linear term coefficient
        c = num_classes

        # Solve 3W^2 + aW + c <= param_limit for W (quadratic formula)
        # Discriminant: a^2 + 12 * (param_limit - c)
        disc = a * a + 12 * max(param_limit - c, 0)
        sqrt_disc = math.isqrt(disc)
        # Ensure sqrt_disc^2 <= disc
        while (sqrt_disc + 1) * (sqrt_disc + 1) <= disc:
            sqrt_disc += 1
        while sqrt_disc * sqrt_disc > disc:
            sqrt_disc -= 1

        # Compute candidate width
        w = ( -a + sqrt_disc ) // 6
        if w < 1:
            w = 1

        def param_count(w_):
            return 3 * (w_ ** 2) + a * w_ + c

        # Adjust downwards until within limit
        while w > 1 and param_count(w) > param_limit:
            w -= 1

        # Put a practical upper bound to avoid extreme widths if param_limit is huge
        w = max(32, min(w, 4096))
        return int(w)

    def solve(self, train_loader, val_loader, metadata: dict = None) -> torch.nn.Module:
        if metadata is None:
            raise ValueError("metadata must be provided")

        input_dim = int(metadata["input_dim"])
        num_classes = int(metadata["num_classes"])
        param_limit = int(metadata["param_limit"])
        device_str = metadata.get("device", "cpu")
        device = torch.device(device_str)

        # Compute hidden dimension under parameter budget
        hidden_dim = self._compute_hidden_dim(input_dim, num_classes, param_limit)

        # Build model and ensure parameter constraint is respected
        model = MLPNet(input_dim, num_classes, hidden_dim, dropout=0.1).to(device)

        def count_params(m):
            return sum(p.numel() for p in m.parameters() if p.requires_grad)

        param_count = count_params(model)
        # Safety adjustment if for any reason we exceed the limit
        while param_count > param_limit and hidden_dim > 1:
            hidden_dim = max(1, hidden_dim - 16)
            model = MLPNet(input_dim, num_classes, hidden_dim, dropout=0.1).to(device)
            param_count = count_params(model)

        # Training setup
        max_epochs = 120
        patience = 20

        # Loss with mild label smoothing
        criterion = nn.CrossEntropyLoss(label_smoothing=0.05)

        optimizer = torch.optim.AdamW(model.parameters(), lr=1e-3, weight_decay=1e-4)
        scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(
            optimizer, T_max=max_epochs, eta_min=1e-5
        )

        best_val_acc = 0.0
        best_state = None
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
            model.eval()
            correct = 0
            total = 0
            with torch.no_grad():
                for inputs, targets in val_loader:
                    inputs = inputs.to(device)
                    targets = targets.to(device)
                    outputs = model(inputs)
                    loss = criterion(outputs, targets)
                    preds = outputs.argmax(dim=1)
                    correct += (preds == targets).sum().item()
                    total += targets.size(0)

            val_acc = correct / total if total > 0 else 0.0
            scheduler.step()

            if val_acc > best_val_acc + 1e-4:
                best_val_acc = val_acc
                # Store a CPU copy of the best state dict
                best_state = {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}
                epochs_no_improve = 0
            else:
                epochs_no_improve += 1
                if epochs_no_improve >= patience:
                    break

        if best_state is not None:
            model.load_state_dict(best_state)

        model.to(device)
        model.eval()
        return model