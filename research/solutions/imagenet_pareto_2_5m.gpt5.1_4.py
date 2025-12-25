import torch
import torch.nn as nn
import torch.optim as optim
import numpy as np
import random
import copy


class ResidualMLP(nn.Module):
    def __init__(
        self,
        input_dim: int,
        num_classes: int,
        hidden_dim1: int = 1024,
        hidden_dim2: int = 1024,
        hidden_dim3: int = 512,
        hidden_dim4: int = 512,
        dropout_prob: float = 0.1,
    ):
        super().__init__()

        self.input_norm = nn.BatchNorm1d(input_dim)

        self.fc1 = nn.Linear(input_dim, hidden_dim1)
        self.bn1 = nn.BatchNorm1d(hidden_dim1)

        self.fc2 = nn.Linear(hidden_dim1, hidden_dim2)
        self.bn2 = nn.BatchNorm1d(hidden_dim2)

        self.fc3 = nn.Linear(hidden_dim2, hidden_dim3)
        self.bn3 = nn.BatchNorm1d(hidden_dim3)

        self.fc4 = nn.Linear(hidden_dim3, hidden_dim4)
        self.bn4 = nn.BatchNorm1d(hidden_dim4)

        self.output_layer = nn.Linear(hidden_dim4, num_classes)

        self.dropout = nn.Dropout(dropout_prob)
        self.activation = nn.ReLU()

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self.input_norm(x)

        x = self.fc1(x)
        x = self.bn1(x)
        x = self.activation(x)
        x = self.dropout(x)

        # Residual block 1 (hidden_dim1 == hidden_dim2)
        res1 = x
        x = self.fc2(x)
        x = self.bn2(x)
        x = self.activation(x)
        x = self.dropout(x)
        x = x + res1

        # Compression to hidden_dim3
        x = self.fc3(x)
        x = self.bn3(x)
        x = self.activation(x)
        x = self.dropout(x)

        # Residual block 2 (hidden_dim3 == hidden_dim4)
        res2 = x
        x = self.fc4(x)
        x = self.bn4(x)
        x = self.activation(x)
        x = self.dropout(x)
        x = x + res2

        logits = self.output_layer(x)
        return logits


class Solution:
    def _build_model(self, input_dim: int, num_classes: int, param_limit: int) -> nn.Module:
        # Try scaled versions of a high-capacity residual MLP until parameter limit is satisfied.
        base_hidden1 = 1024
        base_hidden3 = 512

        scale = 1.0
        chosen_model = None

        while scale >= 0.25:
            h1 = max(64, int(base_hidden1 * scale))
            h2 = h1
            h3 = max(64, int(base_hidden3 * scale))
            h4 = h3

            model = ResidualMLP(
                input_dim=input_dim,
                num_classes=num_classes,
                hidden_dim1=h1,
                hidden_dim2=h2,
                hidden_dim3=h3,
                hidden_dim4=h4,
                dropout_prob=0.1,
            )

            param_count = sum(p.numel() for p in model.parameters() if p.requires_grad)
            if param_count <= param_limit:
                chosen_model = model
                break

            scale *= 0.8

        if chosen_model is None:
            # Fallback to a simple linear classifier if param_limit is extremely small
            chosen_model = nn.Linear(input_dim, num_classes)

        return chosen_model

    def solve(self, train_loader, val_loader, metadata: dict = None) -> torch.nn.Module:
        if metadata is None:
            metadata = {}

        # Set seeds for reproducibility
        seed = 42
        random.seed(seed)
        np.random.seed(seed)
        torch.manual_seed(seed)

        # Extract metadata
        input_dim = int(metadata.get("input_dim", 384))
        num_classes = int(metadata.get("num_classes", 128))
        param_limit = int(metadata.get("param_limit", 2_500_000))
        device_str = metadata.get("device", "cpu")

        if device_str.startswith("cuda") and torch.cuda.is_available():
            device = torch.device(device_str)
        else:
            device = torch.device("cpu")

        # Build model under parameter constraint
        model = self._build_model(input_dim, num_classes, param_limit)
        model.to(device)

        # Double-check parameter limit
        param_count = sum(p.numel() for p in model.parameters() if p.requires_grad)
        if param_count > param_limit:
            # As a safety fallback, use a very small model
            model = nn.Linear(input_dim, num_classes).to(device)

        # Training setup
        criterion = nn.CrossEntropyLoss()

        # Slightly conservative learning rate and weight decay for small synthetic dataset
        optimizer = optim.AdamW(model.parameters(), lr=1e-3, weight_decay=1e-4)

        # Adaptive learning rate scheduler based on validation accuracy
        scheduler = optim.lr_scheduler.ReduceLROnPlateau(
            optimizer,
            mode="max",
            factor=0.5,
            patience=5,
            threshold=1e-4,
            min_lr=1e-5,
            verbose=False,
        )

        train_samples = metadata.get("train_samples", None)
        if train_samples is None:
            max_epochs = 200
        else:
            if train_samples <= 4000:
                max_epochs = 250
            elif train_samples <= 20000:
                max_epochs = 150
            else:
                max_epochs = 100

        early_stopping_patience = max(15, max_epochs // 6)

        def evaluate(model_eval, loader):
            model_eval.eval()
            total = 0
            correct = 0
            running_loss = 0.0
            with torch.no_grad():
                for inputs, targets in loader:
                    inputs = inputs.to(device).float()
                    targets = targets.to(device).long()

                    outputs = model_eval(inputs)
                    loss = criterion(outputs, targets)

                    running_loss += loss.item() * targets.size(0)
                    _, preds = torch.max(outputs, dim=1)
                    correct += (preds == targets).sum().item()
                    total += targets.size(0)

            if total == 0:
                return 0.0, 0.0
            avg_loss = running_loss / total
            acc = correct / total
            return avg_loss, acc

        best_val_acc = 0.0
        best_state_dict = copy.deepcopy(model.state_dict())
        epochs_without_improvement = 0

        for epoch in range(max_epochs):
            model.train()
            for inputs, targets in train_loader:
                inputs = inputs.to(device).float()
                targets = targets.to(device).long()

                optimizer.zero_grad(set_to_none=True)
                outputs = model(inputs)
                loss = criterion(outputs, targets)
                loss.backward()
                optimizer.step()

            # Validation
            val_loss, val_acc = evaluate(model, val_loader)

            scheduler.step(val_acc)

            if val_acc > best_val_acc + 1e-4:
                best_val_acc = val_acc
                best_state_dict = copy.deepcopy(model.state_dict())
                epochs_without_improvement = 0
            else:
                epochs_without_improvement += 1

            if epochs_without_improvement >= early_stopping_patience:
                break

        # Load best model weights
        model.load_state_dict(best_state_dict)
        model.to(device)
        model.eval()

        return model
