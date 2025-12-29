import numpy as np
from pysr import PySRRegressor
import warnings

# Suppress common warnings from PySR and its dependencies for cleaner output.
warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=UserWarning)

class Solution:
    """
    A solution for the Symbolic Regression Benchmark - Peaks Dataset problem.
    This implementation uses the PySR library to perform symbolic regression.
    """

    def __init__(self, **kwargs):
        """
        Initialize the Solution class. The main logic is contained within the solve method.
        """
        pass

    def _fallback_solution(self, X: np.ndarray, y: np.ndarray) -> dict:
        """
        Provides a simple linear regression fallback if PySR fails or finds no solution.
        This ensures that the solution always returns a valid, if simple, expression.
        """
        try:
            x1, x2 = X[:, 0], X[:, 1]
            A = np.column_stack([x1, x2, np.ones_like(x1)])
            coeffs, _, _, _ = np.linalg.lstsq(A, y, rcond=None)
            a, b, c = coeffs
            expression = f"{a:.6f}*x1 + {b:.6f}*x2 + {c:.6f}"
            predictions = a * x1 + b * x2 + c
        except Exception:
            # Ultimate fallback if linear regression also fails.
            expression = "0.0"
            predictions = np.zeros_like(y)

        return {
            "expression": expression,
            "predictions": predictions.tolist(),
            "details": {}
        }

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        """
        Finds a symbolic expression for the given data using PySR.

        The PySR regressor is configured with parameters tuned for this specific
        problem, considering the likely structure of the underlying function (peaks,
        exponentials, polynomials) and the evaluation environment (CPU-only).

        Args:
            X: Feature matrix of shape (n, 2) with columns 'x1', 'x2'.
            y: Target values of shape (n,).

        Returns:
            A dictionary containing the discovered symbolic expression,
            corresponding predictions, and details like complexity.
        """
        # Align PySR's internal complexity calculation with the competition's scoring metric.
        # Score = ... * 0.99^max(C - C_ref, 0), where C = 2*(#binary ops) + (#unary ops)
        complexity_of_operators = {
            # Unary operators have a complexity of 1 in the scoring formula.
            "sin": 1, "cos": 1, "exp": 1, "log": 1,
            # Binary operators have a complexity of 2.
            "+": 2, "-": 2, "*": 2, "/": 2, "**": 2
        }

        model = PySRRegressor(
            # Search configuration
            niterations=150,            # A balance between search depth and time constraints.
            populations=32,             # More populations for better parallel exploration on 8 vCPUs.
            population_size=50,         # Larger population size for greater genetic diversity.
            
            # Allowed operators as per the problem specification.
            unary_operators=["exp", "cos", "sin", "log"],
            binary_operators=["+", "-", "*", "/", "**"],
            
            # Set operator complexities to match the external scoring function.
            complexity_of_operators=complexity_of_operators,

            # Constraints on expression structure.
            maxsize=40,                 # Allow for reasonably complex expressions.
            nested_constraints={
                'exp': {'exp': 0}, 'log': {'log': 0},
                'sin': {'sin': 0}, 'cos': {'cos': 0},
            },
            
            # Performance and environment settings.
            procs=8,                    # Utilize all available CPU cores.
            turbo=True,                 # Use a faster, compiled evaluator for expressions.
            
            # Reproducibility and output control.
            random_state=42,
            verbosity=0,
            progress=False,
            
            # A safety timeout to ensure completion within typical platform time limits.
            timeout_in_seconds=550,
            
            # Use a temporary file to cache equations; good practice for long runs.
            temp_equation_file=True,
        )

        try:
            model.fit(X, y, variable_names=["x1", "x2"])
        except Exception:
            # If PySR fails for any reason (e.g., Julia backend issues), revert to fallback.
            return self._fallback_solution(X, y)

        # Check if any valid equations were found during the search.
        if not hasattr(model, 'equations_') or model.equations_.empty:
            return self._fallback_solution(X, y)

        # Retrieve the best-scoring equation found by PySR.
        # .get_best() selects based on the optimal trade-off between accuracy and complexity.
        best_equation = model.get_best()
        
        # Extract the details of the best equation.
        sympy_expr = best_equation["sympy_format"]
        expression = str(sympy_expr)
        
        # Predictions are generated using the same best model.
        predictions = model.predict(X)

        # The complexity score from PySR should align with the contest's definition
        # because we configured the operator complexities accordingly.
        complexity = int(best_equation['complexity'])

        return {
            "expression": expression,
            "predictions": predictions.tolist(),
            "details": {"complexity": complexity}
        }