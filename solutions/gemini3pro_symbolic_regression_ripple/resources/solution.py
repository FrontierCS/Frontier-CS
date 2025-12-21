import numpy as np
import pandas as pd
from pysr import PySRRegressor
import sympy

class Solution:
    def __init__(self, **kwargs):
        pass

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        """
        Solves the symbolic regression problem for the Ripple dataset.
        """
        try:
            # Configure PySRRegressor with parameters optimized for the evaluation environment (8 vCPUs)
            # and the problem characteristics (Ripple -> trig + poly).
            model = PySRRegressor(
                niterations=100,            # Reasonable balance for time/accuracy
                binary_operators=["+", "-", "*", "/", "^"], # Include power for polynomials/roots
                unary_operators=["sin", "cos", "exp", "log"],
                populations=24,             # Approx 3 populations per core
                population_size=40,
                maxsize=50,                 # Allow sufficient complexity for concentric waves
                ncycles_per_iteration=500,
                procs=8,
                multiprocessing=True,
                verbosity=0,
                progress=False,
                random_state=42,
                model_selection="best",     # Select best model based on score/complexity
                batching=True,
                batch_size=2000,            # Efficient for larger datasets
                constraints={'^': (-1, 1)}, # Limit power exponent complexity
                timeout_in_seconds=300,     # Safety timeout (5 mins)
                temp_equation_file=None,
                delete_tempfiles=True
            )
            
            # Disable batching for small datasets to ensure convergence
            if X.shape[0] < 2000:
                model.set_params(batching=False)
                
            # Fit the model
            model.fit(X, y, variable_names=["x1", "x2"])
            
            # Extract the best symbolic expression
            best_expr = model.sympy()
            expression = str(best_expr)
            
            # Generate predictions using the fitted model
            predictions = model.predict(X)
            
            if isinstance(predictions, np.ndarray):
                predictions = predictions.tolist()
                
        except Exception:
            # Fallback to simple Linear Regression if Symbolic Regression fails
            x1, x2 = X[:, 0], X[:, 1]
            A = np.column_stack([x1, x2, np.ones_like(x1)])
            coeffs, _, _, _ = np.linalg.lstsq(A, y, rcond=None)
            a, b, c = coeffs
            expression = f"{a}*x1 + {b}*x2 + {c}"
            predictions = (a * x1 + b * x2 + c).tolist()

        return {
            "expression": expression,
            "predictions": predictions,
            "details": {}
        }
