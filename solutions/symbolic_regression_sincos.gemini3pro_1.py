import numpy as np
from pysr import PySRRegressor
import sympy

class Solution:
    def __init__(self, **kwargs):
        pass

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        """
        Fits a symbolic regression model to the data using PySR.
        """
        try:
            # Initialize PySRRegressor with configurations optimized for the environment and problem
            model = PySRRegressor(
                niterations=100,               # Sufficient iterations for convergence
                binary_operators=["+", "-", "*", "/"],
                unary_operators=["sin", "cos", "exp", "log"],
                populations=16,                # 2x number of vCPUs (8)
                population_size=40,
                maxsize=35,                    # Allow reasonable complexity for trigonometric compositions
                parsimony=0.001,               # Slight penalty for complexity
                verbosity=0,
                progress=False,
                random_state=42,
                procs=8,                       # Use all 8 vCPUs
                multithreading=False,          # Disable multithreading (use multiprocessing via procs)
                model_selection="best",        # Select model optimizing accuracy/complexity trade-off
                temp_equation_file=True,       # Use temp files
                delete_tempfiles=True
            )

            # Fit the model to the data
            # Using variable_names ensures the output expression uses x1, x2
            model.fit(X, y, variable_names=["x1", "x2"])

            # Retrieve the best expression found
            # model.sympy() returns a sympy object, str() converts it to Python expression string
            best_expr = model.sympy()
            expression = str(best_expr)
            
            # Generate predictions using the fitted model
            predictions = model.predict(X)

            return {
                "expression": expression,
                "predictions": predictions.tolist(),
                "details": {}
            }

        except Exception as e:
            # Fallback to Linear Regression if PySR fails
            # This ensures the solution always returns valid output
            x1 = X[:, 0]
            x2 = X[:, 1]
            A = np.column_stack([x1, x2, np.ones(len(x1))])
            coeffs, _, _, _ = np.linalg.lstsq(A, y, rcond=None)
            a, b, c = coeffs

            expression = f"({a}) * x1 + ({b}) * x2 + ({c})"
            predictions = a * x1 + b * x2 + c

            return {
                "expression": expression,
                "predictions": predictions.tolist(),
                "details": {"error": str(e)}
            }
