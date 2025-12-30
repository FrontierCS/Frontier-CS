import numpy as np
from pysr import PySRRegressor
import sympy as sp

class Solution:
    """
    A solution for symbolic regression on the McCormick dataset using PySR.
    """
    def __init__(self, **kwargs):
        """
        Initializes the solution. Any kwargs are ignored.
        """
        pass

    def _get_fallback_expression(self, X: np.ndarray, y: np.ndarray) -> str:
        """
        Computes a simple linear regression expression as a fallback.
        This is used if PySR fails, times out, or finds no valid expressions.

        Args:
            X: Feature matrix.
            y: Target values.

        Returns:
            A string representing the linear model expression.
        """
        x1, x2 = X[:, 0], X[:, 1]
        # Create the design matrix for linear regression: [x1, x2, 1]
        A = np.c_[x1, x2, np.ones_like(x1)]
        try:
            # Solve for the coefficients using least squares
            coeffs, _, _, _ = np.linalg.lstsq(A, y, rcond=None)
            a, b, c = coeffs
            # Format the expression with high precision
            return f"{a:.8f}*x1 + {b:.8f}*x2 + {c:.8f}"
        except np.linalg.LinAlgError:
            # If least squares fails for any reason, return a constant
            return "0.0"

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        """
        Finds a symbolic expression for the given data.

        Args:
            X: Feature matrix of shape (n, 2)
            y: Target values of shape (n,)

        Returns:
            A dictionary containing the symbolic expression.
        """
        # The McCormick function is f(x1, x2) = sin(x1 + x2) + (x1 - x2)**2 - 1.5*x1 + 2.5*x2 + 1
        # This structure guides the selection of operators for PySR.
        
        # Configure PySRRegressor with parameters optimized for the environment and problem.
        # We leverage the 8 vCPUs by setting a high number of populations.
        model = PySRRegressor(
            niterations=40,          # Number of generations for the search
            populations=24,          # More populations than cores for better search diversity
            population_size=40,      # Number of expressions in each population
            procs=8,                 # Utilize all available CPU cores

            # Provide the set of allowed operators. `**` is important for the squared term.
            binary_operators=["+", "-", "*", "**"],
            # `sin` and `cos` are essential for trigonometric components.
            unary_operators=["sin", "cos"],
            
            # Set a maximum complexity to prevent overly complex expressions.
            maxsize=30,
            
            # Use a fixed random state for reproducibility.
            random_state=42,
            
            # Suppress verbose output during execution.
            verbosity=0,
            progress=False,
            
            # A timeout is a critical safeguard in a timed evaluation environment.
            timeout_in_seconds=240,  # 4-minute timeout
        )

        expression_str = None
        try:
            # Run the symbolic regression search.
            model.fit(X, y, variable_names=["x1", "x2"])
            
            # Check if the model found any equations.
            if hasattr(model, 'equations_') and not model.equations_.empty:
                # Retrieve the best expression as a sympy object.
                best_expression_sympy = model.sympy()
                
                # Attempt to simplify the expression for a more canonical form.
                try:
                    simplified_expr = sp.simplify(best_expression_sympy)
                    expression_str = str(simplified_expr)
                except Exception:
                    # If simplification fails, use the original expression.
                    expression_str = str(best_expression_sympy)

        except Exception:
            # If any part of the PySR process fails (e.g., timeout, runtime error),
            # the expression remains None, and the fallback will be used.
            pass

        # If no expression was found by PySR, use the linear fallback.
        if expression_str is None:
            expression_str = self._get_fallback_expression(X, y)

        return {
            "expression": expression_str,
            # Predictions are not returned; they will be computed by the evaluator
            # from the expression, which is more efficient.
            "predictions": None,
            "details": {}
        }