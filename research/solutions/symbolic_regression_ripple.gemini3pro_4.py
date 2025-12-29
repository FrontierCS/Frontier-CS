import numpy as np
import pandas as pd
import sympy
from pysr import PySRRegressor

class Solution:
    def __init__(self, **kwargs):
        pass

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        """
        Solves the symbolic regression problem for the Ripple dataset using PySR.
        """
        # Configure PySRRegressor
        # Using 8 processes matches the 8 vCPUs environment.
        # Trigonometric functions are essential for the ripple dataset.
        model = PySRRegressor(
            niterations=50,
            binary_operators=["+", "-", "*", "/"],
            unary_operators=["sin", "cos", "exp", "log"],
            populations=24,         # 3 * 8 cores for parallel diversity
            population_size=40,
            ncycles_per_iteration=500,
            maxsize=45,             # Allow enough complexity for modulation + oscillation
            procs=8,
            multithreading=False,   # Use multiprocessing
            verbosity=0,
            progress=False,
            random_state=42,
            temp_equation_file=None,
            delete_tempfiles=True,
            constraints={
                'sin': 5, 'cos': 5, 'exp': 5, 'log': 5
            }
        )

        # Fit the model
        # variable_names are set to match the required output format (x1, x2)
        model.fit(X, y, variable_names=["x1", "x2"])

        # Extract the best expression
        try:
            # model.sympy() returns the SymPy representation of the best model
            # selected by PySR (balancing loss and complexity)
            best_expr = model.sympy()
            expression = str(best_expr)
        except Exception:
            # Fallback in case of unexpected failure
            expression = "0.0"

        # Generate predictions using the fitted model
        try:
            predictions = model.predict(X)
        except Exception:
            predictions = np.zeros(len(y))

        return {
            "expression": expression,
            "predictions": predictions.tolist(),
            "details": {}
        }