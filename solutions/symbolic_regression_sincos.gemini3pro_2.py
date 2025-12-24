import numpy as np
import pandas as pd
import sympy
from pysr import PySRRegressor

class Solution:
    def __init__(self, **kwargs):
        pass

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        """
        Solves the symbolic regression problem using PySR.
        """
        # Configure PySRRegressor
        # Optimized for 8 vCPUs (populations=8, procs=8)
        # Includes all allowed operators
        model = PySRRegressor(
            niterations=50,
            binary_operators=["+", "-", "*", "/", "pow"],
            unary_operators=["sin", "cos", "exp", "log"],
            populations=8,
            population_size=40,
            maxsize=30,
            loss="L2DistLoss",
            model_selection="best",
            verbosity=0,
            progress=False,
            random_state=42,
            procs=8,
            multithreading=False,
            deterministic=True
        )

        # Fit the model
        # variable_names ensures the output expression uses x1, x2
        model.fit(X, y, variable_names=["x1", "x2"])

        try:
            # Retrieve the best expression found as a SymPy object
            best_expr = model.sympy()
            
            # Convert SymPy object to a valid Python expression string
            expression = str(best_expr)
            
            # Generate predictions using the fitted model
            predictions = model.predict(X)
            
        except Exception:
            # Fallback to Linear Regression if symbolic regression fails
            # This ensures the method always returns a valid dictionary
            x1, x2 = X[:, 0], X[:, 1]
            A = np.column_stack([x1, x2, np.ones(len(x1))])
            coeffs, _, _, _ = np.linalg.lstsq(A, y, rcond=None)
            
            a, b, c = coeffs
            expression = f"{a}*x1 + {b}*x2 + {c}"
            predictions = A @ coeffs

        return {
            "expression": expression,
            "predictions": predictions.tolist(),
            "details": {}
        }
