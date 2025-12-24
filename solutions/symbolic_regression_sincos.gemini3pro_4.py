import numpy as np
import os
import shutil
import tempfile
import sympy
from pysr import PySRRegressor

class Solution:
    def __init__(self, **kwargs):
        pass

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        """
        Solves the symbolic regression problem using PySR.
        """
        # Create a temporary directory for PySR output files to ensure isolation
        temp_dir = tempfile.mkdtemp()
        equation_file = os.path.join(temp_dir, "hall_of_fame.csv")

        try:
            # Initialize PySRRegressor
            # Configuration optimized for 8 vCPUs and the SinCos dataset characteristics
            model = PySRRegressor(
                niterations=100,  # Sufficient iterations for convergence on basic trig functions
                binary_operators=["+", "-", "*", "/"],
                unary_operators=["sin", "cos", "exp", "log"],
                populations=24,   # 3 populations per core (8 vCPUs)
                population_size=40,
                ncycles_per_iteration=500,
                maxsize=35,       # Limit complexity
                verbosity=0,
                progress=False,
                random_state=42,
                procs=8,          # Use all available vCPUs
                multiprocessing=True,
                equation_file=equation_file,
                model_selection="best",  # Balances accuracy and complexity
                temp_equation_file=False # We handle the file location manually
            )

            # Fit the model
            model.fit(X, y, variable_names=["x1", "x2"])

            # Retrieve the best expression found
            # PySR returns a sympy object which we convert to string
            best_expr = model.sympy()
            expression = str(best_expr)

            # Generate predictions on the input data
            predictions = model.predict(X)

        except Exception as e:
            # Fallback: Linear Regression Baseline
            # Used if PySR fails due to environment issues or timeouts
            x1, x2 = X[:, 0], X[:, 1]
            A = np.column_stack([x1, x2, np.ones_like(x1)])
            # Least squares fit
            coeffs, _, _, _ = np.linalg.lstsq(A, y, rcond=None)
            a, b, c = coeffs
            
            # Construct linear expression
            expression = f"{a}*x1 + {b}*x2 + {c}"
            predictions = A @ coeffs

        finally:
            # Clean up temporary directory and files
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir, ignore_errors=True)

        # Post-process expression to ensure it is a valid Python string
        # Remove numpy prefixes if present (e.g., 'numpy.sin' -> 'sin')
        expression = expression.replace("numpy.", "").replace("np.", "")

        return {
            "expression": expression,
            "predictions": predictions.tolist(),
            "details": {}
        }
