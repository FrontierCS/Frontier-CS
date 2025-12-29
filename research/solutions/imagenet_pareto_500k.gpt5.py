import math
import copy
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.optim.swa_utils import AveragedModel, update_bn


def count_parameters(model):
    return sum(p.numel() for p in model.parameters() if p.requires_grad)


class LowRankResidual(nn.Module):
    def __init__(self, dim: int, hidden_dim: int = None, dropout: float = 0.1):
        super().__init__()
        if hidden_dim is None:
            hidden_dim = max(1, dim // 2)
        self.norm = nn.LayerNorm(dim)
        self.fc1 = nn.Linear(dim, hidden_dim)
        self.act = nn.SiLU()
        self.dropout = nn.Dropout(dropout)
        self.fc2 = nn.Linear(hidden_dim, dim)

        self._init_weights()

    def _init_weights(self):
        nn.init.kaiming_normal_(self.fc1.weight, nonlinearity="relu")
        nn.init.zeros_(self.fc1.bias)
        nn.init.kaiming_normal_(self.fc2.weight, nonlinearity="linear")
        nn.init.zeros_(self.fc2.bias)
        nn.init.ones_(self.norm.weight)
        nn.init.zeros_(self.norm.bias)

    def forward(self, x):
        residual = x
        x = self.norm(x)
        x = self.fc1(x)
        x = self.act(x)
        x = self.dropout(x)
        x = self.fc2(x)
        x = self.dropout(x)
        return x + residual


class VectorNet(nn.Module):
    def __init__(
        self,
        input_dim: int,
        num_classes: int,
        hidden1: int = 512,
        hidden2: int = 256,
        resblocks: int = 2,
        res_hidden_ratio: float = 0.5,
        dropout: float = 0.15,
        use_input_bn: bool = True,
    ):
        super().__init__()
        self.use_input_bn = use_input_bn
        if use_input_bn:
            self.in_bn = nn.BatchNorm1d(input_dim, affine=True)

        self.fc1 = nn.Linear(input_dim, hidden1)
        self.bn1 = nn.BatchNorm1d(hidden1)
        self.fc2 = nn.Linear(hidden1, hidden2)
        self.bn2 = nn.BatchNorm1d(hidden2)
        self.act = nn.SiLU()
        self.drop = nn.Dropout(dropout)

        self.blocks = nn.ModuleList(
            [LowRankResidual(hidden2, hidden_dim=max(1, int(hidden2 * res_hidden_ratio)), dropout=dropout)
             for _ in range(resblocks)]
        )

        self.head = nn.Linear(hidden2, num_classes)
        self._init_weights()

    def _init_weights(self):
        nn.init.kaiming_normal_(self.fc1.weight, nonlinearity="relu")
        nn.init.zeros_(self.fc1.bias)
        nn.init.kaiming_normal_(self.fc2.weight, nonlinearity="relu")
        nn.init.zeros_(self.fc2.bias)
        nn.init.kaiming_normal_(self.head.weight, nonlinearity="linear")
        nn.init.zeros_(self.head.bias)
        if self.use_input_bn:
            nn.init.ones_(self.in_bn.weight)
            nn.init.zeros_(self.in_bn.bias)
        nn.init.ones_(self.bn1.weight)
        nn.init.zeros_(self.bn1.bias)
        nn.init.ones_(self.bn2.weight)
        nn.init.zeros_(self.bn2.bias)

    def forward(self, x):
        if self.use_input_bn:
            x = self.in_bn(x)
        x = self.fc1(x)
        x = self.bn1(x)
        x = self.act(x)
        x = self.drop(x)
        x = self.fc2(x)
        x = self.bn2(x)
        x = self.act(x)
        x = self.drop(x)
        for blk in self.blocks:
            x = blk(x)
        out = self.head(x)
        return out


def accuracy(model, data_loader, device):
    model.eval()
    correct = 0
    total = 0
    with torch.no_grad():
        for inputs, targets in data_loader:
            inputs = inputs.to(device, non_blocking=False).float()
            targets = targets.to(device, non_blocking=False).long()
            outputs = model(inputs)
            preds = outputs.argmax(dim=1)
            correct += (preds == targets).sum().item()
            total += targets.numel()
    if total == 0:
        return 0.0
    return correct / total


def mixup_data(x, y, alpha=0.2):
    if alpha <= 0.0:
        return x, y, 1.0, None
    batch_size = x.size(0)
    lam = torch.distributions.Beta(alpha, alpha).sample().item()
    # Shuffle for pairing
    index = torch.randperm(batch_size, device=x.device)
    mixed_x = lam * x + (1 - lam) * x[index, :]
    y_a = y
    y_b = y[index]
    return mixed_x, (y_a, y_b), lam, index


def soft_cross_entropy(logits, target_soft):
    log_probs = F.log_softmax(logits, dim=1)
    loss = -(target_soft * log_probs).sum(dim=1).mean()
    return loss


class Solution:
    def solve(self, train_loader, val_loader, metadata: dict = None) -> torch.nn.Module:
        if metadata is None:
            metadata = {}
        input_dim = int(metadata.get("input_dim", 384))
        num_classes = int(metadata.get("num_classes", 128))
        param_limit = int(metadata.get("param_limit", 500_000))
        device_str = metadata.get("device", "cpu")
        device = torch.device(device_str if torch.cuda.is_available() and device_str != "cpu" else "cpu")

        # Attempt near-limit architecture
        attempted_configs = [
            dict(hidden1=512, hidden2=256, resblocks=2, res_hidden_ratio=0.5, dropout=0.15, use_input_bn=True),
            dict(hidden1=512, hidden2=256, resblocks=1, res_hidden_ratio=0.5, dropout=0.15, use_input_bn=True),
            dict(hidden1=384, hidden2=256, resblocks=1, res_hidden_ratio=0.5, dropout=0.15, use_input_bn=True),
            dict(hidden1=384, hidden2=256, resblocks=0, res_hidden_ratio=0.5, dropout=0.15, use_input_bn=True),
        ]

        model = None
        for cfg in attempted_configs:
            candidate = VectorNet(
                input_dim=input_dim,
                num_classes=num_classes,
                hidden1=cfg["hidden1"],
                hidden2=cfg["hidden2"],
                resblocks=cfg["resblocks"],
                res_hidden_ratio=cfg["res_hidden_ratio"],
                dropout=cfg["dropout"],
                use_input_bn=cfg["use_input_bn"],
            )
            pcount = count_parameters(candidate)
            if pcount <= param_limit:
                model = candidate
                break

        if model is None:
            # Fallback minimal model
            model = nn.Sequential(
                nn.Linear(input_dim, 384),
                nn.ReLU(inplace=True),
                nn.Linear(384, 256),
                nn.ReLU(inplace=True),
                nn.Linear(256, num_classes),
            )

        model.to(device)

        # Training setup
        epochs = 180
        steps_per_epoch = max(1, len(train_loader))
        total_steps = epochs * steps_per_epoch

        # Optimizer and scheduler
        base_lr = 0.003
        optimizer = torch.optim.AdamW(model.parameters(), lr=base_lr, weight_decay=1e-4, betas=(0.9, 0.99))
        scheduler = torch.optim.lr_scheduler.OneCycleLR(
            optimizer,
            max_lr=0.005,
            epochs=epochs,
            steps_per_epoch=steps_per_epoch,
            pct_start=0.2,
            div_factor=10.0,
            final_div_factor=1000.0,
            anneal_strategy="cos",
        )

        # Losses and regularization
        label_smoothing = 0.08
        ce_loss = nn.CrossEntropyLoss(label_smoothing=label_smoothing)

        # Mixup settings - decays over time
        mixup_alpha_init = 0.15
        mixup_alpha_final = 0.0
        mixup_decay_epochs = int(0.8 * epochs)

        # SWA setup
        use_swa = True
        swa_start = int(0.6 * epochs)
        swa_model = AveragedModel(model) if use_swa else None

        best_val_acc = -1.0
        best_state = copy.deepcopy(model.state_dict())
        patience = 30
        epochs_no_improve = 0

        for epoch in range(epochs):
            model.train()
            # Compute current mixup alpha schedule
            if epoch < mixup_decay_epochs:
                mixup_alpha = mixup_alpha_init + (mixup_alpha_final - mixup_alpha_init) * (epoch / max(1, mixup_decay_epochs))
            else:
                mixup_alpha = mixup_alpha_final

            for batch in train_loader:
                inputs, targets = batch
                inputs = inputs.to(device, non_blocking=False).float()
                targets = targets.to(device, non_blocking=False).long()

                optimizer.zero_grad(set_to_none=True)

                if mixup_alpha > 0.0:
                    mixed_inputs, (y_a, y_b), lam, _ = mixup_data(inputs, targets, alpha=mixup_alpha)
                    outputs = model(mixed_inputs)
                    # Create soft targets
                    with torch.no_grad():
                        y_a_soft = F.one_hot(y_a, num_classes=num_classes).float()
                        y_b_soft = F.one_hot(y_b, num_classes=num_classes).float()
                        soft_targets = lam * y_a_soft + (1 - lam) * y_b_soft
                    loss = soft_cross_entropy(outputs, soft_targets)
                else:
                    outputs = model(inputs)
                    loss = ce_loss(outputs, targets)

                loss.backward()
                torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
                optimizer.step()
                scheduler.step()

            # SWA update per epoch after swa_start
            if use_swa and epoch >= swa_start:
                swa_model.update_parameters(model)

            # Validation
            val_acc = accuracy(model, val_loader, device)
            if val_acc > best_val_acc:
                best_val_acc = val_acc
                best_state = copy.deepcopy(model.state_dict())
                epochs_no_improve = 0
            else:
                epochs_no_improve += 1

            if epochs_no_improve >= patience:
                break

        # Load best model state
        model.load_state_dict(best_state)

        # Evaluate SWA option and select best
        if use_swa:
            # Update BN stats for SWA model
            swa_model.to(device)
            try:
                update_bn(train_loader, swa_model, device=device)
            except TypeError:
                # Older PyTorch versions do not accept device kwarg
                update_bn(train_loader, swa_model)
            val_acc_base = accuracy(model, val_loader, device)
            val_acc_swa = accuracy(swa_model, val_loader, device)
            if val_acc_swa >= val_acc_base:
                model.load_state_dict(copy.deepcopy(swa_model.state_dict()))

        model.to("cpu")
        model.eval()
        return model