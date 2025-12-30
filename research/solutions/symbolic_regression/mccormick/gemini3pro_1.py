import numpy as np
import pandas as pd
import sympy
from pysr import PySRRegressor
import tempfile
import os
import uuid

class Solution:
    def __init__(self, **kwargs):
        pass

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        """
        Solves the symbolic regression problem for the McCormick dataset using PySR.
        """
        # Create a unique temporary file for the hall of fame to avoid collisions
        # and permission issues in the current working directory.
        unique_id = str(uuid.uuid4())
        equation_file = os.path.join(tempfile.gettempdir(), f"pysr_hof_{unique_id}.csv")

        # Configuration for PySRRegressor
        # The McCormick function is f(x1, x2) = sin(x1 + x2) + (x1 - x2)^2 - 1.5*x1 + 2.5*x2 + 1
        # It involves trigonometric (sin) and polynomial terms (square, linear).
        # We include basic arithmetic and sin/cos.
        model = PySRRegressor(
            niterations=100,               # Number of evolution iterations
            binary_operators=["+", "-", "*"],
            unary_operators=["sin", "cos"], # cos included as it's related to sin
            maxsize=40,                    # Allow sufficient complexity
            populations=16,                # 2x vCPUs for diversity
            population_size=40,
            ncycles_per_iteration=500,
            model_selection="best",        # Balance accuracy and complexity
            verbosity=0,
            progress=False,
            random_state=42,
            equation_file=equation_file,
            tempdir=tempfile.gettempdir(),
            early_stop_condition=1e-7,     # Stop if we find an exact match
            timeout_in_seconds=300,        # Time limit
            deterministic=True,
            procs=8
        )

        try:
            # Fit the model
            model.fit(X, y, variable_names=["x1", "x2"])

            # Retrieve the best expression
            best_sympy = model.sympy()
            expression = str(best_sympy)
            
            # Generate predictions using the model
            predictions = model.predict(X)

        except Exception:
            # Fallback strategy: Linear Regression
            # If symbolic regression fails or times out, return a linear baseline.
            # Fit coefficients: y = a*x1 + b*x2 + c
            A = np.column_stack([X, np.ones(X.shape[0])])
            coeffs, _, _, _ = np.linalg.lstsq(A, y, rcond=None)
            
            # Calculate predictions
            predictions = A @ coeffs
            
            # format expression string
            a, b, c = coeffs[0], coeffs[1], coeffs[2]
            expression = f"({a})*x1 + ({b})*x2 + ({c})"

        finally:
            # Clean up temporary files created by PySR
            if os.path.exists(equation_file):
                try:
                    os.remove(equation_file)
                except OSError:
                    pass
            
            bkup_file = equation_file + ".bkup"
            if os.path.exists(bkup_file):
                try:
                    os.remove(bkup_file)
                except OSError:
                    pass

        return {
            "expression": expression,
            "predictions": predictions.tolist(),
            "details": {}
        }