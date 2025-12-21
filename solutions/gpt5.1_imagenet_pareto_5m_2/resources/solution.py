import torch
import torch.nn as nn
import torch.optim as optim
from copy import deepcopy


class FFNBlock(nn.Module):
    def __init__(self, dim: int, hidden_dim: int, dropout: float = 0.1):
        super().__init__()
        self.norm = nn.LayerNorm(dim)
        self.fc1 = nn.Linear(dim, hidden_dim)
        self.act = nn.GELU()
        self.fc2 = nn.Linear(hidden_dim, dim)
        self.dropout = nn.Dropout(dropout)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        residual = x
        out = self.norm(x)
        out = self.fc1(out)
        out = self.act(out)
        out = self.dropout(out)
        out = self.fc2(out)
        out = self.dropout(out)
        return residual + out


class MLPClassifier(nn.Module):
    def __init__(
        self,
        input_dim: int,
        num_classes: int,
        width: int = 512,
        expansion: int = 4,
        num_blocks: int = 2,
        dropout: float = 0.1,
    ):
        super().__init__()
        self.input_norm = nn.LayerNorm(input_dim)
        self.fc_in = nn.Linear(input_dim, width)
        hidden_dim = width * expansion
        self.blocks = nn.ModuleList(
            [FFNBlock(width, hidden_dim, dropout=dropout) for _ in range(num_blocks)]
        )
        self.final_norm = nn.LayerNorm(width)
        self.fc_out = nn.Linear(width, num_classes)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self.input_norm(x)
        x = self.fc_in(x)
        for block in self.blocks:
            x = block(x)
        x = self.final_norm(x)
        x = self.fc_out(x)
        return x


def count_trainable_params(model: nn.Module) -> int:
    return sum(p.numel() for p in model.parameters() if p.requires_grad)


def train_one_epoch(
    model: nn.Module,
    loader,
    optimizer: optim.Optimizer,
    criterion: nn.Module,
    device: torch.device,
    grad_clip: float = None,
):
    model.train()
    for inputs, targets in loader:
        inputs = inputs.to(device)
        targets = targets.to(device)

        optimizer.zero_grad(set_to_none=True)
        outputs = model(inputs)
        loss = criterion(outputs, targets)
        loss.backward()
        if grad_clip is not None:
            nn.utils.clip_grad_norm_(model.parameters(), grad_clip)
        optimizer.step()


def evaluate_accuracy(model: nn.Module, loader, device: torch.device) -> float:
    model.eval()
    correct = 0
    total = 0
    with torch.no_grad():
        for inputs, targets in loader:
            inputs = inputs.to(device)
            targets = targets.to(device)
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
        input_dim = int(metadata.get("input_dim", 384))
        num_classes = int(metadata.get("num_classes", 128))
        param_limit = int(metadata.get("param_limit", 5_000_000))
        device_str = metadata.get("device", "cpu")
        device = torch.device(device_str if torch.cuda.is_available() else "cpu")

        # Fixed architecture chosen to stay well under 5M params
        width = 512
        expansion = 4
        num_blocks = 2
        dropout = 0.1

        model = MLPClassifier(
            input_dim=input_dim,
            num_classes=num_classes,
            width=width,
            expansion=expansion,
            num_blocks=num_blocks,
            dropout=dropout,
        )

        # Ensure parameter constraint
        total_params = count_trainable_params(model)
        if total_params > param_limit:
            # Fallback to a smaller network if constraint is somehow violated
            width = 384
            expansion = 4
            num_blocks = 2
            model = MLPClassifier(
                input_dim=input_dim,
                num_classes=num_classes,
                width=width,
                expansion=expansion,
                num_blocks=num_blocks,
                dropout=dropout,
            )
            total_params = count_trainable_params(model)
            if total_params > param_limit:
                width = 256
                expansion = 4
                num_blocks = 2
                model = MLPClassifier(
                    input_dim=input_dim,
                    num_classes=num_classes,
                    width=width,
                    expansion=expansion,
                    num_blocks=num_blocks,
                    dropout=dropout,
                )

        model.to(device)

        # Training setup
        train_samples = int(metadata.get("train_samples", 2048))
        max_epochs = 320 if train_samples <= 4096 else 160

        base_lr = 3e-3
        weight_decay = 1e-4
        optimizer = optim.AdamW(model.parameters(), lr=base_lr, weight_decay=weight_decay)

        try:
            criterion = nn.CrossEntropyLoss(label_smoothing=0.05)
        except TypeError:
            criterion = nn.CrossEntropyLoss()

        scheduler = optim.lr_scheduler.ReduceLROnPlateau(
            optimizer,
            mode="max",
            factor=0.5,
            patience=6,
            verbose=False,
            min_lr=1e-5,
        )

        best_model_state = deepcopy(model.state_dict())
        best_val_acc = -1.0
        patience = 30
        epochs_no_improve = 0
        min_delta = 1e-4

        for epoch in range(max_epochs):
            train_one_epoch(
                model,
                train_loader,
                optimizer,
                criterion,
                device=device,
                grad_clip=5.0,
            )

            if val_loader is not None:
                val_acc = evaluate_accuracy(model, val_loader, device)
                scheduler.step(val_acc)

                if val_acc > best_val_acc + min_delta:
                    best_val_acc = val_acc
                    best_model_state = deepcopy(model.state_dict())
                    epochs_no_improve = 0
                else:
                    epochs_no_improve += 1

                if epochs_no_improve >= patience:
                    break
            else:
                # If no validation loader is provided, just run fixed epochs
                continue

        model.load_state_dict(best_model_state)
        model.to(device)

        return model
