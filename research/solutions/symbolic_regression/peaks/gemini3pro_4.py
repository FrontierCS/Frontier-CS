import numpy as np
import pandas as pd
from pysr import PySRRegressor
import sympy

class Solution:
    def __init__(self, **kwargs):
        pass

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        """
        Solves the symbolic regression problem for the Peaks dataset using PySR.
        """
        # PySRRegressor configuration
        # The Peaks function is complex, involving exponentials and polynomials.
        # We allow a large maxsize and specific operators to capture the structure.
        # model_selection="accuracy" is used to minimize MSE, as the scoring
        # penalty for complexity is relatively small (0.99^delta).
        
        try:
            model = PySRRegressor(
                niterations=200,           # Sufficient iterations for convergence
                binary_operators=["+", "-", "*", "/"],
                unary_operators=["exp", "sin", "cos"], # exp is critical, sin/cos allowed
                maxsize=50,                # Allow for the complexity of the Peaks function
                populations=32,            # Multiple of 8 vCPUs
                population_size=40,
                n_jobs=8,                  # Utilize all vCPUs
                timeout_in_seconds=300,    # 5 minutes max runtime
                model_selection="accuracy",# Select model with best loss (MSE)
                verbosity=0,
                progress=False,
                random_state=42,
                temp_equation_file=True,
                delete_temp_files=True
            )

            # Fit the model with specified variable names
            model.fit(X, y, variable_names=["x1", "x2"])

            # Retrieve the best expression as a sympy object and convert to string
            best_expr = model.sympy()
            expression = str(best_expr)

            # Generate predictions using the fitted model
            predictions = model.predict(X)

            # Check for numerical instability (NaN/Inf)
            if np.any(np.isnan(predictions)) or np.any(np.isinf(predictions)):
                raise ValueError("Model predictions contain NaNs or Infs")

        except Exception:
            # Fallback to Linear Regression if symbolic regression fails
            # This ensures a valid return value even in edge cases
            x1 = X[:, 0]
            x2 = X[:, 1]
            # Design matrix for linear regression: [x1, x2, 1]
            A = np.column_stack([x1, x2, np.ones_like(x1)])
            coeffs, _, _, _ = np.linalg.lstsq(A, y, rcond=None)
            a, b, c = coeffs
            
            # Construct linear expression string
            expression = f"{a}*x1 + {b}*x2 + {c}"
            predictions = a * x1 + b * x2 + c

        return {
            "expression": expression,
            "predictions": predictions.tolist(),
            "details": {}
        }