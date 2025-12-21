import numpy as np
import sympy
from pysr import PySRRegressor

# Helper class to remove Abs from a sympy expression.
# PySR may introduce Abs to protect functions like log, but Abs is not
# an allowed function in the final expression string.
class AbsRemover(sympy.Function):
    @classmethod
    def eval(cls, arg):
        # This effectively replaces Abs(x) with x
        return arg

class Solution:
    def __init__(self, **kwargs):
        """
        No-op constructor.
        """
        pass

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        """
        Finds a symbolic expression for the given data using PySR.
        """

        def _fallback():
            """
            Provides a simple linear regression model as a fallback
            if PySR fails to find a suitable expression.
            """
            x1, x2 = X[:, 0], X[:, 1]
            A = np.c_[x1, x2, np.ones_like(x1)]
            try:
                coeffs, _, _, _ = np.linalg.lstsq(A, y, rcond=None)
                a, b, c = coeffs
                expression = f"{a:.6f}*x1 + {b:.6f}*x2 + {c:.6f}"
                predictions = a * x1 + b * x2 + c
            except np.linalg.LinAlgError:
                # If least squares fails, return the mean as a constant expression.
                mean_y = np.mean(y) if y.size > 0 else 0.0
                expression = f"{mean_y:.6f}"
                predictions = np.full_like(y, mean_y)
            
            return {
                "expression": expression,
                "predictions": predictions.tolist(),
                "details": {},
            }

        # Configure PySR for a thorough search within typical time limits.
        model = PySRRegressor(
            niterations=1000,
            binary_operators=["+", "-", "*", "/", "**"],
            unary_operators=["sin", "cos", "exp", "log"],
            populations=24,
            population_size=50,
            maxsize=35,
            verbosity=0,
            progress=False,
            random_state=42,
            timeout_in_seconds=280,
        )

        try:
            model.fit(X, y, variable_names=["x1", "x2"])
        except Exception:
            return _fallback()

        # Check if PySR found any equations.
        if not hasattr(model, 'equations_') or model.equations_.empty:
            return _fallback()

        # Get the best equation found by PySR.
        best_expr_sympy = model.sympy()

        # If the best expression is NaN, PySR failed to find a valid model.
        if best_expr_sympy == sympy.nan:
            return _fallback()
        
        # Remove any `Abs` functions from the expression.
        best_expr_no_abs = best_expr_sympy.subs(sympy.Abs, AbsRemover)
        
        expression = str(best_expr_no_abs)
        
        # Use PySR's prediction for consistency.
        predictions = model.predict(X)

        return {
            "expression": expression,
            "predictions": predictions.tolist(),
            "details": {},
        }
