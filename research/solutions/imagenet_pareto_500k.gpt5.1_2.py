import torch
import torch.nn as nn
import torch.nn.functional as F
import copy


def count_trainable_params(model: nn.Module) -> int:
    return sum(p.numel() for p in model.parameters() if p.requires_grad)


class MLPNet(nn.Module):
    def __init__(self, input_dim: int, num_classes: int, h1: int = 512, h2: int = 384, h3: int = 0, dropout: float = 0.2):
        super().__init__()
        layers = []

        layers.append(nn.Linear(input_dim, h1))
        layers.append(nn.BatchNorm1d(h1))
        layers.append(nn.ReLU(inplace=True))
        layers.append(nn.Dropout(dropout))

        layers.append(nn.Linear(h1, h2))
        layers.append(nn.BatchNorm1d(h2))
        layers.append(nn.ReLU(inplace=True))
        layers.append(nn.Dropout(dropout))

        in_features_last = h2
        if h3 is not None and h3 > 0:
            layers.append(nn.Linear(h2, h3))
            layers.append(nn.BatchNorm1d(h3))
            layers.append(nn.ReLU(inplace=True))
            layers.append(nn.Dropout(dropout))
            in_features_last = h3

        layers.append(nn.Linear(in_features_last, num_classes))

        self.net = nn.Sequential(*layers)
        self._initialize()

    def _initialize(self):
        for m in self.modules():
            if isinstance(m, nn.Linear):
                nn.init.kaiming_normal_(m.weight, nonlinearity='relu')
                if m.bias is not None:
                    nn.init.zeros_(m.bias)
            elif isinstance(m, nn.BatchNorm1d):
                nn.init.ones_(m.weight)
                nn.init.zeros_(m.bias)

    def forward(self, x):
        if x.dim() > 2:
            x = x.view(x.size(0), -1)
        return self.net(x)


class SimpleMLP2Layer(nn.Module):
    def __init__(self, input_dim: int, num_classes: int, hidden: int, dropout: float = 0.2):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(input_dim, hidden),
            nn.BatchNorm1d(hidden),
            nn.ReLU(inplace=True),
            nn.Dropout(dropout),
            nn.Linear(hidden, num_classes),
        )
        self._initialize()

    def _initialize(self):
        for m in self.modules():
            if isinstance(m, nn.Linear):
                nn.init.kaiming_normal_(m.weight, nonlinearity='relu')
                if m.bias is not None:
                    nn.init.zeros_(m.bias)
            elif isinstance(m, nn.BatchNorm1d):
                nn.init.ones_(m.weight)
                nn.init.zeros_(m.bias)

    def forward(self, x):
        if x.dim() > 2:
            x = x.view(x.size(0), -1)
        return self.net(x)


def build_model(input_dim: int, num_classes: int, param_limit: int) -> nn.Module:
    # Try a 3-layer MLP as wide as possible under the parameter budget
    d0 = input_dim
    out = num_classes

    # Base widths for first two layers
    h1 = 512
    h2 = 384

    # Compute constant term C for 3-layer MLP with BatchNorm and dropout (no params)
    # Total_params = C + h3 * (h2 + out + 3)
    C = d0 * h1 + h1 + h1 * h2 + h2 + out + 2 * (h1 + h2)
    coeff_h3 = h2 + out + 3

    h3 = 0
    if param_limit > C + coeff_h3:  # ensure room for at least h3=1
        max_h3 = (param_limit - C) // coeff_h3
        if max_h3 > 0:
            h3 = int(min(max_h3, 512))

    if h3 > 0:
        model = MLPNet(input_dim, num_classes, h1=h1, h2=h2, h3=h3, dropout=0.2)
    else:
        # Fallback to 2-layer MLP, choose largest hidden size under budget
        # params = out + h1 * (d0 + out + 3)
        denom = d0 + out + 3
        if denom <= 0:
            hidden = 128
        else:
            max_h1 = (param_limit - out) // denom
            hidden = int(max(16, min(max_h1, 512)))
        model = SimpleMLP2Layer(input_dim, num_classes, hidden=hidden, dropout=0.2)

    # Safety check: if still over budget (due to miscalculation), shrink to a conservative baseline
    if count_trainable_params(model) > param_limit:
        hidden = min(384, (param_limit - num_classes) // (input_dim + num_classes + 3))
        hidden = max(64, hidden)
        model = SimpleMLP2Layer(input_dim, num_classes, hidden=hidden, dropout=0.2)

    return model


class Solution:
    def solve(self, train_loader, val_loader, metadata: dict = None) -> torch.nn.Module:
        if metadata is None:
            metadata = {}

        input_dim = int(metadata.get("input_dim", 384))
        num_classes = int(metadata.get("num_classes", 128))
        param_limit = int(metadata.get("param_limit", 500000))
        device_str = metadata.get("device", "cpu")

        if torch.cuda.is_available() and device_str.startswith("cuda"):
            device = torch.device(device_str)
        else:
            device = torch.device("cpu")

        torch.manual_seed(42)

        model = build_model(input_dim, num_classes, param_limit)
        model.to(device)

        # Final safety assert (should always pass)
        if count_trainable_params(model) > param_limit:
            # Extremely conservative fallback: single hidden layer 256 units
            hidden = min(256, (param_limit - num_classes) // (input_dim + num_classes + 3))
            hidden = max(32, hidden)
            model = SimpleMLP2Layer(input_dim, num_classes, hidden=hidden, dropout=0.2)
            model.to(device)

        criterion = nn.CrossEntropyLoss(label_smoothing=0.05)
        optimizer = torch.optim.AdamW(model.parameters(), lr=3e-3, weight_decay=1e-4)
        scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
            optimizer,
            mode="max",
            factor=0.5,
            patience=5,
            verbose=False,
            min_lr=1e-5,
        )

        max_epochs = 200
        early_stop_patience = 25

        best_state = copy.deepcopy(model.state_dict())
        best_val_acc = 0.0
        best_epoch = 0

        for epoch in range(max_epochs):
            model.train()
            for batch in train_loader:
                inputs, targets = batch
                inputs = inputs.to(device)
                targets = targets.to(device)

                if inputs.dtype != torch.float32:
                    inputs = inputs.float()

                optimizer.zero_grad(set_to_none=True)
                outputs = model(inputs)
                loss = criterion(outputs, targets)
                loss.backward()
                torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=5.0)
                optimizer.step()

            if val_loader is not None:
                model.eval()
                val_correct = 0
                val_total = 0
                with torch.no_grad():
                    for inputs, targets in val_loader:
                        inputs = inputs.to(device)
                        targets = targets.to(device)
                        if inputs.dtype != torch.float32:
                            inputs = inputs.float()
                        outputs = model(inputs)
                        preds = outputs.argmax(dim=1)
                        val_correct += (preds == targets).sum().item()
                        val_total += targets.numel()

                val_acc = float(val_correct) / float(val_total) if val_total > 0 else 0.0
                scheduler.step(val_acc)

                if val_acc > best_val_acc:
                    best_val_acc = val_acc
                    best_epoch = epoch
                    best_state = copy.deepcopy(model.state_dict())
                elif epoch - best_epoch >= early_stop_patience:
                    break
            else:
                # If no validation loader, still step scheduler with a dummy metric
                scheduler.step(0.0)

        if best_state is not None:
            model.load_state_dict(best_state)

        model.eval()
        return model