import math
import random
import copy
import torch
import torch.nn as nn
import torch.optim as optim


def count_trainable_params(model: nn.Module) -> int:
    return sum(p.numel() for p in model.parameters() if p.requires_grad)


class MLPNet(nn.Module):
    def __init__(self, input_dim, hidden_dims, num_classes, dropout=0.15, use_bn=True, use_input_bn=False):
        super().__init__()
        self.use_bn = use_bn
        self.use_input_bn = use_input_bn
        layers = []
        self.input_bn = nn.BatchNorm1d(input_dim) if use_input_bn else nn.Identity()

        dims = [input_dim] + hidden_dims
        self.fcs = nn.ModuleList()
        self.bns = nn.ModuleList()
        for i in range(len(dims) - 1):
            fc = nn.Linear(dims[i], dims[i + 1], bias=True)
            self.fcs.append(fc)
            if use_bn:
                self.bns.append(nn.BatchNorm1d(dims[i + 1]))
            else:
                self.bns.append(nn.Identity())

        self.fc_out = nn.Linear(dims[-1], num_classes, bias=True)
        self.act = nn.GELU()
        self.drop = nn.Dropout(dropout)

        for layer in self.fcs:
            nn.init.kaiming_normal_(layer.weight, nonlinearity='relu')
            nn.init.zeros_(layer.bias)
        nn.init.zeros_(self.fc_out.bias)

    def forward(self, x):
        x = self.input_bn(x)
        for fc, bn in zip(self.fcs, self.bns):
            x = fc(x)
            x = bn(x)
            x = self.act(x)
            x = self.drop(x)
        x = self.fc_out(x)
        return x


def estimate_params(input_dim, hidden_dims, num_classes, use_bn=True, use_input_bn=False):
    dims = [input_dim] + hidden_dims + [num_classes]
    total = 0
    for i in range(len(dims) - 1):
        total += dims[i] * dims[i + 1] + dims[i + 1]  # weights + bias
    if use_bn:
        # BN for all hidden dims
        for d in hidden_dims:
            total += 2 * d  # gamma + beta
    if use_input_bn:
        total += 2 * input_dim
    return total


def choose_architecture(input_dim, num_classes, param_limit):
    # Start with 3 hidden layers scaled from input dimension
    # Initial widths target
    w1 = max(128, min(256, int(round(input_dim * 0.75))))  # for 384 -> 288, then capped at 256
    w2 = max(96, int(round(w1 * 0.75)))
    w3 = max(64, int(round(w2 * 0.75)))

    use_bn = True
    use_input_bn = True

    # Try to fit with BN and input BN
    for _ in range(128):
        hidden_dims = [w1, w2, w3]
        params = estimate_params(input_dim, hidden_dims, num_classes, use_bn=True, use_input_bn=True)
        if params <= param_limit:
            return hidden_dims, True, True
        # Try without input BN
        params = estimate_params(input_dim, hidden_dims, num_classes, use_bn=True, use_input_bn=False)
        if params <= param_limit:
            return hidden_dims, True, False
        # Try without BN
        params = estimate_params(input_dim, hidden_dims, num_classes, use_bn=False, use_input_bn=False)
        if params <= param_limit:
            return hidden_dims, False, False
        # Reduce widths
        w1 = max(96, w1 - 8)
        w2 = max(72, int(round(w1 * 0.75)))
        w3 = max(48, int(round(w2 * 0.75)))

    # Fallback to 2 hidden layers if still not fitting
    w1 = max(128, min(256, int(round(input_dim * 0.67))))
    w2 = max(96, int(round(w1 * 0.75)))
    for _ in range(128):
        hidden_dims = [w1, w2]
        params = estimate_params(input_dim, hidden_dims, num_classes, use_bn=True, use_input_bn=True)
        if params <= param_limit:
            return hidden_dims, True, True
        params = estimate_params(input_dim, hidden_dims, num_classes, use_bn=True, use_input_bn=False)
        if params <= param_limit:
            return hidden_dims, True, False
        params = estimate_params(input_dim, hidden_dims, num_classes, use_bn=False, use_input_bn=False)
        if params <= param_limit:
            return hidden_dims, False, False
        w1 = max(96, w1 - 8)
        w2 = max(72, int(round(w1 * 0.75)))

    # Last resort: single hidden layer
    w1 = max(128, min(320, int(round(input_dim * 0.67))))
    for _ in range(128):
        hidden_dims = [w1]
        params = estimate_params(input_dim, hidden_dims, num_classes, use_bn=True, use_input_bn=False)
        if params <= param_limit:
            return hidden_dims, True, False
        params = estimate_params(input_dim, hidden_dims, num_classes, use_bn=False, use_input_bn=False)
        if params <= param_limit:
            return hidden_dims, False, False
        w1 = max(64, w1 - 8)

    # Default fallback
    return [256], False, False


