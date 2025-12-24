import math
import copy
import torch
import torch.nn as nn
import torch.optim as optim


class InputNormalizer(nn.Module):
    def __init__(self, mean: torch.Tensor, std: torch.Tensor):
        super().__init__()
        std = std.clone()
        std[std < 1e-6] = 1.0
        self.register_buffer("mean", mean)
        self.register_buffer("std", std)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return (x - self.mean) / self.std


class ResidualBlock(nn.Module):
    def __init__(self, width: int, dropout: float = 0.1):
        super().__init__()
        self.fc1 = nn.Linear(width, width)
        self.bn1 = nn.BatchNorm1d(width)
        self.fc2 = nn.Linear(width, width)
        self.bn2 = nn.BatchNorm1d(width)
        self.act = nn.GELU()
        self.dropout = nn.Dropout(dropout)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        out = self.fc1(x)
        out = self.bn1(out)
        out = self.act(out)
        out = self.fc2(out)
        out = self.bn2(out)
        out = self.dropout(out)
        out = out + x
        out = self.act(out)
        return out


class MLPResNet(nn.Module):
    def __init__(
        self,
        input_dim: int,
        num_classes: int,
        width: int,
        num_blocks: int,
        dropout: float = 0.1,
        mean: torch.Tensor = None,
        std: torch.Tensor = None,
    ):
        super().__init__()
        if mean is not None and std is not None:
            self.input_norm = InputNormalizer(mean, std)
        else:
            self.input_norm = None

        self.fc_in = nn.Linear(input_dim, width)
        self.bn_in = nn.BatchNorm1d(width)
        self.act = nn.GELU()
        self.blocks = nn.ModuleList(
            [ResidualBlock(width, dropout=dropout) for _ in range(num_blocks)]
        )
        self.fc_out = nn.Linear(width, num_classes)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        if self.input_norm is not None:
            x = self.input_norm(x)
        x = self.fc_in(x)
        x = self.bn_in(x)
        x = self.act(x)
        for block in self.blocks:
            x = block(x)
        x = self.fc_out(x)
        return x


def compute_mean_std(loader, input_dim: int, device: torch.device) -> (torch.Tensor, torch.Tensor):
    total = 0
    mean = torch.zeros(input_dim, dtype=torch.float32)
    sq_mean = torch.zeros(input_dim, dtype=torch.float32)
    with torch.no_grad():
        for batch in loader:
            inputs, _ = batch
            inputs = inputs.view(inputs.size(0), -1).to("cpu")
            batch_size = inputs.size(0)
            total += batch_size
            mean += inputs.sum(dim=0)
            sq_mean += (inputs * inputs).sum(dim=0)
    if total == 0:
        std = torch.ones(input_dim, dtype=torch.float32)
        mean = torch.zeros(input_dim, dtype=torch.float32)
    else:
        mean /= total
        sq_mean /= total
        var = sq_mean - mean * mean
        var.clamp_(min=1e-6)
        std = torch.sqrt(var)
    mean = mean.to(device)
    std = std.to(device)
    return mean, std


def count_params_formula(input_dim: int, num_classes: int, width: int, num_blocks: int) -> int:
    # Linear layers
    p_in = input_dim * width + width
    p_blocks = num_blocks * 2 * (width * width + width)
    p_out = width * num_classes + num_classes
    # BatchNorm1d layers (affine: weight + bias)
    num_bns = 1 + 2 * num_blocks
    p_bn = num_bns * 2 * width
    return p_in + p_blocks + p_out + p_bn


def find_best_architecture(input_dim: int, num_classes: int, param_limit: int):
    best_width = 64
    best_blocks = 1
    best_params = 0
    max_blocks = 6
    for blocks in range(1, max_blocks + 1):
        low, high = 16, 2048
        local_best_w = None
        local_best_p = -1
        while low <= high:
            mid = (low + high) // 2
            p = count_params_formula(input_dim, num_classes, mid, blocks)
            if p <= param_limit:
                local_best_w = mid
                local_best_p = p
                low = mid + 1
            else:
                high = mid - 1
        if local_best_w is not None and local_best_p > best_params:
            best_params = local_best_p
            best_width = local_best_w
            best_blocks = blocks
    return best_width, best_blocks


def evaluate(model: nn.Module, loader, device: torch.device, criterion=None):
    model.eval()
    correct = 0
    total = 0
    loss_sum = 0.0
    with torch.no_grad():
        for inputs, targets in loader:
            inputs = inputs.to(device)
            targets = targets.to(device)
            outputs = model(inputs)
            if criterion is not None:
                loss = criterion(outputs, targets)
                loss_sum += loss.item() * targets.size(0)
            preds = outputs.argmax(dim=1)
            correct += (preds == targets).sum().item()
            total += targets.size(0)
    acc = correct / total if total > 0 else 0.0
    loss_avg = loss_sum / total if criterion is not None and total > 0 else 0.0
    return acc, loss_avg


class Solution:
    def solve(self, train_loader, val_loader, metadata: dict = None) -> torch.nn.Module:
        if metadata is None:
            raise ValueError("Metadata dictionary is required.")

        input_dim = int(metadata.get("input_dim", 384))
        num_classes = int(metadata.get("num_classes", 128))
        param_limit = int(metadata.get("param_limit", 1_000_000))
        device_str = metadata.get("device", "cpu")
        if "cuda" in device_str and not torch.cuda.is_available():
            device_str = "cpu"
        device = torch.device(device_str)

        torch.manual_seed(42)

        mean, std = compute_mean_std(train_loader, input_dim, device)

        width, num_blocks = find_best_architecture(input_dim, num_classes, param_limit)

        model = MLPResNet(
            input_dim=input_dim,
            num_classes=num_classes,
            width=width,
            num_blocks=num_blocks,
            dropout=0.1,
            mean=mean,
            std=std,
        )
        model.to(device)

        actual_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
        if actual_params > param_limit:
            # Fallback to a smaller simple MLP if something went wrong
            hidden = 512
            if (input_dim + 1) * hidden + (hidden + 1) * num_classes > param_limit:
                hidden = 256
            model = nn.Sequential(
                InputNormalizer(mean, std),
                nn.Linear(input_dim, hidden),
                nn.ReLU(inplace=True),
                nn.Linear(hidden, num_classes),
            )
            model.to(device)

        lr = 3e-3
        weight_decay = 1e-4
        max_epochs = 120
        patience = 20

        criterion = nn.CrossEntropyLoss(label_smoothing=0.1)
        optimizer = optim.AdamW(model.parameters(), lr=lr, weight_decay=weight_decay)
        scheduler = optim.lr_scheduler.CosineAnnealingLR(
            optimizer, T_max=max_epochs, eta_min=3e-5
        )

        best_state = copy.deepcopy(model.state_dict())
        best_val_acc = 0.0
        epochs_without_improve = 0

        for epoch in range(max_epochs):
            model.train()
            for inputs, targets in train_loader:
                inputs = inputs.to(device)
                targets = targets.to(device)

                optimizer.zero_grad(set_to_none=True)
                outputs = model(inputs)
                loss = criterion(outputs, targets)
                loss.backward()
                optimizer.step()

            scheduler.step()

            val_acc, _ = evaluate(model, val_loader, device, criterion=None)

            if val_acc > best_val_acc + 1e-4:
                best_val_acc = val_acc
                best_state = copy.deepcopy(model.state_dict())
                epochs_without_improve = 0
            else:
                epochs_without_improve += 1
                if epochs_without_improve >= patience:
                    break

        model.load_state_dict(best_state)
        model.eval()
        return model
