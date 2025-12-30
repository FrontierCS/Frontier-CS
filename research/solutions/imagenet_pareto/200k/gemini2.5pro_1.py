import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import TensorDataset, DataLoader

class Solution:
    """
    Solution for the ImageNet Pareto Optimization problem.
    """
    def solve(self, train_loader: DataLoader, val_loader: DataLoader, metadata: dict = None) -> torch.nn.Module:
        """
        Trains a neural network model to maximize accuracy on a synthetic ImageNet-like dataset,
        while adhering to a strict parameter limit of 200,000.

        The approach uses a deep, residual MLP architecture, which allows for greater depth
        and representational capacity compared to a simple MLP, while managing the parameter count.
        Key components of the solution:
        1.  **Architecture**: A ResNet-inspired MLP with two residual blocks. The hidden dimension
            is carefully chosen (167) to maximize model capacity just under the 200K parameter limit.
            This deeper, narrower architecture often generalizes better than shallower, wider ones.
        2.  **Regularization**: To combat overfitting on the small dataset, multiple regularization
            techniques are employed:
            - **AdamW Optimizer**: An extension of Adam that decouples weight decay from the optimization
              step, often leading to better generalization.
            - **Dropout**: Applied within the residual blocks to prevent co-adaptation of neurons.
            - **Label Smoothing**: A technique that prevents the model from becoming too confident
              in its predictions, improving calibration and generalization.
        3.  **Training Strategy**:
            - **Cosine Annealing Scheduler**: The learning rate is cyclically annealed, which helps
              the model converge to wider, more robust minima.
            - **Combined Dataset**: The model is trained on the full combined training and validation
              datasets to leverage all available data before final evaluation.
            - **Epochs**: A relatively high number of epochs (450) is used, as the model and dataset
              are small enough to train quickly on a CPU, allowing the learning rate scheduler to
              complete its full cycle and the model to converge properly.

        The combination of a parameter-efficient deep architecture and robust training/regularization
        techniques aims to achieve the highest possible accuracy within the given constraints.
        """

        # --- Model Definition (scoped within the solve method) ---
        class ResBlock(nn.Module):
            """A residual block for an MLP."""
            def __init__(self, dim, dropout_p):
                super().__init__()
                self.block = nn.Sequential(
                    nn.Linear(dim, dim),
                    nn.BatchNorm1d(dim),
                    nn.GELU(),
                    nn.Dropout(dropout_p),
                    nn.Linear(dim, dim),
                    nn.BatchNorm1d(dim),
                )
                self.final_activation = nn.GELU()
                self.dropout = nn.Dropout(dropout_p)

            def forward(self, x: torch.Tensor) -> torch.Tensor:
                residual = self.block(x)
                x = x + residual
                x = self.final_activation(x)
                x = self.dropout(x)
                return x

        class DeepResNetMLP(nn.Module):
            """A deep residual MLP model."""
            def __init__(self, input_dim, hidden_dim, num_classes, dropout_p):
                super().__init__()
                self.input_layer = nn.Sequential(
                    nn.Linear(input_dim, hidden_dim),
                    nn.BatchNorm1d(hidden_dim),
                    nn.GELU(),
                )
                self.res_blocks = nn.Sequential(
                    ResBlock(hidden_dim, dropout_p),
                    ResBlock(hidden_dim, dropout_p),
                )
                self.output_layer = nn.Linear(hidden_dim, num_classes)

            def forward(self, x: torch.Tensor) -> torch.Tensor:
                x = self.input_layer(x)
                x = self.res_blocks(x)
                x = self.output_layer(x)
                return x

        # --- Hyperparameters ---
        HIDDEN_DIM = 167
        DROPOUT_P = 0.2
        EPOCHS = 450
        LEARNING_RATE = 2e-3
        WEIGHT_DECAY = 1.5e-2
        LABEL_SMOOTHING = 0.1
        
        # --- Setup ---
        device = torch.device(metadata.get("device", "cpu"))
        num_classes = metadata["num_classes"]
        input_dim = metadata["input_dim"]
        
        # For reproducibility
        torch.manual_seed(42)

        # --- Data Preparation ---
        # Combine train and validation data for final training
        train_inputs, train_targets = [], []
        for inputs, targets in train_loader:
            train_inputs.append(inputs)
            train_targets.append(targets)
        for inputs, targets in val_loader:
            train_inputs.append(inputs)
            train_targets.append(targets)

        full_train_inputs = torch.cat(train_inputs, dim=0)
        full_train_targets = torch.cat(train_targets, dim=0)
        full_train_dataset = TensorDataset(full_train_inputs, full_train_targets)
        
        batch_size = train_loader.batch_size if hasattr(train_loader, 'batch_size') and train_loader.batch_size is not None else 64
        
        full_train_loader = DataLoader(
            full_train_dataset,
            batch_size=batch_size,
            shuffle=True,
            num_workers=0, # Optimal for CPU-only environment
            pin_memory=False
        )

        # --- Model Initialization ---
        model = DeepResNetMLP(
            input_dim=input_dim,
            hidden_dim=HIDDEN_DIM,
            num_classes=num_classes,
            dropout_p=DROPOUT_P,
        ).to(device)

        # --- Training ---
        criterion = nn.CrossEntropyLoss(label_smoothing=LABEL_SMOOTHING)
        optimizer = optim.AdamW(
            model.parameters(),
            lr=LEARNING_RATE,
            weight_decay=WEIGHT_DECAY
        )
        scheduler = optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=EPOCHS)

        model.train()
        for _ in range(EPOCHS):
            for inputs, targets in full_train_loader:
                inputs, targets = inputs.to(device), targets.to(device)
                
                optimizer.zero_grad()
                outputs = model(inputs)
                loss = criterion(outputs, targets)
                loss.backward()
                optimizer.step()
            
            scheduler.step()
        
        model.eval()
        return model