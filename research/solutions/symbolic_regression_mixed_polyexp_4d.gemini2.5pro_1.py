import numpy as np
from pysr import PySRRegressor
import sympy

class Solution:
    def __init__(self, **kwargs):
        pass

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        """
        Learns a symbolic expression for the given data using PySR.

        Args:
            X: Feature matrix of shape (n, 4).
            y: Target values of shape (n,).

        Returns:
            A dictionary containing the learned expression and predictions.
        """
        # Configure PySR for a thorough search suitable for a 4D problem
        # within a CPU-only environment.
        model = PySRRegressor(
            niterations=80,
            populations=24,
            population_size=40,
            maxsize=35,
            binary_operators=["+", "-", "*", "/"],
            unary_operators=["exp", "cos", "sin", "log"],
            nested_constraints={
                "sin": {"sin": 0, "cos": 0},
                "cos": {"sin": 0, "cos": 0},
                "exp": {"exp": 0},
                "log": {"log": 0},
            },
            procs=8,
            temp_equation_file=True,
            random_state=42,
            verbosity=0,
            progress=False,
        )

        # Fit the model to the provided data, specifying variable names
        model.fit(X, y, variable_names=["x1", "x2", "x3", "x4"])

        # Handle the case where PySR fails to find any equations
        if len(model.equations_) == 0:
            # Fallback to a constant mean value
            mean_y = np.mean(y)
            expression = str(mean_y)
            predictions = np.full_like(y, mean_y)
            complexity = 0
        else:
            # Extract the best expression and its properties
            best_sympy_expr = model.sympy()
            expression = str(best_sympy_expr)
            predictions = model.predict(X)
            complexity = int(model.equations_.iloc[-1]["complexity"])

        return {
            "expression": expression,
            "predictions": predictions.tolist(),
            "details": {
                "complexity": complexity
            }
        }
