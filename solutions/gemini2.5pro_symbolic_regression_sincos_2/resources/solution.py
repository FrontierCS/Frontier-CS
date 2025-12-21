import numpy as np
from pysr import PySRRegressor
import sympy

class Solution:
    def __init__(self, **kwargs):
        """
        Initialize the Solution class.
        You can use this to set up any parameters or models.
        """
        pass

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        """
        Fit a symbolic expression to the data.

        Args:
            X: Feature matrix of shape (n, 2)
            y: Target values of shape (n,)

        Returns:
            dict with keys:
              - "expression": str, a Python-evaluable expression using x1, x2
              - "predictions": list/array of length n (optional)
              - "details": dict with optional "complexity" int
        """
        # Given the dataset name "SinCos", we expect trigonometric functions.
        # We configure PySR to use the allowed operators and functions,
        # leveraging the 8 available vCPUs for an efficient search.
        model = PySRRegressor(
            niterations=100,
            populations=24,
            population_size=50,
            binary_operators=["+", "-", "*", "/"],
            unary_operators=["sin", "cos", "exp", "log"],
            maxsize=25,
            model_selection="best",
            parsimony=0.0025,
            procs=8,
            random_state=42,
            verbosity=0,
            progress=False,
            # Use a slightly more stable optimizer
            optimizer_algorithm="NelderMead",
            # Ensure constants are optimized
            should_optimize_constants=True,
        )

        model.fit(X, y, variable_names=["x1", "x2"])

        if not hasattr(model, 'equations') or model.equations.empty:
            # Fallback in case no expression is found
            expression = "0.0"
            predictions = np.zeros_like(y)
        else:
            # Get the best expression found by PySR
            sympy_expr = model.sympy()
            expression = str(sympy_expr)
            predictions = model.predict(X)

        return {
            "expression": expression,
            "predictions": predictions.tolist(),
            "details": {}
        }
