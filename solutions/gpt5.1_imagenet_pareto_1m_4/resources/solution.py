import torch
import torch.nn as nn
import torch.optim as optim


class MLPNet(nn.Module):
    def __init__(self, input_dim, num_classes, hidden_dims, dropout=0.1, mean=None, std=None):
        super().__init__()
        self.input_dim = input_dim

        if mean is not None and std is not None:
            self.register_buffer("mean", mean.clone().detach())
            self.register_buffer("std", std.clone().detach())
            self.use_norm = True
        else:
            self.register_buffer("mean", torch.zeros(input_dim))
            self.register_buffer("std", torch.ones(input_dim))
            self.use_norm = False

        layers = []
        in_dim = input_dim
        for h in hidden_dims:
            layers.append(nn.Linear(in_dim, h))
            layers.append(nn.BatchNorm1d(h))
            layers.append(nn.GELU())
            if dropout > 0.0:
                layers.append(nn.Dropout(dropout))
            in_dim = h
        self.features = nn.Sequential(*layers)
        self.classifier = nn.Linear(in_dim, num_classes)

    def forward(self, x):
        x = x.view(x.size(0), -1)
        if self.use_norm:
            x = (x - self.mean) / self.std
        x = self.features(x)
        x = self.classifier(x)
        return x


class Solution:
    def _compute_dataset_stats(self, train_loader, input_dim, device):
        sum_x = torch.zeros(input_dim, device=device)
        sum_x2 = torch.zeros(input_dim, device=device)
        count = 0

        with torch.no_grad():
            for inputs, _ in train_loader:
                inputs = inputs.to(device)
                inputs = inputs.view(inputs.size(0), -1)
                sum_x += inputs.sum(dim=0)
                sum_x2 += (inputs * inputs).sum(dim=0)
                count += inputs.size(0)

        if count == 0:
            mean = torch.zeros(input_dim, device=device)
            std = torch.ones(input_dim, device=device)
        else:
            mean = sum_x / count
            var = sum_x2 / count - mean * mean
            var = torch.clamp(var, min=1e-6)
            std = torch.sqrt(var)

        return mean, std

    def _build_model(self, input_dim, num_classes, param_limit, mean, std):
        # Start with a high-capacity configuration under 1M params for (384, 128)
        hidden_dims = [512, 512, 512, 384]
        dropout = 0.1

        # Adjust hidden dims downwards if we exceed the parameter limit
        while True:
            model = MLPNet(input_dim, num_classes, hidden_dims, dropout=dropout, mean=mean, std=std)
            param_count = sum(p.numel() for p in model.parameters() if p.requires_grad)
            if param_limit is None or param_count <= param_limit:
                break
            if all(h <= 32 for h in hidden_dims):
                break
            hidden_dims = [max(32, int(h * 0.9)) for h in hidden_dims]

        return model

    def _train_model(self, model, train_loader, val_loader, device, max_epochs=150):
        criterion = nn.CrossEntropyLoss(label_smoothing=0.1)
        optimizer = optim.AdamW(model.parameters(), lr=1e-3, weight_decay=1e-4)
        patience = 20
        best_val_acc = None
        best_state = None
        epochs_no_improve = 0

        for _ in range(max_epochs):
            model.train()
            for inputs, targets in train_loader:
                inputs = inputs.to(device)
                targets = targets.to(device, dtype=torch.long)

                optimizer.zero_grad()
                outputs = model(inputs)
                loss = criterion(outputs, targets)
                loss.backward()
                nn.utils.clip_grad_norm_(model.parameters(), max_norm=5.0)
                optimizer.step()

            if val_loader is not None:
                model.eval()
                correct = 0
                total = 0
                with torch.no_grad():
                    for inputs, targets in val_loader:
                        inputs = inputs.to(device)
                        targets = targets.to(device, dtype=torch.long)
                        outputs = model(inputs)
                        loss = criterion(outputs, targets)
                        preds = outputs.argmax(dim=1)
                        correct += (preds == targets).sum().item()
                        total += targets.size(0)

                val_acc = correct / total if total > 0 else 0.0

                if best_val_acc is None or val_acc > best_val_acc + 1e-4:
                    best_val_acc = val_acc
                    best_state = {k: v.cpu().clone() for k, v in model.state_dict().items()}
                    epochs_no_improve = 0
                else:
                    epochs_no_improve += 1
                    if epochs_no_improve >= patience:
                        break

        if best_state is not None:
            model.load_state_dict(best_state)

        return model

    def solve(self, train_loader, val_loader, metadata: dict = None) -> torch.nn.Module:
        if metadata is None:
            metadata = {}

        device_str = metadata.get("device", "cpu")
        device = torch.device(device_str)

        input_dim = int(metadata.get("input_dim", 384))
        num_classes = int(metadata.get("num_classes", 128))
        param_limit = int(metadata.get("param_limit", 1_000_000))

        mean, std = self._compute_dataset_stats(train_loader, input_dim, device=torch.device("cpu"))

        model = self._build_model(input_dim, num_classes, param_limit, mean.cpu(), std.cpu())
        model.to(device)

        # Safety check: ensure parameter constraint
        param_count = sum(p.numel() for p in model.parameters() if p.requires_grad)
        if param_limit is not None and param_count > param_limit:
            model = MLPNet(input_dim, num_classes, hidden_dims=[128], dropout=0.0, mean=mean.cpu(), std=std.cpu())
            model.to(device)

        max_epochs = 150
        train_samples = metadata.get("train_samples", None)
        if train_samples is not None:
            if train_samples < 1500:
                max_epochs = 200
            elif train_samples > 5000:
                max_epochs = 100

        self._train_model(model, train_loader, val_loader, device, max_epochs=max_epochs)
        model.eval()
        return model
