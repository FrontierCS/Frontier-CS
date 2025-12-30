import torch
import torch.nn as nn
import torch.optim
import copy

# A robust MLP architecture designed to maximize capacity under the 1M parameter limit.
# It uses common modern techniques like Batch Normalization, GELU activation, and Dropout
# for better training stability and regularization on the small dataset.
class _CustomNet(nn.Module):
    def __init__(self, input_dim: int, num_classes: int):
        super().__init__()
        
        # Architecture: 384 -> 900 -> 512 -> 256 -> 128
        # This structure is chosen to be close to, but under, 1,000,000 parameters.
        # Parameter Calculation:
        # Linear 1 (384->900): 384*900 + 900 = 346,500
        # BatchNorm1d 1 (900): 2*900 = 1,800
        # Linear 2 (900->512): 900*512 + 512 = 461,312
        # BatchNorm1d 2 (512): 2*512 = 1,024
        # Linear 3 (512->256): 512*256 + 256 = 131,328
        # BatchNorm1d 3 (256): 2*256 = 512
        # Linear 4 (256->128): 256*128 + 128 = 32,896
        # Total Parameters = 975,372 < 1,000,000
        
        self.layers = nn.Sequential(
            nn.Linear(input_dim, 900),
            nn.BatchNorm1d(900),
            nn.GELU(),
            nn.Dropout(0.4),

            nn.Linear(900, 512),
            nn.BatchNorm1d(512),
            nn.GELU(),
            nn.Dropout(0.3),

            nn.Linear(512, 256),
            nn.BatchNorm1d(256),
            nn.GELU(),
            nn.Dropout(0.2),
            
            nn.Linear(256, num_classes)
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.layers(x)


class Solution:
    def solve(self, train_loader, val_loader, metadata: dict = None) -> torch.nn.Module:
        """
        Train a model and return it.
        
        This solution trains a custom MLP model (_CustomNet) designed to maximize accuracy
        on the given synthetic dataset while adhering to a strict 1,000,000 parameter limit.
        
        The training strategy includes:
        - AdamW optimizer for better weight decay handling.
        - CosineAnnealingLR scheduler to adjust the learning rate over epochs.
        - Early stopping based on validation accuracy to prevent overfitting and
          return the best performing model.
        """
        device = torch.device(metadata.get("device", "cpu"))
        input_dim = metadata["input_dim"]
        num_classes = metadata["num_classes"]

        model = _CustomNet(input_dim, num_classes).to(device)

        # Tuned hyperparameters for robust training
        EPOCHS = 250
        LEARNING_RATE = 3e-4
        WEIGHT_DECAY = 1e-4
        PATIENCE = 40

        optimizer = torch.optim.AdamW(model.parameters(), lr=LEARNING_RATE, weight_decay=WEIGHT_DECAY)
        criterion = nn.CrossEntropyLoss()
        scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=EPOCHS, eta_min=1e-6)

        best_val_accuracy = 0.0
        epochs_no_improve = 0
        best_model_state = None

        for epoch in range(EPOCHS):
            # --- Training Phase ---
            model.train()
            for inputs, targets in train_loader:
                inputs, targets = inputs.to(device), targets.to(device)

                optimizer.zero_grad()
                outputs = model(inputs)
                loss = criterion(outputs, targets)
                loss.backward()
                optimizer.step()

            # --- Validation Phase ---
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

            current_val_accuracy = val_correct / val_total

            # --- Early Stopping & Checkpointing ---
            if current_val_accuracy > best_val_accuracy:
                best_val_accuracy = current_val_accuracy
                epochs_no_improve = 0
                best_model_state = copy.deepcopy(model.state_dict())
            else:
                epochs_no_improve += 1

            if epochs_no_improve >= PATIENCE:
                break
            
            scheduler.step()

        # Load the best performing model state before returning
        if best_model_state:
            model.load_state_dict(best_model_state)

        return model