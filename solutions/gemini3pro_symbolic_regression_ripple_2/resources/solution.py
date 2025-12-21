import numpy as np
from pysr import PySRRegressor
import os

class Solution:
    def __init__(self, **kwargs):
        pass

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        """
        Solves the Symbolic Regression problem using PySR.
        """
        # Configure PySRRegressor
        # niterations and populations tuned for 8 vCPUs and the specific problem type (Ripple)
        # Binary operators include ^ to allow for polynomial terms and sqrt (via ^0.5)
        # Unary operators focus on trigonometric functions essential for ripple patterns
        model = PySRRegressor(
            niterations=100,
            binary_operators=["+", "-", "*", "/", "^"],
            unary_operators=["sin", "cos", "exp", "log"],
            maxsize=40,
            populations=24,
            population_size=40,
            ncycles_per_iteration=500,
            model_selection="best",
            verbosity=0,
            progress=False,
            random_state=42,
            procs=8,
            multiprocessing=True,
            timeout_in_seconds=300,
            temp_equation_file=True,
            delete_tempfiles=True,
            # Penalize complexity slightly to prefer cleaner solutions
            parsimony=0.001,
        )

        try:
            # Fit the model
            model.fit(X, y, variable_names=["x1", "x2"])

            # Retrieve the best expression
            # .sympy() returns the sympy object for the selected equation
            best_expr = model.sympy()
            expression = str(best_expr)
            
            # Generate predictions
            predictions = model.predict(X)
            
            # Ensure predictions are in the correct format
            if isinstance(predictions, np.ndarray):
                predictions = predictions.tolist()
            
            return {
                "expression": expression,
                "predictions": predictions,
                "details": {}
            }

        except Exception as e:
            # Fallback strategy: Linear Regression
            # Used if PySR fails to initialize or runs out of time without a valid model
            x1, x2 = X[:, 0], X[:, 1]
            # Add bias term
            A = np.column_stack([x1, x2, np.ones_like(x1)])
            # Least squares fit
            coeffs, _, _, _ = np.linalg.lstsq(A, y, rcond=None)
            a, b, c = coeffs
            
            expression = f"{a}*x1 + {b}*x2 + {c}"
            predictions = (a * x1 + b * x2 + c).tolist()
            
            return {
                "expression": expression,
                "predictions": predictions,
                "details": {"error": str(e)}
            }
