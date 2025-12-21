import torch
import torch.nn as nn
import torch.nn.functional as F
import random
import numpy as np
from copy import deepcopy


def set_seed(seed: int = 42):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)


def count_trainable_params(model: nn.Module) -> int:
    return sum(p.numel() for p in model.parameters() if p.requires_grad)


class ResidualBlock(nn.Module):
    def __init__(self, dim: int, dropout: float = 0.3):
        super().__init__()
        self.fc1 = nn.Linear(dim, dim)
        self.bn1 = nn.BatchNorm1d(dim)
        self.fc2 = nn.Linear(dim, dim)
        self.bn2 = nn.BatchNorm1d(dim)
        self.dropout = nn.Dropout(dropout)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        residual = x
        out = self.fc1(x)
        out = self.bn1(out)
        out = F.relu(out, inplace=True)
        out = self.dropout(out)
        out = self.fc2(out)
        out = self.bn2(out)
        out = self.dropout(out)
        out = out + residual
        out = F.relu(out, inplace=True)
        return out


class MLPModel(nn.Module):
    def __init__(self, input_dim: int, num_classes: int, hidden_dim: int, dropout: float = 0.3):
        super().__init__()
        self.fc_in = nn.Linear(input_dim, hidden_dim)
        self.bn_in = nn.BatchNorm1d(hidden_dim)
        self.block1 = ResidualBlock(hidden_dim, dropout=dropout)
        self.fc_out = nn.Linear(hidden_dim, num_classes)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self.fc_in(x)
        x = self.bn_in(x)
        x = F.relu(x, inplace=True)
        x = self.block1(x)
        x = self.fc_out(x)
        return x


def train_one_epoch(model, loader, optimizer, criterion, device):
    model.train()
    running_loss = 0.0
    correct = 0
    total = 0
    for inputs, targets in loader:
        inputs = inputs.to(device)
        targets = targets.to(device)

        optimizer.zero_grad()
        outputs = model(inputs)
        loss = criterion(outputs, targets)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=5.0)
        optimizer.step()

        batch_size = targets.size(0)
        running_loss += loss.item() * batch_size
        preds = outputs.argmax(dim=1)
        correct += (preds == targets).sum().item()
        total += batch_size

    epoch_loss = running_loss / max(total, 1)
    epoch_acc = correct / max(total, 1)
    return epoch_loss, epoch_acc


@torch.no_grad()
def evaluate(model, loader, criterion, device):
    model.eval()
    running_loss = 0.0
    correct = 0
    total = 0
    for inputs, targets in loader:
        inputs = inputs.to(device)
        targets = targets.to(device)

        outputs = model(inputs)
        loss = criterion(outputs, targets)

        batch_size = targets.size(0)
        running_loss += loss.item() * batch_size
        preds = outputs.argmax(dim=1)
        correct += (preds == targets).sum().item()
        total += batch_size

    epoch_loss = running_loss / max(total, 1)
    epoch_acc = correct / max(total, 1)
    return epoch_loss, epoch_acc


class Solution:
    def solve(self, train_loader, val_loader, metadata: dict = None) -> torch.nn.Module:
        if metadata is None:
            metadata = {}

        set_seed(42)

        input_dim = int(metadata.get("input_dim", 384))
        num_classes = int(metadata.get("num_classes", 128))
        param_limit = int(metadata.get("param_limit", 500_000))
        device = torch.device(metadata.get("device", "cpu"))

        # Choose the largest hidden size that satisfies the parameter constraint
        candidate_hidden_dims = [512, 448, 416, 384, 352, 320, 288, 256, 224, 192]
        model = None
        chosen_hidden = None
        for h in candidate_hidden_dims:
            candidate_model = MLPModel(input_dim, num_classes, h, dropout=0.3)
            n_params = count_trainable_params(candidate_model)
            if n_params <= param_limit:
                model = candidate_model
                chosen_hidden = h
                break

        if model is None or chosen_hidden is None:
            # Very conservative fallback
            fallback_hidden = 128
            model = MLPModel(input_dim, num_classes, fallback_hidden, dropout=0.3)

        model.to(device)

        # Training hyperparameters
        max_epochs = 120
        patience = 20
        base_lr = 3e-3
        weight_decay = 1e-4

        optimizer = torch.optim.AdamW(model.parameters(), lr=base_lr, weight_decay=weight_decay)
        scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=max_epochs)
        criterion = nn.CrossEntropyLoss(label_smoothing=0.05)

        best_model_state = deepcopy(model.state_dict())
        best_val_acc = 0.0
        epochs_no_improve = 0

        for epoch in range(max_epochs):
            train_one_epoch(model, train_loader, optimizer, criterion, device)
            val_loss, val_acc = evaluate(model, val_loader, criterion, device)

            scheduler.step()

            if val_acc > best_val_acc + 1e-4:
                best_val_acc = val_acc
                best_model_state = deepcopy(model.state_dict())
                epochs_no_improve = 0
            else:
                epochs_no_improve += 1
                if epochs_no_improve >= patience:
                    break

        model.load_state_dict(best_model_state)
        model.to("cpu")
        return model
