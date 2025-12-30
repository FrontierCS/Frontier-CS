import torch
import torch.nn as nn
import torch.optim as optim
import numpy as np
import copy

class Solution:
    def solve(self, train_loader, val_loader, metadata: dict = None) -> torch.nn.Module:
        input_dim = metadata["input_dim"]
        num_classes = metadata["num_classes"]
        device = torch.device(metadata.get("device", "cpu"))

        class DeepMLP(nn.Module):
            def __init__(self, input_dim, num_classes, hidden_dim=1054, dropout_p=0.25):
                super().__init__()
                self.layers = nn.Sequential(
                    nn.Linear(input_dim, hidden_dim),
                    nn.BatchNorm1d(hidden_dim),
                    nn.SiLU(),
                    nn.Dropout(p=dropout_p),

                    nn.Linear(hidden_dim, hidden_dim),
                    nn.BatchNorm1d(hidden_dim),
                    nn.SiLU(),
                    nn.Dropout(p=dropout_p),

                    nn.Linear(hidden_dim, hidden_dim),
                    nn.BatchNorm1d(hidden_dim),
                    nn.SiLU(),
                    nn.Dropout(p=dropout_p),

                    nn.Linear(hidden_dim, hidden_dim),
                    nn.BatchNorm1d(hidden_dim),
                    nn.SiLU(),
                    nn.Dropout(p=dropout_p),

                    nn.Linear(hidden_dim, hidden_dim),
                    nn.BatchNorm1d(hidden_dim),
                    nn.SiLU(),
                    nn.Dropout(p=dropout_p),

                    nn.Linear(hidden_dim, num_classes)
                )

            def forward(self, x):
                return self.layers(x)

        model = DeepMLP(input_dim, num_classes).to(device)
        
        # uncomment to verify param count
        # param_count = sum(p.numel() for p in model.parameters() if p.requires_grad)
        # print(f"Parameter count: {param_count}") # ~4,999,666

        EPOCHS = 700
        MAX_LR = 1.2e-3
        WEIGHT_DECAY = 0.05
        LABEL_SMOOTHING = 0.1
        MIXUP_ALPHA = 0.2

        criterion = nn.CrossEntropyLoss(label_smoothing=LABEL_SMOOTHING)
        optimizer = optim.AdamW(model.parameters(), lr=MAX_LR, weight_decay=WEIGHT_DECAY)
        scheduler = optim.lr_scheduler.OneCycleLR(
            optimizer,
            max_lr=MAX_LR,
            epochs=EPOCHS,
            steps_per_epoch=len(train_loader),
            pct_start=0.2,
            div_factor=25,
            final_div_factor=1e4
        )

        best_val_acc = 0.0
        best_model_state = None

        for epoch in range(EPOCHS):
            model.train()
            for inputs, targets in train_loader:
                inputs, targets = inputs.to(device), targets.to(device)

                lam = np.random.beta(MIXUP_ALPHA, MIXUP_ALPHA) if MIXUP_ALPHA > 0 else 1.0
                rand_index = torch.randperm(inputs.size(0)).to(device)
                
                mixed_inputs = lam * inputs + (1 - lam) * inputs[rand_index, :]
                target_a, target_b = targets, targets[rand_index]

                optimizer.zero_grad(set_to_none=True)
                outputs = model(mixed_inputs)
                
                loss = lam * criterion(outputs, target_a) + (1 - lam) * criterion(outputs, target_b)
                
                loss.backward()
                optimizer.step()
                scheduler.step()

            model.eval()
            val_correct = 0
            val_total = 0
            with torch.no_grad():
                for inputs, targets in val_loader:
                    inputs, targets = inputs.to(device), targets.to(device)
                    outputs = model(inputs)
                    _, predicted = torch.max(outputs.data, 1)
                    val_total += targets.size(0)
                    val_correct += (predicted == targets).sum().item()

            current_val_acc = val_correct / val_total

            if current_val_acc > best_val_acc:
                best_val_acc = current_val_acc
                best_model_state = copy.deepcopy(model.state_dict())

        if best_model_state is not None:
            model.load_state_dict(best_model_state)

        return model