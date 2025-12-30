import numpy as np
from pysr import PySRRegressor

class Solution:
    def __init__(self, **kwargs):
        """
        No-op constructor.
        """
        pass

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        """
        Finds a symbolic expression for the given data.

        Args:
            X: Feature matrix of shape (n, 2)
            y: Target values of shape (n,)

        Returns:
            dict with keys:
              - "expression": str, a Python-evaluable expression using x1, x2
              - "predictions": list/array of length n (optional)
              - "details": dict with optional "complexity" int
        """
        
        # Configure PySR based on problem description: "peaks-like function" suggests
        # interactions between polynomial and exponential terms. We tailor the
        # operators to this, which significantly prunes the search space.
        model = PySRRegressor(
            # Search configuration: A balance between search time and depth.
            niterations=80,
            populations=24,
            population_size=40,
            
            # Operators tailored to the problem description
            binary_operators=["+", "-", "*", "**"],
            unary_operators=["exp"],
            
            # Model and environment settings
            maxsize=30,
            procs=8,  # Utilize all 8 vCPUs in the environment
            random_state=42,
            verbosity=0,
            progress=False,
            
            # Heuristic constraints to guide the search towards more stable expressions
            constraints={'pow': (-1, 1)},  # Allow x**const, but not x**f(x)
            nested_constraints={"exp": {"exp": 0}}, # Disallow exp(exp(...))
            
            # Select the model with the best score (trade-off between MSE and complexity)
            model_selection="best",
        )

        try:
            model.fit(X, y, variable_names=["x1", "x2"])
        except Exception:
            # Catch potential errors during PySR execution and fall back.
            model = None

        # Check if PySR found a valid model. If not, fall back to a simple baseline.
        if model is None or len(model.equations_) == 0:
            x1, x2 = X[:, 0], X[:, 1]
            A = np.column_stack([x1, x2, np.ones_like(x1)])
            try:
                coeffs, _, _, _ = np.linalg.lstsq(A, y, rcond=None)
                a, b, c = coeffs
                expression = f"{a:.6f}*x1 + {b:.6f}*x2 + {c:.6f}"
                predictions = a * x1 + b * x2 + c
            except np.linalg.LinAlgError:
                # In the unlikely event lstsq fails, return a constant model
                mean_y = np.mean(y)
                expression = f"{mean_y:.6f}"
                predictions = np.full_like(y, mean_y)

            return {
                "expression": expression,
                "predictions": predictions.tolist(),
                "details": {}
            }
        
        # Get the best expression as a sympy object
        best_expr_sympy = model.sympy()
        
        # Convert the sympy expression to a Python-evaluable string
        expression_str = str(best_expr_sympy)

        # Get predictions from the best-fit model
        predictions = model.predict(X)

        return {
            "expression": expression_str,
            "predictions": predictions.tolist(),
            "details": {}
        }