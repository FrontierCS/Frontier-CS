import numpy as np
import pandas as pd
from pysr import PySRRegressor
import sympy
import warnings

# Suppress warnings
warnings.filterwarnings("ignore")

class Solution:
    def __init__(self, **kwargs):
        pass

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        """
        Solves the symbolic regression problem using PySR.
        Falls back to linear regression on failure.
        """
        try:
            # Configure PySRRegressor with operators suitable for Ripple functions
            # (polynomial amplitude modulation + trigonometric oscillations)
            model = PySRRegressor(
                niterations=40,
                binary_operators=["+", "-", "*", "/", "^"],
                unary_operators=["sin", "cos", "exp", "log"],
                populations=16,        # Parallel populations (2 per core approx)
                population_size=33,
                maxsize=35,            # Allow enough complexity for concentric waves
                procs=8,               # Use 8 vCPUs
                model_selection="best",
                verbosity=0,
                progress=False,
                random_state=42,
                deterministic=True,
                timeout_in_seconds=300 # Safety timeout
            )

            # Fit the model
            model.fit(X, y, variable_names=["x1", "x2"])

            # Retrieve the best expression found
            # PySR returns a sympy object which converts to python-valid string (using **)
            best_expr = model.sympy()
            expression = str(best_expr)

            # Generate predictions
            predictions = model.predict(X)

        except Exception as e:
            # Fallback to simple Linear Regression if PySR fails
            # This ensures a valid return format even in case of environment/search errors
            x1, x2 = X[:, 0], X[:, 1]
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
