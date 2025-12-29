import numpy as np
from pysr import PySRRegressor
import sympy

class Solution:
    def __init__(self, **kwargs):
        pass

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        """
        Solves the symbolic regression problem for the McCormick dataset.
        """
        # Define variable names for the problem
        variable_names = ["x1", "x2"]
        
        try:
            # Configure PySRRegressor
            # We focus on the operators likely involved in the McCormick function:
            # sin, cos, and basic arithmetic (+, -, *)
            # Limiting the search space improves convergence speed.
            model = PySRRegressor(
                niterations=40,
                binary_operators=["+", "-", "*"],
                unary_operators=["sin", "cos"],
                populations=8,
                population_size=40,
                maxsize=35,
                model_selection="best",
                verbosity=0,
                progress=False,
                random_state=42,
                temp_equation_file=True,
                procs=8
            )

            # Fit the model to the data
            model.fit(X, y, variable_names=variable_names)

            # Extract the best expression found
            best_expr = model.sympy()
            expression = str(best_expr)
            
            # Generate predictions using the model
            predictions = model.predict(X)

        except Exception:
            # Fallback strategy: Quadratic Regression
            # The McCormick function contains squared terms and linear terms.
            # A quadratic polynomial is a strong baseline if symbolic regression fails.
            # f(x1, x2) ~ c0 + c1*x1 + c2*x2 + c3*x1^2 + c4*x2^2 + c5*x1*x2
            
            x1 = X[:, 0]
            x2 = X[:, 1]
            ones = np.ones_like(x1)
            
            # Construct design matrix
            A = np.column_stack([ones, x1, x2, x1**2, x2**2, x1*x2])
            
            # Solve using least squares
            coeffs, _, _, _ = np.linalg.lstsq(A, y, rcond=None)
            c = coeffs
            
            # Format expression string
            expression = (f"{c[0]} + {c[1]}*x1 + {c[2]}*x2 + "
                          f"{c[3]}*x1**2 + {c[4]}*x2**2 + {c[5]}*x1*x2")
            
            # Compute predictions
            predictions = A @ coeffs

        return {
            "expression": expression,
            "predictions": predictions,
            "details": {}
        }