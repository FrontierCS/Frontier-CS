import numpy as np
import pandas as pd
from pysr import PySRRegressor
import sympy
import warnings

# Suppress warnings to maintain clean output
warnings.filterwarnings("ignore")

class Solution:
    def __init__(self, **kwargs):
        pass

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        """
        Solves the symbolic regression problem using PySR.
        
        Args:
            X: Feature matrix of shape (n, 2)
            y: Target values of shape (n,)

        Returns:
            dict containing "expression", "predictions", and "details"
        """
        # Subsample data if dataset is large to ensure efficient runtime
        # 2000 points are typically sufficient for symbolic regression to find the structure
        n_samples = X.shape[0]
        if n_samples > 2000:
            rng = np.random.RandomState(42)
            indices = rng.choice(n_samples, 2000, replace=False)
            X_train = X[indices]
            y_train = y[indices]
        else:
            X_train = X
            y_train = y

        # Configure PySRRegressor
        # Tuned for 8 vCPUs and expected trigonometric patterns
        model = PySRRegressor(
            niterations=60,
            binary_operators=["+", "-", "*", "/", "^"],
            unary_operators=["sin", "cos", "exp", "log"],
            populations=16,           # Parallel populations (2x vCPUs)
            population_size=40,
            maxsize=30,               # Limit complexity
            loss="mse",
            denoise=False,
            procs=8,                  # Use all 8 vCPUs
            multiprocessing=True,
            verbosity=0,
            progress=False,
            random_state=42,
            timeout_in_seconds=300,   # 5 minute timeout safety
            temp_equation_file=True,
            delete_temp_files=True
        )

        try:
            # Fit the model to the training data
            # variable_names ensures the output expression uses x1, x2
            model.fit(X_train, y_train, variable_names=["x1", "x2"])
            
            # Retrieve the best expression found (balanced by score and complexity)
            best_expr = model.sympy()
            expression = str(best_expr)
            
            # Generate predictions for the full dataset
            predictions = model.predict(X)
            
            # Validate predictions
            if np.any(np.isnan(predictions)) or np.any(np.isinf(predictions)):
                raise ValueError("Model predictions contain NaN or Inf")

        except Exception:
            # Fallback strategy: Linear Regression
            # Used if PySR fails, times out, or produces unstable predictions
            x1 = X[:, 0]
            x2 = X[:, 1]
            # Design matrix: [x1, x2, 1]
            A = np.column_stack([x1, x2, np.ones_like(x1)])
            
            # Solve least squares
            coeffs, _, _, _ = np.linalg.lstsq(A, y, rcond=None)
            a, b, c = coeffs
            
            # Construct linear expression string
            expression = f"{a} * x1 + {b} * x2 + {c}"
            predictions = a * x1 + b * x2 + c

        return {
            "expression": expression,
            "predictions": predictions.tolist(),
            "details": {}
        }
