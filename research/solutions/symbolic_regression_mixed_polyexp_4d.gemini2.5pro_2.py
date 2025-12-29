import numpy as np
import pandas as pd
from pysr import PySRRegressor
import sympy

class Solution:
    def __init__(self, **kwargs):
        """
        Constructor for the Solution class.
        The `**kwargs` are not used in this implementation.
        """
        pass

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        """
        Uses symbolic regression to find a mathematical expression that fits the data.

        Args:
            X: A numpy array of shape (n, 4) representing the input features.
            y: A numpy array of shape (n,) representing the target values.

        Returns:
            A dictionary containing the best-fit expression, its predictions, and
            details like complexity.
        """
        variable_names = ["x1", "x2", "x3", "x4"]
        
        # Configure PySRRegressor with parameters tuned for the 4D PolyExp problem
        # on an 8-core CPU environment.
        model = PySRRegressor(
            niterations=100,
            populations=40,
            population_size=50,
            maxsize=35,
            procs=8,
            random_state=42,
            binary_operators=["+", "-", "*", "/", "**"],
            unary_operators=["exp", "log", "sin", "cos"],
            
            # Gradually increase max complexity to find simple expressions first
            warmup_maxsize_by=0.5,
            
            # Assign higher complexity to division and power operators
            complexity_of_operators={"/": 2, "**": 2},
            
            # Constrain nesting of operators to reduce search space
            nested_constraints={
                "sin": {"sin": 0, "cos": 0},
                "cos": {"sin": 0, "cos": 0},
                "exp": {"exp": 0},
                "log": {"log": 0},
            },
            
            # Ensure all features are considered
            select_k_features=4,

            # Suppress verbose output during fitting
            verbosity=0,
            progress=False,
            
            # Use a temporary file for caching equations
            temp_equation_file=True,
        )

        try:
            model.fit(X, y, variable_names=variable_names)
        except (Exception, SystemExit):
            # Fallback to a linear model if PySR encounters a critical error
            return self._linear_fallback(X, y)

        # Check if PySR found any valid equations
        if model.equations_ is None or len(model.equations_) == 0:
            return self._linear_fallback(X, y)

        # Retrieve the best equation found by PySR
        best_equation = model.get_best()
        
        # Convert the sympy expression to a string for the output
        expression_sympy = best_equation.sympy_format
        expression_str = str(expression_sympy)

        # Generate predictions using the best model
        predictions = model.predict(X)

        # Get the complexity of the expression
        complexity = best_equation.complexity

        return {
            "expression": expression_str,
            "predictions": predictions.tolist(),
            "details": {
                "complexity": int(complexity)
            }
        }

    def _linear_fallback(self, X: np.ndarray, y: np.ndarray) -> dict:
        """
        Provides a linear regression model as a fallback solution.
        This is used if the primary symbolic regression fails.

        Args:
            X: Input features.
            y: Target values.

        Returns:
            A dictionary with a linear expression and its predictions.
        """
        x1, x2, x3, x4 = X[:, 0], X[:, 1], X[:, 2], X[:, 3]

        try:
            # Create the design matrix for linear regression with an intercept
            A = np.column_stack([x1, x2, x3, x4, np.ones_like(x1)])
            # Solve for the coefficients using least squares
            coeffs, _, _, _ = np.linalg.lstsq(A, y, rcond=None)
            a, b, c, d, e = coeffs

            # Format the expression string
            expression = f"{a:.6f}*x1 + {b:.6f}*x2 + {c:.6f}*x3 + {d:.6f}*x4 + {e:.6f}"
            
            # Calculate predictions
            predictions = a * x1 + b * x2 + c * x3 + d * x4 + e
            
            # Complexity: 4 multiplications and 4 additions = 8 binary operators
            # C = 2 * 8 = 16
            complexity = 16

        except np.linalg.LinAlgError:
            # If least squares fails, fall back to the mean of y
            mean_y = np.mean(y)
            expression = f"{mean_y:.6f}"
            predictions = np.full_like(y, mean_y)
            complexity = 0

        return {
            "expression": expression,
            "predictions": predictions.tolist(),
            "details": {
                "complexity": complexity
            }
        }