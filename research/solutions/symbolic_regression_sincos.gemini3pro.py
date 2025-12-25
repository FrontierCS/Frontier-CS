import numpy as np
import pandas as pd
import sympy
from pysr import PySRRegressor

class Solution:
    def __init__(self, **kwargs):
        pass

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        """
        Solves the symbolic regression problem using PySRRegressor.
        
        Args:
            X: Feature matrix of shape (n, 2)
            y: Target values of shape (n,)
            
        Returns:
            dict containing "expression", "predictions", and "details"
        """
        # Configure PySRRegressor
        # Optimized for 8 vCPUs (populations multiple of cores)
        # Includes trigonometric functions matching the "SinCos" dataset hint
        model = PySRRegressor(
            niterations=100,
            binary_operators=["+", "-", "*", "/"],
            unary_operators=["sin", "cos", "exp", "log"],
            populations=24,
            population_size=40,
            maxsize=30,
            verbosity=0,
            progress=False,
            random_state=42,
            model_selection="best",
            deterministic=True
        )

        try:
            # Fit the model to the data
            model.fit(X, y, variable_names=["x1", "x2"])

            # Extract the best expression as a sympy object and convert to string
            best_expr = model.sympy()
            expression = str(best_expr)

            # Generate predictions
            predictions = model.predict(X)
            
            # Ensure predictions format is list
            if hasattr(predictions, "tolist"):
                predictions = predictions.tolist()

        except Exception:
            # Fallback strategy: Linear Regression
            # Used if PySR encounters runtime issues
            x1 = X[:, 0]
            x2 = X[:, 1]
            A = np.column_stack([x1, x2, np.ones_like(x1)])
            coeffs, _, _, _ = np.linalg.lstsq(A, y, rcond=None)
            a, b, c = coeffs
            
            expression = f"{a}*x1 + {b}*x2 + {c}"
            predictions = (a * x1 + b * x2 + c).tolist()

        return {
            "expression": expression,
            "predictions": predictions,
            "details": {}
        }
