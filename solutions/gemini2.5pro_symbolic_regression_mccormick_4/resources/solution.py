import numpy as np
from pysr import PySRRegressor
import sympy as sp

class Solution:
    def __init__(self, **kwargs):
        """
        Initialize the Solution class.
        """
        pass

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        """
        Finds a symbolic expression for the given data using PySR.
        
        Args:
            X: Feature matrix of shape (n, 2) with columns 'x1', 'x2'.
            y: Target values of shape (n,).
            
        Returns:
            A dictionary containing the symbolic expression, predictions, and details.
        """
        # Configure PySRRegressor with parameters tuned for the McCormick function
        # and the specified CPU-only evaluation environment.
        model = PySRRegressor(
            niterations=80,
            populations=32,
            population_size=40,
            binary_operators=["+", "-", "*", "**"],
            unary_operators=["sin", "cos"],
            nested_constraints={"sin": 1, "cos": 1},
            maxsize=25,
            model_selection="best",
            procs=8,  # Utilize all 8 vCPUs
            random_state=42,
            verbosity=0,
            progress=False,
            timeout_in_seconds=300,  # 5-minute timeout for safety
        )

        try:
            model.fit(X, y, variable_names=["x1", "x2"])
        except Exception:
            # If PySR fails (e.g., timeout), the fallback will be triggered.
            pass

        # If PySR fails to find any equations, provide a robust linear fallback.
        if not hasattr(model, 'equations') or model.equations.empty:
            x1, x2 = X[:, 0], X[:, 1]
            A = np.c_[x1, x2, np.ones_like(x1)]
            try:
                coeffs, _, _, _ = np.linalg.lstsq(A, y, rcond=None)
                a, b, c = coeffs
                expression = f"{a:.8f}*x1 + {b:.8f}*x2 + {c:.8f}"
                predictions = a * x1 + b * x2 + c
            except np.linalg.LinAlgError:
                # If least squares fails, fallback to the mean.
                mean_y = np.mean(y)
                expression = f"{mean_y:.8f}"
                predictions = np.full_like(y, mean_y)
            
            return {
                "expression": expression,
                "predictions": predictions.tolist(),
                "details": {"pysr_failed": True}
            }

        # Retrieve the best symbolic expression found by PySR.
        best_eq = model.get_best()
        sympy_expr = best_eq["sympy_format"]
        expression_str = str(sympy_expr)
        complexity = int(best_eq["complexity"])
        
        # Generate predictions from the best model.
        try:
            predictions = model.predict(X)
        except (ValueError, RuntimeError):
            # Fallback for prediction if model.predict fails for some reason.
            x1_sp, x2_sp = sp.symbols('x1 x2')
            # Use numpy backend for speed
            f = sp.lambdify((x1_sp, x2_sp), sympy_expr, 'numpy')
            predictions = f(X[:, 0], X[:, 1])

        return {
            "expression": expression_str,
            "predictions": predictions.tolist(),
            "details": {"complexity": complexity}
        }
