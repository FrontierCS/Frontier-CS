import torch
import torch.nn as nn
from torch.utils.data import DataLoader, ConcatDataset

class Solution:
    """
    Implementation of the solution for the ImageNet Pareto Optimization problem.
    """
    def solve(self, train_loader, val_loader, metadata: dict = None) -> torch.nn.Module:
        """
        Trains a model on the provided data loaders to maximize accuracy under a 5M parameter budget.

        Args:
            train_loader: DataLoader for the training set.
            val_loader: DataLoader for the validation set.
            metadata: A dictionary containing problem-specific details like input dimensions,
                      number of classes, device, and parameter limits.

        Returns:
            A trained torch.nn.Module ready for evaluation.
        """
        device = torch.device(metadata.get("device", "cpu"))
        input_dim = metadata["input_dim"]
        num_classes = metadata["num_classes"]

        # 1. Model Definition
        # A deep, pyramidal MLP architecture is chosen to maximize representational capacity
        # within the 5M parameter limit. This structure has been carefully designed to
        # be just under the budget including all parameters (weights, biases, batchnorm).
        class ImageNetParetoModel(nn.Module):
            def __init__(self, input_dim: int, num_classes: int):
                super().__init__()
                # Pyramidal structure: 384 -> 2464 -> 1232 -> 616 -> 308 -> 128
                # This architecture has ~4,983,876 parameters.
                h1, h2, h3, h4 = 2464, 1232, 616, 308
                dropout_rate = 0.4

                self.layers = nn.Sequential(
                    # Block 1
                    nn.Linear(input_dim, h1),
                    nn.BatchNorm1d(h1),
                    nn.GELU(),
                    nn.Dropout(p=dropout_rate),
                    # Block 2
                    nn.Linear(h1, h2),
                    nn.BatchNorm1d(h2),
                    nn.GELU(),
                    nn.Dropout(p=dropout_rate),
                    # Block 3
                    nn.Linear(h2, h3),
                    nn.BatchNorm1d(h3),
                    nn.GELU(),
                    nn.Dropout(p=dropout_rate),
                    # Block 4
                    nn.Linear(h3, h4),
                    nn.BatchNorm1d(h4),
                    nn.GELU(),
                    nn.Dropout(p=dropout_rate),
                    # Output Layer
                    nn.Linear(h4, num_classes)
                )

            def forward(self, x: torch.Tensor) -> torch.Tensor:
                return self.layers(x)

        model = ImageNetParetoModel(input_dim, num_classes).to(device)

        # 2. Data Preparation
        # Combine train and validation datasets to use all available labeled data for training.
        # This is a common strategy when the final evaluation is on a separate, hidden test set.
        combined_dataset = ConcatDataset([train_loader.dataset, val_loader.dataset])
        batch_size = train_loader.batch_size if train_loader.batch_size is not None else 64
        
        # num_workers=0 is safest for reproducibility and avoids multiprocessing overhead.
        combined_loader = DataLoader(
            combined_dataset,
            batch_size=batch_size,
            shuffle=True,
            num_workers=0,
            pin_memory=False  # pin_memory is for CUDA
        )

        # 3. Training Hyperparameters and Setup
        # These hyperparameters are chosen to provide strong regularization and fast convergence.
        NUM_EPOCHS = 500
        MAX_LR = 1e-3         # Optimal max learning rate for OneCycleLR
        WEIGHT_DECAY = 0.01   # Weight decay for AdamW optimizer
        LABEL_SMOOTHING = 0.1 # Regularization technique to prevent overconfidence

        criterion = nn.CrossEntropyLoss(label_smoothing=LABEL_SMOOTHING)
        optimizer = torch.optim.AdamW(model.parameters(), lr=MAX_LR, weight_decay=WEIGHT_DECAY)
        
        # OneCycleLR is a powerful scheduler that varies learning rate, often leading to
        # faster convergence and better performance.
        scheduler = torch.optim.lr_scheduler.OneCycleLR(
            optimizer,
            max_lr=MAX_LR,
            epochs=NUM_EPOCHS,
            steps_per_epoch=len(combined_loader)
        )

        # 4. Training Loop
        model.train()
        for _ in range(NUM_EPOCHS):
            for inputs, targets in combined_loader:
                inputs, targets = inputs.to(device), targets.to(device)

                # Forward pass
                outputs = model(inputs)
                loss = criterion(outputs, targets)

                # Backward pass and optimization
                optimizer.zero_grad(set_to_none=True)
                loss.backward()
                optimizer.step()
                scheduler.step()

        # 5. Finalize and Return Model
        # Set the model to evaluation mode to disable layers like Dropout for inference.
        model.eval()
        return model
