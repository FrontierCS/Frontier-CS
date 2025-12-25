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
        Finds a closed-form expression f(x1, x2) ~ y.
        """
        
        # Configure PySRRegressor
        # Optimized for 8 vCPUs with a time limit to ensure termination.
        # - niterations: High limit, controlled effectively by timeout
        # - binary/unary_operators: As allowed by problem spec
        # - populations: 3x core count for diversity
        # - maxsize: Sufficient for the complexity of peaks-like functions
        model = PySRRegressor(
            niterations=1000,
            timeout_in_seconds=180,  # 3 minutes max
            binary_operators=["+", "-", "*", "/", "^"],
            unary_operators=["exp", "sin", "cos", "log"],
            populations=24,
            population_size=40,
            maxsize=50,
            verbosity=0,
            progress=False,
            random_state=42,
            model_selection="best",
            temp_equation_file=True,
            delete_tempfiles=True,
            loss="mse"
        )

        try:
            # Fit the model
            # variable_names must match the required output format
            model.fit(X, y, variable_names=["x1", "x2"])

            # Retrieve the best expression found
            # PySR's "best" model selection balances MSE and complexity
            best_expr = model.sympy()
            expression = str(best_expr)

            # Generate predictions using the fitted model
            predictions = model.predict(X)

            return {
                "expression": expression,
                "predictions": predictions.tolist(),
                "details": {
                    "equations": str(model.equations_.to_dict()) if hasattr(model, "equations_") else ""
                }
            }

        except Exception as e:
            # Fallback to linear regression in case of failure
            return self._fallback(X, y)

    def _fallback(self, X: np.ndarray, y: np.ndarray) -> dict:
        """
        Simple linear regression fallback: y = a*x1 + b*x2 + c
        """
        x1 = X[:, 0]
        x2 = X[:, 1]
        
        # Prepare design matrix
        A = np.column_stack([x1, x2, np.ones_like(x1)])
        
        try:
            # Least squares fit
            coeffs, _, _, _ = np.linalg.lstsq(A, y, rcond=None)
            a, b, c = coeffs
        except Exception:
            a, b, c = 0.0, 0.0, 0.0

        expression = f"({a}) * x1 + ({b}) * x2 + ({c})"
        predictions = a * x1 + b * x2 + c
        
        return {
            "expression": expression,
            "predictions": predictions.tolist(),
            "details": {"fallback": True}
        }
