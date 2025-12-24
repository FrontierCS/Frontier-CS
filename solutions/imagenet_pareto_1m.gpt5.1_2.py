import torch
import torch.nn as nn
import torch.optim as optim
import random
import numpy as np
from copy import deepcopy


class ResidualBlock(nn.Module):
    def __init__(self, dim: int, dropout: float = 0.1):
        super().__init__()
        self.norm = nn.LayerNorm(dim)
        self.fc1 = nn.Linear(dim, dim * 2)
        self.fc2 = nn.Linear(dim * 2, dim)
        self.act = nn.GELU()
        self.dropout = nn.Dropout(dropout)

    def forward(self, x):
        residual = x
        out = self.norm(x)
        out = self.fc1(out)
        out = self.act(out)
        out = self.dropout(out)
        out = self.fc2(out)
        out = self.dropout(out)
        return out + residual


class MLPNet(nn.Module):
    def __init__(self, input_dim: int, num_classes: int, hidden_dim: int, num_blocks: int, dropout: float = 0.1):
        super().__init__()
        self.fc_in = nn.Linear(input_dim, hidden_dim)
        self.act_in = nn.GELU()
        self.blocks = nn.Sequential(*[ResidualBlock(hidden_dim, dropout) for _ in range(num_blocks)])
        self.norm_final = nn.LayerNorm(hidden_dim)
        self.head = nn.Linear(hidden_dim, num_classes)

    def forward(self, x):
        x = self.fc_in(x)
        x = self.act_in(x)
        x = self.blocks(x)
        x = self.norm_final(x)
        x = self.head(x)
        return x


class Solution:
    def _estimate_params(self, input_dim: int, num_classes: int, hidden_dim: int, num_blocks: int) -> int:
        # Formula derived from architecture:
        # fc_in: input_dim*hidden_dim + hidden_dim
        # each ResidualBlock: 4*hidden_dim^2 + 5*hidden_dim
        # norm_final: 2*hidden_dim
        # head: hidden_dim*num_classes + num_classes
        return (
            4 * num_blocks * hidden_dim * hidden_dim
            + (input_dim + num_classes + 3 + 5 * num_blocks) * hidden_dim
            + num_classes
        )

    def _choose_arch(self, input_dim: int, num_classes: int, param_limit: int):
        max_blocks = 3
        max_hidden = 512
        min_hidden = 64
        hidden_step = 8

        best_hidden = None
        best_blocks = None
        best_params = -1

        # Prefer deeper networks if they can get close (>=95%) to the parameter limit
        for blocks in range(max_blocks, 0, -1):
            local_best_hidden = None
            local_best_params = -1
            for hidden in range(max_hidden, min_hidden - 1, -hidden_step):
                p = self._estimate_params(input_dim, num_classes, hidden, blocks)
                if p <= param_limit and p > local_best_params:
                    local_best_params = p
                    local_best_hidden = hidden
            if local_best_hidden is not None:
                # If this depth can reach near the parameter limit, use it immediately
                if local_best_params >= 0.95 * param_limit:
                    return local_best_hidden, blocks
                if local_best_params > best_params:
                    best_params = local_best_params
                    best_hidden = local_best_hidden
                    best_blocks = blocks

        if best_hidden is None:
            # Fallback: aggressively shrink until under limit
            hidden = max_hidden
            blocks = 1
            while hidden > 8:
                p = self._estimate_params(input_dim, num_classes, hidden, blocks)
                if p <= param_limit:
                    best_hidden = hidden
                    best_blocks = blocks
                    break
                hidden //= 2
            if best_hidden is None:
                best_hidden = 8
                best_blocks = 1

        return best_hidden, best_blocks

    def _evaluate(self, model, data_loader, criterion, device):
        model.eval()
        total_loss = 0.0
        correct = 0
        total = 0
        with torch.no_grad():
            for inputs, targets in data_loader:
                inputs = inputs.to(device).float()
                targets = targets.to(device).long()
                outputs = model(inputs)
                loss = criterion(outputs, targets)
                total_loss += loss.item() * targets.size(0)
                preds = outputs.argmax(dim=1)
                correct += (preds == targets).sum().item()
                total += targets.numel()
        avg_loss = total_loss / max(total, 1)
        acc = correct / max(total, 1)
        return avg_loss, acc

    def _train_model(self, model, train_loader, val_loader, device, metadata):
        train_samples = metadata.get("train_samples", None)
        if train_samples is None or train_samples <= 5000:
            max_epochs = 250
        else:
            max_epochs = 80

        patience = 30
        label_smoothing = 0.1
        base_lr = 1e-3
        weight_decay = 1e-2
        dropout = 0.1  # kept constant; model already built with this

        criterion = nn.CrossEntropyLoss(label_smoothing=label_smoothing)
        optimizer = optim.AdamW(model.parameters(), lr=base_lr, weight_decay=weight_decay)
        scheduler = optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=max_epochs, eta_min=1e-5)

        best_state = deepcopy(model.state_dict())
        best_val_acc = 0.0
        epochs_no_improve = 0

        for epoch in range(max_epochs):
            model.train()
            for inputs, targets in train_loader:
                inputs = inputs.to(device).float()
                targets = targets.to(device).long()

                optimizer.zero_grad(set_to_none=True)
                outputs = model(inputs)
                loss = criterion(outputs, targets)
                loss.backward()
                torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=5.0)
                optimizer.step()

            if val_loader is not None:
                _, val_acc = self._evaluate(model, val_loader, criterion, device)
                if val_acc > best_val_acc + 1e-4:
                    best_val_acc = val_acc
                    best_state = deepcopy(model.state_dict())
                    epochs_no_improve = 0
                else:
                    epochs_no_improve += 1
                    if epochs_no_improve >= patience:
                        scheduler.step()
                        break
            scheduler.step()

        model.load_state_dict(best_state)
        return model

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
        if input_dim is None or num_classes is None:
            # Infer from a single batch if not provided
            for batch_inputs, batch_targets in train_loader:
                input_dim = batch_inputs.shape[1]
                num_classes = int(batch_targets.max().item() + 1)
                break

        param_limit = int(metadata.get("param_limit", 1_000_000))
        device_str = metadata.get("device", "cpu")
        if device_str == "cuda" and torch.cuda.is_available():
            device = torch.device("cuda")
        else:
            device = torch.device("cpu")

        hidden_dim, num_blocks = self._choose_arch(input_dim, num_classes, param_limit)
        dropout = 0.1
        model = MLPNet(input_dim, num_classes, hidden_dim, num_blocks, dropout=dropout).to(device)

        # Safety check against parameter limit; if exceeded, shrink progressively
        param_count = sum(p.numel() for p in model.parameters() if p.requires_grad)
        if param_count > param_limit:
            # Fallback shrinking strategy
            while (param_count > param_limit) and (hidden_dim > 32 or num_blocks > 1):
                if hidden_dim > 32:
                    hidden_dim = max(32, hidden_dim - 16)
                elif num_blocks > 1:
                    num_blocks -= 1
                model = MLPNet(input_dim, num_classes, hidden_dim, num_blocks, dropout=dropout).to(device)
                param_count = sum(p.numel() for p in model.parameters() if p.requires_grad)
            if param_count > param_limit:
                hidden_dim = 32
                num_blocks = 1
                model = MLPNet(input_dim, num_classes, hidden_dim, num_blocks, dropout=dropout).to(device)

        self._train_model(model, train_loader, val_loader, device, metadata)
        return model
