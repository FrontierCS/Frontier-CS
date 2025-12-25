import numpy as np
from pysr import PySRRegressor
import sympy

class Solution:
    """
    A solution for symbolic regression using the PySR library.
    This class wraps the PySRRegressor to find a symbolic expression
    that fits the given data. It is configured for a CPU-only environment
    with multiple cores.
    """
    def __init__(self, **kwargs):
        """
        Initializes the Solution class.
        """
        pass

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        """
        Finds a symbolic expression for the given dataset.

        Args:
            X: Feature matrix of shape (n, 2).
            y: Target values of shape (n,).

        Returns:
            A dictionary containing the symbolic expression, predictions,
            and other details.
        """
        # Configure the PySR regressor with parameters optimized for the
        # problem and environment.
        model = PySRRegressor(
            # Search and evolution parameters
            niterations=150,
            populations=40,
            population_size=50,

            # Operators allowed in the expressions
            binary_operators=["+", "-", "*", "/", "**"],
            unary_operators=["sin", "cos", "exp", "log"],

            # Complexity settings
            maxsize=30,
            # Constraints to guide the search by preventing deep nesting
            nested_constraints={"sin": 1, "cos": 1, "exp": 1, "log": 1},
            
            # Performance and environment settings
            procs=8,

            # Reproducibility and output control
            random_state=42,
            verbosity=0,
            progress=False,

            # Model selection strategy
            model_selection="best",
        )

        try:
            # Fit the model to the data
            model.fit(X, y, variable_names=["x1", "x2"])
        except Exception:
            # If PySR fails for any reason, ensure the fallback is triggered.
            model.equations_ = []

        # Check if PySR found any valid equations.
        if not hasattr(model, 'equations_') or len(model.equations_) == 0:
            # Fallback to a linear regression model if PySR fails.
            # This provides a robust baseline solution.
            x1, x2 = X[:, 0], X[:, 1]
            A = np.column_stack([x1, x2, np.ones_like(x1)])
            try:
                coeffs, _, _, _ = np.linalg.lstsq(A, y, rcond=None)
                a, b, c = coeffs
                expression = f"{a:.15g}*x1 + {b:.15g}*x2 + {c:.15g}"
                predictions = (a * x1 + b * x2 + c).tolist()
            except np.linalg.LinAlgError:
                # If linear regression also fails, fall back to the mean.
                mean_y = np.mean(y)
                expression = f"{mean_y:.15g}"
                predictions = np.full_like(y, mean_y).tolist()
        else:
            # If PySR succeeds, get the best expression.
            best_expr_sympy = model.sympy()
            expression = str(best_expr_sympy)
            
            # Use the fitted model to generate predictions for highest precision.
            predictions = model.predict(X).tolist()

        return {
            "expression": expression,
            "predictions": predictions,
            "details": {}
        }
