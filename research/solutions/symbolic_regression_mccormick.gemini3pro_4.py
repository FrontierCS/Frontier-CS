import numpy as np
import sympy as sp
from pysr import PySRRegressor
import tempfile
import os
import uuid

class Solution:
    def __init__(self, **kwargs):
        pass

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        """
        Solves the symbolic regression problem using PySR.
        """
        # Generate a unique path for the equation file to prevent conflicts
        temp_dir = tempfile.gettempdir()
        unique_id = str(uuid.uuid4())
        equation_file = os.path.join(temp_dir, f"hall_of_fame_{unique_id}.csv")

        # Configure PySRRegressor
        # The McCormick function involves trigonometric and polynomial terms.
        # We use a configuration balanced for the 8 vCPU environment.
        model = PySRRegressor(
            niterations=50,
            binary_operators=["+", "-", "*", "/"],
            unary_operators=["sin", "cos", "exp", "log"],
            populations=16,              # 2 populations per core
            population_size=40,
            maxsize=45,                  # Sufficient complexity for McCormick function
            ncycles_per_iteration=500,
            model_selection="best",      # Select best model based on score/complexity
            loss="L2DistLoss",           # MSE
            
            # Compute configuration
            procs=8,                     # Utilize all 8 vCPUs
            multithreading=False,        # Use multiprocessing (default/stable)
            
            # Output control
            verbosity=0,
            progress=False,
            
            # File and State management
            equation_file=equation_file,
            tempdir=temp_dir,
            delete_tempfiles=True,
            random_state=42,
            deterministic=True
        )

        expression = ""
        predictions = None

        try:
            # Fit the model to the data
            # variable_names matches the required output format (x1, x2)
            model.fit(X, y, variable_names=["x1", "x2"])

            # Retrieve the best symbolic expression
            # PySR returns a sympy object which we convert to string
            best_expr = model.sympy()
            expression = str(best_expr)
            
            # Generate predictions using the discovered model
            predictions = model.predict(X)
            
        except Exception:
            # Fallback: Linear Regression if symbolic regression fails
            # This ensures the solution always returns a valid result
            x1 = X[:, 0]
            x2 = X[:, 1]
            A = np.column_stack([x1, x2, np.ones_like(x1)])
            
            # Least squares fit
            result = np.linalg.lstsq(A, y, rcond=None)
            coeffs = result[0]
            a, b, c = coeffs
            
            expression = f"{a}*x1 + {b}*x2 + {c}"
            predictions = a*x1 + b*x2 + c
        
        # Clean up the equation file if it exists
        if os.path.exists(equation_file):
            try:
                os.remove(equation_file)
            except OSError:
                pass

        return {
            "expression": expression,
            "predictions": predictions.tolist(),
            "details": {}
        }
