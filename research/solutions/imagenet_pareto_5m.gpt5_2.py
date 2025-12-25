import math
import copy
import torch
import torch.nn as nn
import torch.nn.functional as F


class ResidualBlock(nn.Module):
    def __init__(self, dim, dropout=0.1):
        super().__init__()
        self.norm = nn.LayerNorm(dim)
        self.fc = nn.Linear(dim, dim, bias=True)
        self.dropout = nn.Dropout(dropout)

    def forward(self, x):
        y = self.norm(x)
        y = F.gelu(y)
        y = self.fc(y)
        y = self.dropout(y)
        return x + y


class ResidualMLP(nn.Module):
    def __init__(self, in_dim, hidden_dim, out_dim, num_blocks=4, dropout=0.1,
                 use_input_norm=True, use_hidden_stem_norm=True, use_preout_norm=True):
        super().__init__()
        self.use_input_norm = use_input_norm
        self.use_hidden_stem_norm = use_hidden_stem_norm
        self.use_preout_norm = use_preout_norm

        if use_input_norm:
            self.input_norm = nn.LayerNorm(in_dim)
        else:
            self.input_norm = nn.Identity()

        self.fc_in = nn.Linear(in_dim, hidden_dim, bias=True)

        if use_hidden_stem_norm:
            self.stem_norm = nn.LayerNorm(hidden_dim)
        else:
            self.stem_norm = nn.Identity()

        self.blocks = nn.ModuleList([ResidualBlock(hidden_dim, dropout=dropout) for _ in range(num_blocks)])

        if use_preout_norm:
            self.preout_norm = nn.LayerNorm(hidden_dim)
        else:
            self.preout_norm = nn.Identity()

        self.fc_out = nn.Linear(hidden_dim, out_dim, bias=True)

    def forward(self, x):
        x = self.input_norm(x)
        x = self.fc_in(x)
        x = F.gelu(self.stem_norm(x))
        for blk in self.blocks:
            x = blk(x)
        x = self.preout_norm(x)
        x = self.fc_out(x)
        return x


def count_trainable_params(model: nn.Module) -> int:
    return sum(p.numel() for p in model.parameters() if p.requires_grad)


def estimate_params(in_dim, hidden, out_dim, blocks,
                    use_input_norm=True, use_hidden_stem_norm=True, use_preout_norm=True):
    # Linear parameters (+bias)
    p = 0
    # input projection
    p += in_dim * hidden + hidden
    # residual block linears
    p += blocks * (hidden * hidden + hidden)
    # output
    p += hidden * out_dim + out_dim
    # norms
    if use_input_norm:
        p += 2 * in_dim
    if use_hidden_stem_norm:
        p += 2 * hidden
    # each block has one LayerNorm
    p += blocks * (2 * hidden)
    if use_preout_norm:
        p += 2 * hidden
    return p


def build_parameter_groups(model: nn.Module, weight_decay: float):
    decay_params = []
    no_decay_params = []
    for module_name, module in model.named_modules():
        for name, param in module.named_parameters(recurse=False):
            if not param.requires_grad:
                continue
            if isinstance(module, (nn.LayerNorm, nn.BatchNorm1d, nn.BatchNorm2d, nn.BatchNorm3d)):
                no_decay_params.append(param)
            elif name.endswith('bias'):
                no_decay_params.append(param)
            else:
                decay_params.append(param)
    return [
        {'params': decay_params, 'weight_decay': weight_decay},
        {'params': no_decay_params, 'weight_decay': 0.0}
    ]


class EMA:
    def __init__(self, model: nn.Module, decay=0.995):
        self.decay = decay
        self.shadow = {}
        self.backup = {}
        for name, param in model.named_parameters():
            if param.requires_grad:
                self.shadow[name] = param.detach().clone()

    def update(self, model: nn.Module):
        d = self.decay
        for name, param in model.named_parameters():
            if param.requires_grad:
                assert name in self.shadow
                self.shadow[name].mul_(d).add_(param.detach(), alpha=1 - d)

    def apply_to(self, model: nn.Module):
        for name, param in model.named_parameters():
            if param.requires_grad:
                param.data.copy_(self.shadow[name].data)


def evaluate(model: nn.Module, loader, device):
    model.eval()
    total = 0
    correct = 0
    loss_sum = 0.0
    criterion = nn.CrossEntropyLoss()
    with torch.no_grad():
        for inputs, targets in loader:
            inputs = inputs.to(device)
            targets = targets.to(device)
            outputs = model(inputs)
            loss = criterion(outputs, targets)
            loss_sum += loss.item() * targets.size(0)
            preds = outputs.argmax(dim=1)
            correct += (preds == targets).sum().item()
            total += targets.numel()
    acc = correct / total if total > 0 else 0.0
    loss_avg = loss_sum / total if total > 0 else 0.0
    return acc, loss_avg


