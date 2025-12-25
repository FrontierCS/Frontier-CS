import torch
import torch.nn as nn
import torch.nn.functional as F
import copy


class MLP(nn.Module):
    def __init__(self, input_dim: int, num_classes: int, hidden_sizes, dropout: float = 0.1, use_bn: bool = True):
        super().__init__()
        layers = []
        prev_dim = input_dim
        for h in hidden_sizes:
            layers.append(nn.Linear(prev_dim, h))
            if use_bn:
                layers.append(nn.BatchNorm1d(h))
            layers.append(nn.ReLU(inplace=True))
            if dropout > 0.0:
                layers.append(nn.Dropout(dropout))
            prev_dim = h
        layers.append(nn.Linear(prev_dim, num_classes))
        self.net = nn.Sequential(*layers)

    def forward(self, x):
        return self.net(x)


def count_parameters(model: nn.Module) -> int:
    return sum(p.numel() for p in model.parameters() if p.requires_grad)


def build_model(input_dim: int, num_classes: int, param_limit: int) -> nn.Module:
    # Start with a reasonably large architecture under the 1M parameter budget
    candidate_hidden = [768, 512, 256, 128]
    dropout = 0.1
    use_bn = True

    # Try full candidate first
    hidden = candidate_hidden[:]
    model = MLP(input_dim, num_classes, hidden, dropout=dropout, use_bn=use_bn)
    if count_parameters(model) <= param_limit:
        return model

    # Gradually reduce number of layers
    for num_layers in range(len(candidate_hidden) - 1, 0, -1):
        hidden = candidate_hidden[:num_layers]
        model = MLP(input_dim, num_classes, hidden, dropout=dropout, use_bn=use_bn)
        if count_parameters(model) <= param_limit:
            return model

    # Fallback to simple baseline if still above limit
    fallback_hidden = [min(512, max(128, input_dim * 2))]
    model = MLP(input_dim, num_classes, fallback_hidden, dropout=0.0, use_bn=True)
    # Ensure final fallback respects the parameter limit
    if count_parameters(model) > param_limit:
        # Last resort: single small layer
        fallback_hidden = [min(256, max(64, input_dim))]
        model = MLP(input_dim, num_classes, fallback_hidden, dropout=0.0, use_bn=False)
    return model


def evaluate_accuracy(model: nn.Module, data_loader, device: torch.device) -> float:
    model.eval()
    correct = 0
    total = 0
    with torch.no_grad():
        for inputs, targets in data_loader:
            inputs = inputs.to(device)
            targets = targets.long().to(device)
            outputs = model(inputs)
            preds = outputs.argmax(dim=1)
            correct += (preds == targets).sum().item()
            total += targets.numel()
    if total == 0:
        return 0.0
    return correct / total


class Solution:
    def solve(self, train_loader, val_loader, metadata: dict = None) -> torch.nn.Module:
        if metadata is None:
            metadata = {}

        # Determine basic metadata
        input_dim = metadata.get("input_dim", None)
        num_classes = metadata.get("num_classes", None)
        param_limit = metadata.get("param_limit", 1_000_000)
        device_str = metadata.get("device", "cpu")

        if input_dim is None or num_classes is None:
            for batch in train_loader:
                x_batch, y_batch = batch
                x_flat = x_batch.view(x_batch.size(0), -1)
                input_dim = x_flat.size(1)
                if num_classes is None:
                    num_classes = int(y_batch.max().item()) + 1
                break

        if device_str != "cpu" and not torch.cuda.is_available():
            device_str = "cpu"
        device = torch.device(device_str)

        torch.manual_seed(42)

        model = build_model(input_dim, num_classes, param_limit)
        model.to(device)

        # Ensure parameter budget is respected
        if count_parameters(model) > param_limit:
            # As a hard safeguard, use minimal 2-layer MLP well under limit
            hidden_dim = min(512, max(128, input_dim * 2))
            model = nn.Sequential(
                nn.Linear(input_dim, hidden_dim),
                nn.ReLU(inplace=True),
                nn.Linear(hidden_dim, num_classes),
            ).to(device)

        # Training setup
        try:
            criterion = nn.CrossEntropyLoss(label_smoothing=0.05)
        except TypeError:
            criterion = nn.CrossEntropyLoss()

        optimizer = torch.optim.AdamW(model.parameters(), lr=1e-3, weight_decay=1e-2)
        max_epochs = 200
        scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(
            optimizer, T_max=max_epochs, eta_min=1e-5
        )

        best_state = None
        best_val_acc = -1.0
        patience = 30
        epochs_no_improve = 0
        has_val = val_loader is not None

        for epoch in range(max_epochs):
            model.train()
            for inputs, targets in train_loader:
                inputs = inputs.to(device)
                targets = targets.long().to(device)

                optimizer.zero_grad()
                outputs = model(inputs)
                loss = criterion(outputs, targets)
                loss.backward()
                nn.utils.clip_grad_norm_(model.parameters(), max_norm=5.0)
                optimizer.step()

            scheduler.step()

            if has_val:
                val_acc = evaluate_accuracy(model, val_loader, device)
                if val_acc > best_val_acc + 1e-4:
                    best_val_acc = val_acc
                    best_state = copy.deepcopy(model.state_dict())
                    epochs_no_improve = 0
                else:
                    epochs_no_improve += 1
                    if epochs_no_improve >= patience:
                        break

        if best_state is not None:
            model.load_state_dict(best_state)

        model.to("cpu")
        return model