def mixup_batch(x, y, alpha=0.2):
    if alpha <= 0:
        lam = 1.0
        index = torch.arange(x.size(0))
    else:
        lam = torch._standard_gamma(torch.tensor([alpha]))[0].item()
        lam2 = torch._standard_gamma(torch.tensor([alpha]))[0].item()
        lam = lam / (lam + lam2)
        index = torch.randperm(x.size(0))
    mixed_x = lam * x + (1 - lam) * x[index, :]
    y_a, y_b = y, y[index]
    return mixed_x, y_a, y_b, lam


def evaluate(model, data_loader, device):
    model.eval()
    correct = 0
    total = 0
    with torch.no_grad():
        for inputs, targets in data_loader:
            inputs = inputs.to(device)
            targets = targets.to(device)
            outputs = model(inputs)
            preds = outputs.argmax(dim=1)
            correct += (preds == targets).sum().item()
            total += targets.numel()
    return correct / max(1, total)


class Solution:
    def solve(self, train_loader, val_loader, metadata: dict = None) -> torch.nn.Module:
        if metadata is None:
            metadata = {}
        device = torch.device(metadata.get("device", "cpu"))
        input_dim = int(metadata.get("input_dim", 384))
        num_classes = int(metadata.get("num_classes", 128))
        param_limit = int(metadata.get("param_limit", 200000))
        baseline_accuracy = float(metadata.get("baseline_accuracy", 0.65))

        # Construct architecture within parameter budget
        hidden_dims, use_bn, use_input_bn = choose_architecture(input_dim, num_classes, param_limit)
        model = MLPNet(input_dim, hidden_dims, num_classes, dropout=0.15, use_bn=use_bn, use_input_bn=use_input_bn).to(device)

        # Verify parameter constraint
        total_params = count_trainable_params(model)
        if total_params > param_limit:
            # As a strict fallback, revert to a small 2-layer network always under budget
            model = MLPNet(input_dim, [256, 160], num_classes, dropout=0.15, use_bn=False, use_input_bn=False).to(device)

        # Optimizer and scheduler
        base_lr = 0.003
        weight_decay = 1e-4
        optimizer = optim.AdamW(model.parameters(), lr=base_lr, weight_decay=weight_decay)
        criterion = nn.CrossEntropyLoss(label_smoothing=0.05)

        epochs = 150
        steps_per_epoch = max(1, len(train_loader))
        total_steps = epochs * steps_per_epoch
        scheduler = optim.lr_scheduler.OneCycleLR(
            optimizer,
            max_lr=base_lr,
            total_steps=total_steps,
            pct_start=0.15,
            anneal_strategy='cos',
            cycle_momentum=False
        )

        best_val_acc = 0.0
        best_state = copy.deepcopy(model.state_dict())
        patience = 30
        no_improve_epochs = 0

        # Train loop
        for epoch in range(epochs):
            model.train()
            for inputs, targets in train_loader:
                inputs = inputs.to(device)
                targets = targets.to(device)

                use_mix = random.random() < 0.7
                if use_mix:
                    mixed_x, y_a, y_b, lam = mixup_batch(inputs, targets, alpha=0.3)
                    optimizer.zero_grad(set_to_none=True)
                    outputs = model(mixed_x)
                    loss = lam * criterion(outputs, y_a) + (1 - lam) * criterion(outputs, y_b)
                else:
                    optimizer.zero_grad(set_to_none=True)
                    outputs = model(inputs)
                    loss = criterion(outputs, targets)

                loss.backward()
                nn.utils.clip_grad_norm_(model.parameters(), max_norm=2.0)
                optimizer.step()
                scheduler.step()

            # Validation
            val_acc = evaluate(model, val_loader, device)
            if val_acc > best_val_acc + 1e-6:
                best_val_acc = val_acc
                best_state = copy.deepcopy(model.state_dict())
                no_improve_epochs = 0
            else:
                no_improve_epochs += 1

            if no_improve_epochs >= patience:
                break

        model.load_state_dict(best_state)
        model.eval()
        return model