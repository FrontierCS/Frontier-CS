import math
import random
import copy
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim


class ResidualBottleneckBlock(nn.Module):
    def __init__(self, width, bottleneck, dropout=0.1, use_bn=True):
        super().__init__()
        self.use_bn = use_bn
        self.bn1 = nn.BatchNorm1d(width) if use_bn else nn.Identity()
        self.bn2 = nn.BatchNorm1d(bottleneck) if use_bn else nn.Identity()
        self.fc1 = nn.Linear(width, bottleneck)
        self.act = nn.GELU()
        self.fc2 = nn.Linear(bottleneck, width)
        self.drop = nn.Dropout(dropout) if dropout and dropout > 0 else nn.Identity()

    def forward(self, x):
        residual = x
        y = self.bn1(x)
        y = self.fc1(y)
        y = self.act(y)
        y = self.bn2(y)
        y = self.fc2(y)
        y = self.drop(y)
        return residual + y


class MLPClassifier(nn.Module):
    def __init__(self, input_dim, num_classes, width=640, bottleneck=256, num_blocks=2, dropout=0.1, use_bn=True, input_bn=True):
        super().__init__()
        self.input_bn = nn.BatchNorm1d(input_dim) if input_bn else nn.Identity()
        self.stem = nn.Linear(input_dim, width)
        blocks = []
        for _ in range(num_blocks):
            blocks.append(ResidualBottleneckBlock(width, bottleneck, dropout=dropout, use_bn=use_bn))
        self.blocks = nn.Sequential(*blocks)
        self.out_bn = nn.BatchNorm1d(width) if use_bn else nn.Identity()
        self.out_act = nn.GELU()
        self.out_drop = nn.Dropout(dropout) if dropout and dropout > 0 else nn.Identity()
        self.head = nn.Linear(width, num_classes)
        self.reset_parameters()

    def reset_parameters(self):
        for m in self.modules():
            if isinstance(m, nn.Linear):
                nn.init.xavier_uniform_(m.weight)
                if m.bias is not None:
                    nn.init.zeros_(m.bias)
            elif isinstance(m, nn.BatchNorm1d):
                nn.init.ones_(m.weight)
                nn.init.zeros_(m.bias)

    def forward(self, x):
        x = x.float()
        x = self.input_bn(x)
        x = self.stem(x)
        x = self.blocks(x)
        x = self.out_bn(x)
        x = self.out_act(x)
        x = self.out_drop(x)
        x = self.head(x)
        return x


def count_trainable_parameters(model: nn.Module) -> int:
    return sum(p.numel() for p in model.parameters() if p.requires_grad)


def cosine_warmup_lambda(epoch, total_epochs, warmup_epochs):
    if epoch < warmup_epochs:
        return float(epoch + 1) / float(max(1, warmup_epochs))
    progress = (epoch - warmup_epochs) / float(max(1, total_epochs - warmup_epochs))
    return 0.5 * (1.0 + math.cos(math.pi * progress))


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
    acc = correct / total if total > 0 else 0.0
    return acc


class Solution:
    def _select_architecture(self, input_dim, num_classes, param_limit):
        # Search for the largest width under parameter limit using 2 residual bottleneck blocks
        candidate_widths = [768, 736, 704, 672, 640, 608, 576, 544, 512, 480, 448, 416, 384]
        ratios = [0.5, 0.4, 0.33, 0.25]
        for w in candidate_widths:
            for r in ratios:
                b = max(64, int(round((w * r) / 32.0)) * 32)
                model = MLPClassifier(input_dim, num_classes, width=w, bottleneck=b, num_blocks=2, dropout=0.1, use_bn=True, input_bn=True)
                params = count_trainable_parameters(model)
                if params <= param_limit:
                    return w, b, 2
        # Fallback conservative architecture
        w = 512
        b = 192
        model = MLPClassifier(input_dim, num_classes, width=w, bottleneck=b, num_blocks=2, dropout=0.1, use_bn=True, input_bn=True)
        if count_trainable_parameters(model) <= param_limit:
            return w, b, 2
        # Last resort - reduce blocks
        for w in [512, 480, 448, 416, 384]:
            b = max(64, int(round((w * 0.33) / 32.0)) * 32)
            model = MLPClassifier(input_dim, num_classes, width=w, bottleneck=b, num_blocks=1, dropout=0.1, use_bn=True, input_bn=True)
            if count_trainable_parameters(model) <= param_limit:
                return w, b, 1
        # Minimal model
        return 384, 128, 1

    def solve(self, train_loader, val_loader, metadata: dict = None) -> torch.nn.Module:
        if metadata is None:
            metadata = {}
        input_dim = int(metadata.get("input_dim", 384))
        num_classes = int(metadata.get("num_classes", 128))
        param_limit = int(metadata.get("param_limit", 1_000_000))
        device = torch.device(metadata.get("device", "cpu"))

        seed = 42
        random.seed(seed)
        np.random.seed(seed)
        torch.manual_seed(seed)

        width, bottleneck, num_blocks = self._select_architecture(input_dim, num_classes, param_limit)
        model = MLPClassifier(input_dim, num_classes, width=width, bottleneck=bottleneck, num_blocks=num_blocks, dropout=0.1, use_bn=True, input_bn=True).to(device)

        # Ensure parameter constraint
        if count_trainable_parameters(model) > param_limit:
            # As a hard safety fallback, use a simpler baseline if selection somehow failed
            model = nn.Sequential(
                nn.Linear(input_dim, 512),
                nn.GELU(),
                nn.BatchNorm1d(512),
                nn.Linear(512, num_classes),
            ).to(device)

        epochs = 160
        warmup_epochs = max(5, epochs // 16)
        lr = 3e-3
        weight_decay = 2e-2
        optimizer = optim.AdamW(model.parameters(), lr=lr, weight_decay=weight_decay)
        scheduler = optim.lr_scheduler.LambdaLR(
            optimizer, lr_lambda=lambda e: cosine_warmup_lambda(e, epochs, warmup_epochs)
        )

        criterion = nn.CrossEntropyLoss(label_smoothing=0.05)

        best_state = copy.deepcopy(model.state_dict())
        best_val_acc = 0.0

        mixup_alpha = 0.2
        mixup_prob = 0.4
        mixup_until = int(epochs * 0.6)

        for epoch in range(epochs):
            model.train()
            for inputs, targets in train_loader:
                inputs = inputs.to(device)
                targets = targets.to(device)

                apply_mixup = (epoch < mixup_until) and (random.random() < mixup_prob) and (inputs.size(0) > 1)
                if apply_mixup:
                    lam = np.random.beta(mixup_alpha, mixup_alpha)
                    index = torch.randperm(inputs.size(0), device=device)
                    mixed_inputs = lam * inputs + (1 - lam) * inputs[index, :]
                    y_a, y_b = targets, targets[index]
                    outputs = model(mixed_inputs)
                    loss = lam * criterion(outputs, y_a) + (1 - lam) * criterion(outputs, y_b)
                else:
                    outputs = model(inputs)
                    loss = criterion(outputs, targets)

                optimizer.zero_grad()
                loss.backward()
                nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
                optimizer.step()

            scheduler.step()

            # Validation
            val_acc = evaluate(model, val_loader, device)
            if val_acc > best_val_acc:
                best_val_acc = val_acc
                best_state = copy.deepcopy(model.state_dict())

        model.load_state_dict(best_state)
        model.to(device)
        model.eval()
        return model
