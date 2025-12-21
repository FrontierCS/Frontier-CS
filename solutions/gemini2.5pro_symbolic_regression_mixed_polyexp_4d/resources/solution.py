import numpy as np
import sympy as sp
from pysr import PySRRegressor

# These imports are required for the final expression to be evaluable by the backend
from numpy import sin, cos, exp, log

class Solution:
    def __init__(self, **kwargs):
        """
        No-op constructor.
        """
        pass

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        """
        Finds a symbolic expression for the given dataset.

        Args:
            X: Feature matrix of shape (n, 4)
            y: Target values of shape (n,)

        Returns:
            A dictionary containing the symbolic expression and optionally predictions.
        """
        
        # Configure PySRRegressor. The parameters are chosen to be more aggressive
        # than the defaults, as this is a 4D problem which is significantly harder
        # than 1D or 2D cases.
        model = PySRRegressor(
            niterations=75,         # More generations to find a good solution
            populations=40,         # Leverage multiple cores (8 vCPUs available)
            population_size=50,     # Larger population size for diversity
            maxsize=35,             # Allow for moderately complex expressions
            
            # All allowed operators as per problem specification
            binary_operators=["+", "-", "*", "/", "**"],
            unary_operators=["sin", "cos", "exp", "log"],

            # Use a timeout as a safeguard against excessively long runs
            timeout_in_seconds=600, # 10 minutes

            # Optimizes constants in the final expression for better accuracy
            weight_optimize=True,

            # Standard settings for competition environment
            model_selection="best",
            verbosity=0,
            progress=False,
            random_state=42,
            temp_equation_file=True,
        )

        try:
            # Fit the model to the data
            model.fit(X, y, variable_names=["x1", "x2", "x3", "x4"])
            
            # Check if any valid equations were found
            if not hasattr(model, 'equations_') or model.equations_.empty:
                raise ValueError("PySR did not find any equations.")

            # Get the best equation as a sympy object and convert to a string
            best_sympy_expr = model.sympy()
            expression_str = str(best_sympy_expr)
            
            # Replace any potential sympy artifacts like 'zoo' (complex infinity)
            expression_str = expression_str.replace('zoo', '1e100')

            # Generate predictions from the best model
            predictions = model.predict(X)

            # Sanity check predictions for NaN or Inf values, which indicate an unstable expression
            if np.any(~np.isfinite(predictions)):
                raise ValueError("PySR generated unstable predictions (NaN or Inf).")

            # Extract complexity from the best model's details
            complexity = model.get_best().get("complexity", 0)

            return {
                "expression": expression_str,
                "predictions": predictions.tolist(),
                "details": {"complexity": complexity}
            }

        except Exception as e:
            # Fallback to a robust linear regression model if PySR fails
            # This ensures a valid (if suboptimal) solution is always returned.
            x1, x2, x3, x4 = X[:, 0], X[:, 1], X[:, 2], X[:, 3]
            
            # Create the design matrix with an intercept term
            A = np.c_[x1, x2, x3, x4, np.ones_like(x1)]
            
            try:
                # Solve for coefficients using least squares
                coeffs, _, _, _ = np.linalg.lstsq(A, y, rcond=None)
                a, b, c, d, e = coeffs
                
                # Format the linear expression string
                expression = f"{a:.6f}*x1 + {b:.6f}*x2 + {c:.6f}*x3 + {d:.6f}*x4 + {e:.6f}"
                
                # Calculate predictions from the linear model
                predictions = a * x1 + b * x2 + c * x3 + d * x4 + e
            
            except np.linalg.LinAlgError:
                # If least squares fails (e.g., singular matrix), fall back to the mean
                mean_y = np.mean(y)
                expression = str(mean_y)
                predictions = np.full_like(y, mean_y)

            return {
                "expression": expression,
                "predictions": predictions.tolist(),
                "details": {"fallback_reason": str(e)}
            }
