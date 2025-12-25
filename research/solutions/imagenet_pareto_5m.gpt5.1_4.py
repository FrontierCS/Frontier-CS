import torch
import torch.nn as nn
import torch.nn.functional as F
import copy


class ResMLPBlock(nn.Module):
    def __init__(self, dim: int, dropout: float = 0.1):
        super().__init__()
        self.norm = nn.LayerNorm(dim)
        self.fc1 = nn.Linear(dim, dim)
        self.fc2 = nn.Linear(dim, dim)
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


class ResMLPNet(nn.Module):
    def __init__(self, input_dim: int, num_classes: int, width: int, num_blocks: int, dropout: float = 0.1):
        super().__init__()
        self.input_bn = nn.BatchNorm1d(input_dim)
        self.input = nn.Linear(input_dim, width)
        self.blocks = nn.ModuleList([ResMLPBlock(width, dropout=dropout) for _ in range(num_blocks)])
        self.norm = nn.LayerNorm(width)
        self.output = nn.Linear(width, num_classes)

    def forward(self, x):
        x = self.input_bn(x)
        x = self.input(x)
        for block in self.blocks:
            x = block(x)
        x = self.norm(x)
        x = self.output(x)
        return x


def count_parameters(model: nn.Module) -> int:
    return sum(p.numel() for p in model.parameters() if p.requires_grad)


def build_best_model(input_dim: int, num_classes: int, param_limit: int) -> nn.Module:
    # Search over a grid of widths and block counts to maximize parameter usage under the limit
    candidate_widths = [1024, 896, 768, 640, 576, 512, 448, 384, 320]
    candidate_blocks = list(range(12, 0, -1))

    best_model = None
    best_params = -1

    for width in candidate_widths:
        for blocks in candidate_blocks:
            model = ResMLPNet(input_dim, num_classes, width, blocks, dropout=0.1)
            params = count_parameters(model)
            if params <= param_limit and params > best_params:
                best_params = params
                best_model = model

    if best_model is None:
        # Fallback tiny model (should not happen for this task)
        best_model = nn.Sequential(
            nn.Linear(input_dim, num_classes)
        )

    return best_model


def train_one_epoch(model, loader, optimizer, criterion, device, grad_clip=None):
    model.train()
    total_loss = 0.0
    total_samples = 0

    for inputs, targets in loader:
        inputs = inputs.to(device)
        targets = targets.to(device)

        optimizer.zero_grad()
        outputs = model(inputs)
        loss = criterion(outputs, targets)
        loss.backward()

        if grad_clip is not None:
            nn.utils.clip_grad_norm_(model.parameters(), grad_clip)

        optimizer.step()

        batch_size = targets.size(0)
        total_loss += loss.item() * batch_size
        total_samples += batch_size

    if total_samples == 0:
        return 0.0
    return total_loss / total_samples


def evaluate(model, loader, criterion, device):
    model.eval()
    total_loss = 0.0
    total_correct = 0
    total_samples = 0

    with torch.no_grad():
        for inputs, targets in loader:
            inputs = inputs.to(device)
            targets = targets.to(device)

            outputs = model(inputs)
            loss = criterion(outputs, targets)

            batch_size = targets.size(0)
            total_loss += loss.item() * batch_size
            preds = outputs.argmax(dim=1)
            total_correct += (preds == targets).sum().item()
            total_samples += batch_size

    if total_samples == 0:
        return 0.0, 0.0
    avg_loss = total_loss / total_samples
    accuracy = total_correct / total_samples
    return avg_loss, accuracy


class Solution:
    def solve(self, train_loader, val_loader, metadata: dict = None) -> torch.nn.Module:
        if metadata is None:
            # Sensible defaults if metadata is missing
            input_dim = 384
            num_classes = 128
            param_limit = 5_000_000
            device_str = "cpu"
        else:
            input_dim = int(metadata.get("input_dim", 384))
            num_classes = int(metadata.get("num_classes", 128))
            param_limit = int(metadata.get("param_limit", 5_000_000))
            device_str = metadata.get("device", "cpu")

        device = torch.device(device_str)

        # Build the best model under the parameter limit
        model = build_best_model(input_dim, num_classes, param_limit)
        # Double-check parameter constraint; if violated, shrink by reducing blocks
        params = count_parameters(model)
        if params > param_limit and isinstance(model, ResMLPNet):
            # Reduce number of blocks until under limit
            width = model.input.out_features
            blocks = len(model.blocks)
            while blocks > 0:
                candidate = ResMLPNet(input_dim, num_classes, width, blocks, dropout=0.1)
                if count_parameters(candidate) <= param_limit:
                    model = candidate
                    break
                blocks -= 1
        model.to(device)

        # Training setup
        base_lr = 1e-3
        weight_decay = 1e-4
        max_epochs = 200
        min_epochs = 50
        patience = 30
        grad_clip = 1.0

        criterion = nn.CrossEntropyLoss(label_smoothing=0.1)
        optimizer = torch.optim.AdamW(model.parameters(), lr=base_lr, weight_decay=weight_decay)

        best_state = None
        best_val_acc = -1.0
        epochs_no_improve = 0

        for epoch in range(max_epochs):
            # Simple step LR schedule
            if epoch == 80 or epoch == 140:
                for g in optimizer.param_groups:
                    g["lr"] *= 0.2

            train_one_epoch(model, train_loader, optimizer, criterion, device, grad_clip=grad_clip)
            _, val_acc = evaluate(model, val_loader, criterion, device)

            if val_acc > best_val_acc + 1e-4:
                best_val_acc = val_acc
                best_state = copy.deepcopy(model.state_dict())
                epochs_no_improve = 0
            else:
                epochs_no_improve += 1

            if (epoch + 1) >= min_epochs and epochs_no_improve >= patience:
                break

        if best_state is not None:
            model.load_state_dict(best_state)

        model.eval()
        return model
