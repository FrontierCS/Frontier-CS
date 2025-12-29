import numpy as np
from pysr import PySRRegressor
import sympy

class Solution:
    def __init__(self, **kwargs):
        pass

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        """
        Fits a symbolic regression model using PySR to predict y from X.
        """
        # Configure PySRRegressor
        # Using settings optimized for the provided CPU-only environment (8 vCPUs)
        # We limit iterations and populations to ensure execution within reasonable time
        # while maintaining enough search depth for trigonometric patterns.
        model = PySRRegressor(
            niterations=60,
            binary_operators=["+", "-", "*", "/"],
            unary_operators=["sin", "cos", "exp", "log"],
            populations=16,  # Approx 2 populations per vCPU
            population_size=40,
            maxsize=30,      # Allow for moderate complexity
            verbosity=0,     # Suppress output
            progress=False,
            random_state=42,
            model_selection="best", # Select best model based on score/complexity trade-off
        )

        # Fit the model
        # variable_names ensures the output expression uses "x1" and "x2"
        model.fit(X, y, variable_names=["x1", "x2"])

        # Extract the best expression found
        # model.sympy() returns a sympy object, str() converts it to a Python expression string
        try:
            best_expr = model.sympy()
            expression = str(best_expr)
        except Exception:
            # Fallback in case of unexpected failure
            expression = "0"

        # Generate predictions
        try:
            predictions = model.predict(X)
        except Exception:
            predictions = np.zeros(len(y))

        return {
            "expression": expression,
            "predictions": predictions.tolist(),
            "details": {}
        }