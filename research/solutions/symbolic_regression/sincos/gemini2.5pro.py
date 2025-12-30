import numpy as np
from pysr import PySRRegressor
import sympy

class Solution:
    def __init__(self, **kwargs):
        pass

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        """
        Fits a symbolic expression to the data using PySR.

        Args:
            X: Feature matrix of shape (n, 2) with columns 'x1', 'x2'.
            y: Target values of shape (n,).

        Returns:
            A dictionary containing the symbolic expression, predictions,
            and optional details like complexity.
        """
        model = PySRRegressor(
            niterations=60,
            populations=32,
            population_size=50,
            procs=8,
            binary_operators=["+", "*", "-"],
            unary_operators=["sin", "cos"],
            maxsize=25,
            random_state=42,
            verbosity=0,
            progress=False,
            model_selection="best",
        )

        try:
            model.fit(X, y, variable_names=["x1", "x2"])

            if not hasattr(model, 'equations_') or model.equations_.empty:
                return self._fallback(X, y)

            best_equation = model.get_best()
            expression_sympy = model.sympy()
            expression_str = self._format_expression(expression_sympy)
            predictions = model.predict(X)
            complexity = best_equation['complexity']

            return {
                "expression": expression_str,
                "predictions": predictions.tolist(),
                "details": {"complexity": int(complexity)}
            }
        except (RuntimeError, IndexError):
            return self._fallback(X, y)

    def _format_expression(self, expr: sympy.Expr) -> str:
        """
        Formats the sympy expression to a string, rounding constants.
        """
        try:
            # Round floating point numbers for a cleaner expression string
            return str(expr.xreplace({n: round(n, 8) for n in expr.atoms(sympy.Float)}))
        except Exception:
            return str(expr)

    def _fallback(self, X: np.ndarray, y: np.ndarray) -> dict:
        """
        Provides a simple linear regression model as a robust fallback.
        """
        x1, x2 = X[:, 0], X[:, 1]
        A = np.c_[x1, x2, np.ones_like(x1)]
        
        try:
            coeffs, _, _, _ = np.linalg.lstsq(A, y, rcond=None)
            a, b, c = coeffs
        except np.linalg.LinAlgError:
            a, b, c = 0.0, 0.0, np.mean(y)

        expression = f"{a:.6f}*x1 + {b:.6f}*x2 + {c:.6f}"
        predictions = a * x1 + b * x2 + c

        return {
            "expression": expression,
            "predictions": predictions.tolist(),
            "details": {}
        }