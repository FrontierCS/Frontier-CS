import numpy as np
import sympy as sp
from pysr import PySRRegressor
import warnings
import os

# Suppress warnings and Julia output
warnings.filterwarnings("ignore")
os.environ["JULIA_ERROR_COLOR"] = "none"

class Solution:
    def __init__(self, **kwargs):
        pass

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        """
        Solves the Symbolic Regression problem for the McCormick dataset.
        Target function: f(x1, x2) = sin(x1 + x2) + (x1 - x2)^2 - 1.5x1 + 2.5x2 + 1
        """
        
        # Configure PySRRegressor
        # Settings are tuned for the available 8 vCPUs and the known complexity of the McCormick function.
        model = PySRRegressor(
            niterations=60,                   # Sufficient iterations for convergence on this dataset
            binary_operators=["+", "-", "*"], # Basic arithmetic is sufficient (powers handled by *)
            unary_operators=["sin", "cos"],   # Trigonometric functions required
            maxsize=45,                       # Allow enough nodes for the full expression
            populations=24,                   # Parallel populations (multiple of 8 vCPUs)
            population_size=40,               # Size of each population
            ncycles_per_iteration=500,        # Evolution steps per iteration
            model_selection="best",           # Select model optimizing accuracy/complexity
            verbosity=0,                      # Suppress output
            progress=False,                   # Suppress progress bar
            random_state=42,                  # Reproducibility
            deterministic=True,               # Deterministic behavior
            procs=8,                          # Utilize all available cores
            multiprocessing=True,             # Enable multiprocessing
            temp_equation_file=True,          # Use temp files
            delete_tempfiles=True,            # Cleanup
            timeout_in_seconds=300            # Safety timeout
        )

        try:
            # Ensure target is 1D array
            y_flat = y.ravel()
            
            # Fit the symbolic regression model
            model.fit(X, y_flat, variable_names=["x1", "x2"])
            
            # Retrieve the best expression found
            # model.sympy() returns a sympy object of the best equation
            best_expr = model.sympy()
            expression = str(best_expr)
            
            # Generate predictions
            predictions = model.predict(X)
            
            # Ensure predictions are flattened
            if predictions.ndim > 1:
                predictions = predictions.flatten()
                
        except Exception:
            # Robust fallback: Linear Regression
            # This ensures the solution returns a valid result even if symbolic regression fails
            x1 = X[:, 0]
            x2 = X[:, 1]
            # Solve for coefficients: y = a*x1 + b*x2 + c
            A = np.column_stack([x1, x2, np.ones_like(x1)])
            coeffs, _, _, _ = np.linalg.lstsq(A, y.ravel(), rcond=None)
            a, b, c = coeffs
            
            expression = f"{a}*x1 + {b}*x2 + {c}"
            predictions = a * x1 + b * x2 + c

        return {
            "expression": expression,
            "predictions": predictions.tolist(),
            "details": {}
        }
