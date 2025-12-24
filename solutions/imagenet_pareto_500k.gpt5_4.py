import math
import copy
import torch
import torch.nn as nn
import torch.optim as optim


def count_parameters(model):
    return sum(p.numel() for p in model.parameters() if p.requires_grad)


class PreActResBlock(nn.Module):
    def __init__(self, dim, dropout=0.1):
        super().__init__()
        self.bn1 = nn.BatchNorm1d(dim)
        self.act1 = nn.GELU()
        self.fc1 = nn.Linear(dim, dim, bias=False)
        self.bn2 = nn.BatchNorm1d(dim)
        self.act2 = nn.GELU()
        self.drop = nn.Dropout(dropout)
        self.fc2 = nn.Linear(dim, dim, bias=False)
        nn.init.zeros_(self.fc2.weight)

    def forward(self, x):
        out = self.act1(self.bn1(x))
        out = self.fc1(out)
        out = self.act2(self.bn2(out))
        out = self.drop(out)
        out = self.fc2(out)
        return x + out


class MLPResNet(nn.Module):
    def __init__(self, input_dim, num_classes, width1=512, width2=256, dropout=0.1, bn_pre_out=True):
        super().__init__()
        self.fc_in = nn.Linear(input_dim, width1, bias=False)
        self.bn_in = nn.BatchNorm1d(width1)
        self.act_in = nn.GELU()

        self.fc_mid = nn.Linear(width1, width2, bias=False)
        self.bn_mid = nn.BatchNorm1d(width2)
        self.act_mid = nn.GELU()

        self.block = PreActResBlock(width2, dropout=dropout)
        self.bn_pre_out = nn.BatchNorm1d(width2) if bn_pre_out else None
        self.act_pre_out = nn.GELU() if bn_pre_out else None

        self.drop_out = nn.Dropout(dropout)
        self.fc_out = nn.Linear(width2, num_classes, bias=True)

        self._init_weights()

    def _init_weights(self):
        nn.init.kaiming_normal_(self.fc_in.weight, nonlinearity='linear')
        nn.init.kaiming_normal_(self.fc_mid.weight, nonlinearity='linear')
        nn.init.kaiming_normal_(self.fc_out.weight, nonlinearity='linear')
        nn.init.zeros_(self.fc_out.bias)

    def forward(self, x):
        x = self.fc_in(x)
        x = self.act_in(self.bn_in(x))

        x = self.fc_mid(x)
        x = self.act_mid(self.bn_mid(x))

        x = self.block(x)

        if self.bn_pre_out is not None:
            x = self.act_pre_out(self.bn_pre_out(x))
        x = self.drop_out(x)
        x = self.fc_out(x)
        return x


def build_model_under_limit(input_dim, num_classes, param_limit):
    w1 = 512
    w2 = 256
    dropout = 0.15
    bn_pre_out = True

    def instantiate(w1_val, w2_val):
        return MLPResNet(input_dim, num_classes, width1=w1_val, width2=w2_val, dropout=dropout, bn_pre_out=bn_pre_out)

    model = instantiate(w1, w2)
    params = count_parameters(model)
    if params <= param_limit:
        return model

    # Reduce widths until under limit
    while params > param_limit and (w1 > 96 or w2 > 64):
        if w1 > w2 * 2:
            w1 = max(96, w1 - 32)
        else:
            w2 = max(64, w2 - 16)
        model = instantiate(w1, w2)
        params = count_parameters(model)

    # As a final fallback, build a simpler 2-layer MLP if still over limit
    if params > param_limit:
        hidden = 384
        class SimpleMLP(nn.Module):
            def __init__(self, in_dim, num_cls, h):
                super().__init__()
                self.net = nn.Sequential(
                    nn.Linear(in_dim, h),
                    nn.ReLU(),
                    nn.Dropout(0.1),
                    nn.Linear(h, num_cls),
                )
            def forward(self, x):
                return self.net(x)
        model = SimpleMLP(input_dim, num_classes, hidden)
    return model


@torch.no_grad()
def evaluate(model, loader, device):
    model.eval()
    total = 0
    correct = 0
    loss_sum = 0.0
    criterion = nn.CrossEntropyLoss()
    for xb, yb in loader:
        xb = xb.to(device=device, dtype=torch.float32, non_blocking=False)
        yb = yb.to(device=device, dtype=torch.long, non_blocking=False)
        logits = model(xb)
        loss = criterion(logits, yb)
        loss_sum += loss.item() * yb.numel()
        preds = logits.argmax(dim=1)
        correct += (preds == yb).sum().item()
        total += yb.numel()
    acc = correct / total if total > 0 else 0.0
    loss_avg = loss_sum / total if total > 0 else 0.0
    return acc, loss_avg


class Solution:
    def solve(self, train_loader, val_loader, metadata: dict = None) -> torch.nn.Module:
        torch.manual_seed(42)

        device = torch.device(metadata.get("device", "cpu") if metadata is not None else "cpu")
        input_dim = int(metadata.get("input_dim", 384)) if metadata else 384
        num_classes = int(metadata.get("num_classes", 128)) if metadata else 128
        param_limit = int(metadata.get("param_limit", 500000)) if metadata else 500000

        model = build_model_under_limit(input_dim, num_classes, param_limit)
        model.to(device)

        # Ensure hard constraint
        if count_parameters(model) > param_limit:
            # Last-resort tiny model
            hidden = 256
            model = nn.Sequential(
                nn.Linear(input_dim, hidden),
                nn.ReLU(),
                nn.Dropout(0.1),
                nn.Linear(hidden, num_classes),
            ).to(device)

        # Optimizer and training setup
        wd = 5e-4
        optimizer = optim.AdamW(model.parameters(), lr=3e-3, weight_decay=wd)
        criterion = nn.CrossEntropyLoss(label_smoothing=0.10)

        epochs = 200
        steps_per_epoch = max(1, len(train_loader))
        total_steps = steps_per_epoch * epochs
        # OneCycleLR setup
        scheduler = optim.lr_scheduler.OneCycleLR(
            optimizer,
            max_lr=3e-3,
            steps_per_epoch=steps_per_epoch,
            epochs=epochs,
            pct_start=0.2,
            div_factor=10.0,
            final_div_factor=100.0,
            anneal_strategy='cos'
        )

        best_state = copy.deepcopy(model.state_dict())
        best_acc = -1.0
        no_improve_epochs = 0
        patience = 40

        for epoch in range(epochs):
            model.train()
            for xb, yb in train_loader:
                xb = xb.to(device=device, dtype=torch.float32, non_blocking=False)
                yb = yb.to(device=device, dtype=torch.long, non_blocking=False)

                optimizer.zero_grad(set_to_none=True)
                logits = model(xb)
                loss = criterion(logits, yb)
                loss.backward()
                nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
                optimizer.step()
                scheduler.step()

            # Validation
            if val_loader is not None:
                val_acc, _ = evaluate(model, val_loader, device)
                if val_acc > best_acc:
                    best_acc = val_acc
                    best_state = copy.deepcopy(model.state_dict())
                    no_improve_epochs = 0
                else:
                    no_improve_epochs += 1
                if no_improve_epochs >= patience:
                    break

        if val_loader is not None:
            model.load_state_dict(best_state)

        model.to("cpu")
        return model
