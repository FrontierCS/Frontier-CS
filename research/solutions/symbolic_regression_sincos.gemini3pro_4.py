import numpy as np
from pysr import PySRRegressor
import sympy
import warnings

# Suppress warnings from libraries to keep output clean
warnings.filterwarnings("ignore")

class Solution:
    def __init__(self, **kwargs):
        pass

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        """
        Solves the symbolic regression problem using PySR.
        
        Args:
            X: Feature matrix of shape (n, 2)
            y: Target values of shape (n,)

        Returns:
            dict containing expression, predictions, and details
        """
        # Ensure inputs are contiguous float64 arrays
        X = np.ascontiguousarray(X, dtype=np.float64)
        y = np.ascontiguousarray(y, dtype=np.float64)

        # Configure PySRRegressor
        # Optimized for SinCos dataset on 8 vCPUs
        # Trigonometric functions are prioritized in unary_operators
        model = PySRRegressor(
            niterations=100,                  # Sufficient iterations for convergence
            binary_operators=["+", "-", "*", "/"],
            unary_operators=["sin", "cos", "exp", "log"],
            populations=32,                   # 4 populations per core (8 vCPUs)
            population_size=40,
            maxsize=40,                       # Limit complexity
            verbosity=0,
            progress=False,
            random_state=42,
            procs=8,                          # Utilize all 8 vCPUs
            multithreading=False,             # Use multiprocessing
            model_selection="best",           # Select best model based on score/complexity
            timeout_in_seconds=600,           # Safety timeout
            early_stop_condition=1e-8,        # Stop if MSE is negligible
            deterministic=True                # Ensure reproducibility
        )

        expression = "0"
        predictions = np.zeros_like(y)

        try:
            # Fit the model
            model.fit(X, y, variable_names=["x1", "x2"])
            
            # Retrieve the best symbolic expression as a string
            # model.sympy() returns the expression selected by 'model_selection'
            best_expr = model.sympy()
            expression = str(best_expr)
            
            # Generate predictions using the fitted model
            predictions = model.predict(X)

        except Exception:
            # Fallback strategy: Linear Regression
            # Used if symbolic regression fails or times out
            try:
                # Add bias column
                A = np.column_stack([X, np.ones(len(X))])
                # Least squares fit
                coeffs, _, _, _ = np.linalg.lstsq(A, y, rcond=None)
                
                # Reconstruct expression string (x1 is col 0, x2 is col 1, bias is col 2)
                a, b, c = coeffs
                expression = f"{a}*x1 + {b}*x2 + {c}"
                predictions = A @ coeffs
            except Exception:
                # Ultimate fallback: Mean constant
                mean_val = np.mean(y)
                expression = str(mean_val)
                predictions = np.full(len(y), mean_val)

        return {
            "expression": expression,
            "predictions": predictions.tolist(),
            "details": {}
        }