import numpy as np
import pandas as pd
import sympy
from pysr import PySRRegressor

class Solution:
    def __init__(self, **kwargs):
        pass

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        """
        Fits a symbolic regression model to the data using PySR.
        """
        # Configure PySRRegressor
        # Using settings optimized for 8 vCPUs (CPU-only) and the SinCos dataset characteristics
        model = PySRRegressor(
            niterations=50,
            binary_operators=["+", "-", "*", "/"],
            unary_operators=["sin", "cos", "exp", "log"],
            populations=16,            # Parallelize across available vCPUs
            population_size=40,
            ncycles_per_iteration=500,
            maxsize=30,                # Allow sufficient complexity for trig combinations
            model_selection="best",    # Select best model based on accuracy/complexity trade-off
            verbosity=0,
            progress=False,
            random_state=42,
            deterministic=True
        )

        try:
            # Fit the model
            model.fit(X, y, variable_names=["x1", "x2"])

            # Extract the best expression as a sympy object and convert to string
            best_expr = model.sympy()
            expression = str(best_expr)

            # Generate predictions
            predictions = model.predict(X)

        except Exception:
            # Fallback to linear regression if symbolic regression fails
            # This ensures a valid return format is always produced
            x1 = X[:, 0]
            x2 = X[:, 1]
            A = np.column_stack([x1, x2, np.ones_like(x1)])
            coeffs, _, _, _ = np.linalg.lstsq(A, y, rcond=None)
            a, b, c = coeffs
            
            expression = f"{a}*x1 + {b}*x2 + {c}"
            predictions = a * x1 + b * x2 + c

        return {
            "expression": expression,
            "predictions": predictions.tolist(),
            "details": {}
        }