class Solution:
    def solve(self, train_loader, val_loader, metadata: dict = None) -> torch.nn.Module:
        torch.manual_seed(42)
        if torch.cuda.is_available():
            torch.cuda.manual_seed_all(42)

        input_dim = int(metadata.get("input_dim", 384))
        num_classes = int(metadata.get("num_classes", 128))
        param_limit = int(metadata.get("param_limit", 5_000_000))
        device = torch.device(metadata.get("device", "cpu"))

        # Architectural choices
        blocks = 4
        dropout = 0.1
        use_input_norm = True
        use_hidden_stem_norm = True
        use_preout_norm = True

        # Determine the maximal hidden size within parameter budget
        # Start from analytical approximation then step down
        # approx solve for hidden ~ sqrt((limit - linear terms)/blocks)
        linear_terms = input_dim + num_classes + (blocks + 1)  # biases roughly
        approx_hidden = int(math.sqrt(max(1, (param_limit - 10000) / max(1, blocks))))  # rough start
        approx_hidden = min(max(512, approx_hidden), 2000)

        hidden = approx_hidden
        # refine down to fit limit
        while hidden > 64:
            est = estimate_params(
                input_dim, hidden, num_classes, blocks,
                use_input_norm, use_hidden_stem_norm, use_preout_norm
            )
            if est <= param_limit:
                break
            hidden -= 1
        # As an extra guardrail, construct and validate actual count; if too big, reduce further
        while hidden > 64:
            model = ResidualMLP(
                in_dim=input_dim,
                hidden_dim=hidden,
                out_dim=num_classes,
                num_blocks=blocks,
                dropout=dropout,
                use_input_norm=use_input_norm,
                use_hidden_stem_norm=use_hidden_stem_norm,
                use_preout_norm=use_preout_norm
            )
            pcount = count_trainable_params(model)
            if pcount <= param_limit:
                break
            hidden -= 1

        # Final model
        model = ResidualMLP(
            in_dim=input_dim,
            hidden_dim=hidden,
            out_dim=num_classes,
            num_blocks=blocks,
            dropout=dropout,
            use_input_norm=use_input_norm,
            use_hidden_stem_norm=use_hidden_stem_norm,
            use_preout_norm=use_preout_norm
        )
        model.to(device)

        # Optimizer with weight decay on weights only
        weight_decay = 1e-4
        param_groups = build_parameter_groups(model, weight_decay)
        optimizer = torch.optim.AdamW(param_groups, lr=0.003, betas=(0.9, 0.999))

        # Scheduler: OneCycle to rapidly converge
        epochs = 85
        steps_per_epoch = max(1, len(train_loader))
        scheduler = torch.optim.lr_scheduler.OneCycleLR(
            optimizer,
            max_lr=0.003,
            epochs=epochs,
            steps_per_epoch=steps_per_epoch,
            pct_start=0.15,
            anneal_strategy='cos',
            div_factor=10.0,
            final_div_factor=100.0
        )

        # Loss
        criterion = nn.CrossEntropyLoss()

        # EMA
        ema = EMA(model, decay=0.995)

        # Training loop with early stopping
        best_state = copy.deepcopy({k: v.cpu().clone() for k, v in model.state_dict().items()})
        best_acc = -1.0
        patience = 18
        epochs_no_improve = 0

        for epoch in range(epochs):
            model.train()
            for inputs, targets in train_loader:
                inputs = inputs.to(device)
                targets = targets.to(device)

                optimizer.zero_grad(set_to_none=True)
                outputs = model(inputs)
                loss = criterion(outputs, targets)
                loss.backward()
                torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
                optimizer.step()
                scheduler.step()
                ema.update(model)

            # Validate with EMA weights applied for stability
            current_state = copy.deepcopy({k: v.cpu().clone() for k, v in model.state_dict().items()})
            ema.apply_to(model)
            val_acc, _ = evaluate(model, val_loader, device)
            # Restore current weights after EMA eval
            model.load_state_dict(current_state)

            if val_acc > best_acc + 1e-5:
                best_acc = val_acc
                best_state = copy.deepcopy({k: v.cpu().clone() for k, v in ema.shadow.items()})
                epochs_no_improve = 0
            else:
                epochs_no_improve += 1
                if epochs_no_improve >= patience:
                    break

        # Load best EMA weights
        state_dict_to_load = {}
        for name, param in model.named_parameters():
            if name in best_state:
                state_dict_to_load[name] = best_state[name]
        # For buffers (e.g., LayerNorm running stats not present; LN has no buffers)
        model.load_state_dict({**model.state_dict(), **state_dict_to_load})

        model.to(device)
        return model
