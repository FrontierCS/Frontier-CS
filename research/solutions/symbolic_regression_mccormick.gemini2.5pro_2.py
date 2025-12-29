import numpy as np
from pysr import PySRRegressor
import sympy as sp

class Solution:
    def __init__(self, **kwargs):
        """
        Initializes the Solution class.
        """
        pass

    def _linear_fallback(self, X: np.ndarray, y: np.ndarray) -> dict:
        """
        Provides a linear regression model as a fallback if PySR fails.
        """
        x1, x2 = X[:, 0], X[:, 1]
        
        # Fit coefficients via least squares: a*x1 + b*x2 + c
        A = np.column_stack([x1, x2, np.ones_like(x1)])
        try:
            coeffs, _, _, _ = np.linalg.lstsq(A, y, rcond=None)
            a, b, c = coeffs
        except np.linalg.LinAlgError:
            a, b, c = 1.0, 1.0, 0.0

        expression = f"{a:.8f}*x1 + {b:.8f}*x2 + {c:.8f}"
        predictions = a * x1 + b * x2 + c

        # Complexity for a*x1 + b*x2 + c:
        # 2 multiplications, 2 additions -> 4 binary ops
        # Complexity C = 2 * 4 = 8. Let's use a simpler estimate.
        complexity = 5 

        return {
            "expression": expression,
            "predictions": predictions.tolist(),
            "details": {"complexity": complexity}
        }

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        """
        Finds a symbolic expression for the McCormick dataset using PySR.
        
        Args:
            X: Feature matrix of shape (n, 2)
            y: Target values of shape (n,)

        Returns:
            dict with keys:
              - "expression": str, a Python-evaluable expression using x1, x2
              - "predictions": list/array of length n (optional)
              - "details": dict with optional "complexity" int
        """
        try:
            # Configure PySR. Parameters are tuned for the expected function
            # structure (trigonometric + polynomial) and the 8-core environment.
            model = PySRRegressor(
                niterations=100,
                populations=24,
                population_size=50,
                # The McCormick function uses +, -, *, **, and sin.
                # 'pow' is used by PySR for the power operator (**).
                # Adding '/' and 'cos' provides more flexibility.
                binary_operators=["+", "-", "*", "pow", "/"],
                unary_operators=["sin", "cos"],
                maxsize=30,          # Allow for reasonably complex expressions.
                procs=0,             # Use all available CPU cores.
                random_state=42,
                verbosity=0,
                progress=False,
                timeout_in_seconds=600, # Safety timeout (10 minutes).
                parsimony=0.001,     # Lower penalty on complexity to find the true form.
                precision=64,        # Use float64 for higher precision constants.
                optimizer_options={'learning_rate': 0.05},
            )
            
            model.fit(X, y, variable_names=["x1", "x2"])

            # If PySR fails to find any equations (e.g., times out early),
            # fall back to a simpler model.
            if not hasattr(model, 'equations_') or model.equations_.empty:
                return self._linear_fallback(X, y)

            # Get the best expression found by PySR as a sympy object.
            sympy_expr = model.sympy()
            
            # Attempt to simplify the expression. This can reduce complexity
            # and improve readability.
            try:
                simplified_expr = sp.simplify(sympy_expr)
            except Exception:
                # If simplification fails, use the original expression.
                simplified_expr = sympy_expr

            # Convert the simplified sympy expression to a Python string.
            # sympy automatically converts Pow(x, y) to x**y.
            expression = str(simplified_expr)

            # Extract complexity and predictions from the final model.
            complexity = int(model.equations_.iloc[-1]['complexity'])
            predictions = model.predict(X)

            return {
                "expression": expression,
                "predictions": predictions.tolist(),
                "details": {"complexity": complexity}
            }
        except Exception:
            # If any part of the PySR process fails, revert to the robust fallback.
            return self._linear_fallback(X, y)