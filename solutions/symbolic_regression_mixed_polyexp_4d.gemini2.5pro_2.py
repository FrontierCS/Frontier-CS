import numpy as np
from pysr import PySRRegressor
import sympy

class Solution:
    def __init__(self, **kwargs):
        pass

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        """
        Finds a symbolic expression for the given data using PySR.
        """
        # Configure PySR for a potentially complex 4D problem, leveraging the
        # 8-core CPU environment for a thorough search.
        model = PySRRegressor(
            niterations=120,
            populations=40,
            population_size=50,
            binary_operators=["+", "-", "*", "/"],
            unary_operators=["exp", "cos", "sin", "log"],
            maxsize=40,
            
            # Let PySR automatically use all available CPU cores.
            
            # A timeout is set as a safeguard to ensure a solution is returned
            # within typical evaluation time limits.
            timeout_in_seconds=870,  # 14.5 minutes

            # Use a deterministic random state for reproducibility.
            random_state=42,

            # Suppress verbose output during execution.
            verbosity=0,
            progress=False,
        )

        try:
            model.fit(X, y, variable_names=["x1", "x2", "x3", "x4"])
        except Exception:
            # If PySR encounters an unrecoverable error, use a fallback.
            return self._fallback(X, y)

        # Check if PySR found any valid equations.
        if not hasattr(model, 'equations') or model.equations.empty:
            return self._fallback(X, y)

        # Retrieve the best-scoring equation from the search.
        best_equation = model.get_best()
        
        # Convert the sympy representation of the equation to a Python-evaluable string.
        expression_str = sympy.sstr(best_equation.sympy_format, full_prec=False)
        complexity = best_equation.complexity

        # The 'predictions' field is optional and will be computed by the evaluator
        # from the expression if set to None.
        return {
            "expression": expression_str,
            "predictions": None,
            "details": {"complexity": complexity}
        }

    def _fallback(self, X: np.ndarray, y: np.ndarray) -> dict:
        """
        Provides a simple linear regression model as a fallback solution if
        PySR fails or finds no equations.
        """
        x1, x2, x3, x4 = X[:, 0], X[:, 1], X[:, 2], X[:, 3]
        A = np.c_[x1, x2, x3, x4, np.ones_like(x1)]
        try:
            coeffs, _, _, _ = np.linalg.lstsq(A, y, rcond=None)
            a, b, c, d, e = coeffs
            expression = f"{a:.6f}*x1 + {b:.6f}*x2 + {c:.6f}*x3 + {d:.6f}*x4 + {e:.6f}"
            
            return {
                "expression": expression,
                "predictions": None,
                "details": {}
            }
        except np.linalg.LinAlgError:
            # As a last resort, if linear algebra fails, return the mean.
            mean_y = np.mean(y)
            expression = f"{mean_y:.6f}"

            return {
                "expression": expression,
                "predictions": None,
                "details": {}
            }
