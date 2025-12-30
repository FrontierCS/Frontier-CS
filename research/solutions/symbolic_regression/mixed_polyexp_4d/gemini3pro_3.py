import numpy as np
import pandas as pd
import sympy
from pysr import PySRRegressor

class Solution:
    def __init__(self, **kwargs):
        pass

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        """
        Solves the symbolic regression problem using PySR.
        
        Args:
            X: Feature matrix of shape (n, 4)
            y: Target values of shape (n,)

        Returns:
            dict containing the expression string and predictions.
        """
        # Define variable names corresponding to the dataset columns
        variable_names = ["x1", "x2", "x3", "x4"]

        # Configure PySRRegressor
        # Optimized for the available 8 vCPUs and the "Mixed PolyExp 4D" problem structure.
        # We allow a reasonably large maxsize to capture the 4D interactions and exponential terms.
        model = PySRRegressor(
            niterations=100,             # Number of evolution iterations
            binary_operators=["+", "-", "*", "/"],
            unary_operators=["sin", "cos", "exp", "log"],
            maxsize=45,                  # Allow sufficient complexity for 4D PolyExp functions
            populations=24,              # Multiple populations for diversity (3 per CPU approx)
            population_size=50,          # Size of each population
            ncycles_per_iteration=500,   # Evolution steps per iteration
            model_selection="best",      # Select the model with best score/complexity trade-off
            verbosity=0,                 # Suppress output
            progress=False,              # Suppress progress bar
            procs=8,                     # Utilize all 8 vCPUs
            multithreading=False,        # Use multiprocessing (standard for PySR)
            random_state=42,             # Ensure reproducibility
            timeout_in_seconds=600,      # Safety timeout (10 minutes)
            tempdir=None,
            delete_tempfiles=True
        )

        try:
            # Fit the symbolic model
            model.fit(X, y, variable_names=variable_names)

            # Retrieve the best expression found
            # model.sympy() returns a sympy expression object
            best_sympy = model.sympy()
            
            # Convert sympy expression to a Python-evaluable string
            expression = str(best_sympy)
            
            # Generate predictions using the fitted model
            predictions = model.predict(X)
            
            # Safety check: if predictions contain NaNs or Infs (unstable model), trigger fallback
            if np.any(np.isnan(predictions)) or np.any(np.isinf(predictions)):
                raise ValueError("Model predictions unstable")

        except Exception:
            # Fallback: Linear Regression
            # If PySR fails or times out, return a baseline linear model.
            
            # Augment X with an intercept column
            A = np.column_stack([X, np.ones(X.shape[0])])
            
            # Compute least squares solution
            coeffs, _, _, _ = np.linalg.lstsq(A, y, rcond=None)
            
            # Compute predictions
            predictions = A @ coeffs
            
            # Construct the expression string: c1*x1 + c2*x2 + c3*x3 + c4*x4 + intercept
            terms = []
            for i, var in enumerate(variable_names):
                terms.append(f"({coeffs[i]} * {var})")
            terms.append(str(coeffs[4])) # Intercept
            expression = " + ".join(terms)

        return {
            "expression": expression,
            "predictions": predictions.tolist(),
            "details": {}
        }