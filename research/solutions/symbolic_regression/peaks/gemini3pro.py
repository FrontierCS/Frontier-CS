import numpy as np
import pandas as pd
import sympy
from pysr import PySRRegressor

class Solution:
    def __init__(self, **kwargs):
        pass

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        """
        Args:
            X: Feature matrix of shape (n, 2)
            y: Target values of shape (n,)

        Returns:
            dict with keys:
              - "expression": str, a Python-evaluable expression using x1, x2
              - "predictions": list/array of length n
              - "details": dict with optional details
        """
        try:
            # Configure PySRRegressor
            # Increased iterations and complexity for the Peaks dataset
            # Using multiprocessing (procs=8) to leverage available vCPUs
            model = PySRRegressor(
                niterations=80,
                binary_operators=["+", "-", "*", "/"],
                unary_operators=["sin", "cos", "exp", "log"],
                populations=24,
                population_size=40,
                maxsize=50,
                ncycles_per_iteration=500,
                verbosity=0,
                progress=False,
                random_state=42,
                model_selection="best",
                procs=8,
                multithreading=False,
                loss="L2DistLoss()",
                temp_equation_file=True
            )

            # Fit the symbolic regression model
            # Enforce variable names x1, x2
            model.fit(X, y, variable_names=["x1", "x2"])

            # Retrieve the best expression as a sympy object
            best_expr = model.sympy()
            
            # Convert sympy expression to a Python-compatible string
            expression = str(best_expr)

            # Generate predictions on the input data
            predictions = model.predict(X)
            
            # Ensure predictions are in list format
            if isinstance(predictions, np.ndarray):
                predictions = predictions.tolist()

        except Exception:
            # Fallback mechanism: Linear Regression
            # In case PySR fails due to environment constraints or convergence issues
            x1 = X[:, 0]
            x2 = X[:, 1]
            
            # Fit linear model A*w = y
            A = np.column_stack([x1, x2, np.ones_like(x1)])
            coeffs, _, _, _ = np.linalg.lstsq(A, y, rcond=None)
            a, b, c = coeffs
            
            # Create linear expression string
            expression = f"({a})*x1 + ({b})*x2 + ({c})"
            predictions = (a * x1 + b * x2 + c).tolist()

        return {
            "expression": expression,
            "predictions": predictions,
            "details": {}
        }