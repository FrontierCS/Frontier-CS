import numpy as np
from pysr import PySRRegressor

class Solution:
    def __init__(self, **kwargs):
        pass

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        """
        Learns a symbolic expression for the given data using PySR.

        Args:
            X: Feature matrix of shape (n, 2)
            y: Target values of shape (n,)

        Returns:
            A dictionary with the learned expression and predictions.
        """
        model = PySRRegressor(
            # Environment settings tailored to 8 vCPUs
            procs=8,
            random_state=42,

            # Search parameters for a thorough search
            niterations=80,
            populations=32,
            population_size=50,
            
            # Complexity settings for the expression
            maxsize=40,
            
            # Allowed operators and functions
            binary_operators=["+", "-", "*", "/"],
            unary_operators=["sin", "cos", "exp", "log"],
            
            # Constraints to prevent pathological expressions
            nested_constraints={
                "sin": {"sin": 0, "cos": 0},
                "cos": {"sin": 0, "cos": 0},
                "exp": {"exp": 0},
                "log": {"log": 0},
            },

            # Suppress output during execution
            verbosity=0,
            progress=False,
        )

        # Fit the model to the data
        model.fit(X, y, variable_names=["x1", "x2"])

        # Check if PySR found any equations
        if not hasattr(model, 'equations_') or model.equations_.shape[0] == 0:
            # Fallback to a simple linear model if PySR fails
            x1, x2 = X[:, 0], X[:, 1]
            A = np.column_stack([x1, x2, np.ones_like(x1)])
            try:
                coeffs, _, _, _ = np.linalg.lstsq(A, y, rcond=None)
                a, b, c = coeffs
                expression = f"{a:.6f}*x1 + {b:.6f}*x2 + {c:.6f}"
                predictions = a * x1 + b * x2 + c
            except np.linalg.LinAlgError:
                # Further fallback to mean prediction if least squares fails
                mean_y = np.mean(y)
                expression = f"{mean_y:.6f}"
                predictions = np.full_like(y, mean_y)
        else:
            # Extract the best expression from the fitted model
            best_expr_sympy = model.sympy()
            expression = str(best_expr_sympy)
            
            # Generate predictions using the best model
            predictions = model.predict(X)

        return {
            "expression": expression,
            "predictions": predictions.tolist(),
            "details": {}
        }