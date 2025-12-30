import torch
import torch.nn as nn
import torch.optim as optim
import random
import numpy as np
import copy


class MLPNet(nn.Module):
    def __init__(self, input_dim, num_classes, hidden_dims, dropout=0.1):
        super().__init__()
        layers = []
        prev_dim = input_dim
        for h in hidden_dims:
            layers.append(nn.Linear(prev_dim, h))
            layers.append(nn.BatchNorm1d(h))
            layers.append(nn.GELU())
            if dropout > 0.0:
                layers.append(nn.Dropout(dropout))
            prev_dim = h
        layers.append(nn.Linear(prev_dim, num_classes))
        self.net = nn.Sequential(*layers)
        self._init_weights()

    def _init_weights(self):
        for m in self.modules():
            if isinstance(m, nn.Linear):
                nn.init.kaiming_normal_(m.weight, nonlinearity="relu")
                if m.bias is not None:
                    nn.init.zeros_(m.bias)
            elif isinstance(m, nn.BatchNorm1d):
                nn.init.ones_(m.weight)
                nn.init.zeros_(m.bias)

    def forward(self, x):
        if x.dim() > 2:
            x = x.view(x.size(0), -1)
        x = x.float()
        return self.net(x)


class Solution:
    def _build_model(self, input_dim, num_classes, param_limit):
        candidate_hidden_configs = [
            (768, 512, 256),
            (640, 640, 320),
            (768, 384, 256),
            (640, 512, 256),
            (512, 512, 256),
            (512, 512),
            (512, 384),
            (512,),
            (384, 384),
            (384,),
            (),
        ]
        for hidden_dims in candidate_hidden_configs:
            dropout = 0.1 if len(hidden_dims) > 0 else 0.0
            model = MLPNet(input_dim, num_classes, hidden_dims, dropout=dropout)
            param_count = sum(p.numel() for p in model.parameters() if p.requires_grad)
            if param_count <= param_limit:
                return model
        model = MLPNet(input_dim, num_classes, (), dropout=0.0)
        return model

    def _evaluate(self, model, loader, criterion, device):
        model.eval()
        total_loss = 0.0
        correct = 0
        total = 0
        with torch.no_grad():
            for inputs, targets in loader:
                inputs = inputs.to(device)
                targets = targets.to(device)
                outputs = model(inputs)
                loss = criterion(outputs, targets)
                batch_size = targets.size(0)
                total_loss += loss.item() * batch_size
                preds = outputs.argmax(dim=1)
                correct += (preds == targets).sum().item()
                total += batch_size
        if total == 0:
            return 0.0, 0.0
        return total_loss / total, correct / total

    def solve(self, train_loader, val_loader, metadata: dict = None) -> torch.nn.Module:
        if metadata is None:
            metadata = {}

        seed = 42
        random.seed(seed)
        np.random.seed(seed)
        torch.manual_seed(seed)

        device_str = metadata.get("device", "cpu")
        device = torch.device("cpu")

        input_dim = int(metadata.get("input_dim", 384))
        num_classes = int(metadata.get("num_classes", 128))
        param_limit = int(metadata.get("param_limit", 1_000_000))
        train_samples = metadata.get("train_samples", None)
        if train_samples is None:
            try:
                train_samples = len(train_loader.dataset)
            except Exception:
                train_samples = 2048

        model = self._build_model(input_dim, num_classes, param_limit)
        model.to(device)

        total_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
        if total_params > param_limit:
            model = MLPNet(input_dim, num_classes, (), dropout=0.0)
            model.to(device)

        if train_samples <= 4096:
            max_epochs = 400
            patience = 40
        else:
            max_epochs = 200
            patience = 30

        criterion = nn.CrossEntropyLoss()
        optimizer = optim.AdamW(model.parameters(), lr=1e-3, weight_decay=1e-2)
        scheduler = optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=max_epochs, eta_min=1e-5)

        best_val_acc = 0.0
        best_state_dict = None
        epochs_no_improve = 0

        for epoch in range(max_epochs):
            model.train()
            for inputs, targets in train_loader:
                inputs = inputs.to(device)
                targets = targets.to(device)

                optimizer.zero_grad(set_to_none=True)
                outputs = model(inputs)
                loss = criterion(outputs, targets)
                loss.backward()
                nn.utils.clip_grad_norm_(model.parameters(), max_norm=5.0)
                optimizer.step()

            _, val_acc = self._evaluate(model, val_loader, criterion, device)
            scheduler.step()

            if val_acc > best_val_acc + 1e-4:
                best_val_acc = val_acc
                best_state_dict = copy.deepcopy(model.state_dict())
                epochs_no_improve = 0
            else:
                epochs_no_improve += 1
                if epochs_no_improve >= patience:
                    break

        if best_state_dict is not None:
            model.load_state_dict(best_state_dict)

        model.to("cpu")
        model.eval()
        return model