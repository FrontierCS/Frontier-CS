import numpy as np
import pandas as pd
from pysr import PySRRegressor
import sympy

class Solution:
    def __init__(self, **kwargs):
        pass

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        """
        Solves the symbolic regression problem for the Ripple Dataset using PySR.
        """
        # Configure PySRRegressor
        # Optimized for Ripple dataset: standard arithmetic + trig functions for waves
        # CPU constrained environment: Limit iterations but use parallel processing
        model = PySRRegressor(
            niterations=50,
            binary_operators=["+", "-", "*", "/"],
            unary_operators=["sin", "cos", "exp"],  # Log omitted to avoid domain errors on oscillations
            populations=20,
            population_size=35,
            maxsize=40,  # Allow complexity for nested trig/polynomials
            verbosity=0,
            progress=False,
            random_state=42,
            procs=8,
            multithreading=True,
            model_selection="best",
            denoise=False,
            deterministic=True
        )

        try:
            # Fit the model to the data
            model.fit(X, y, variable_names=["x1", "x2"])

            # Extract the best symbolic expression converted to SymPy then string
            best_expr = model.sympy()
            expression = str(best_expr)
            
            # Generate predictions
            predictions = model.predict(X)

        except Exception:
            # Fallback strategy: Quadratic Regression
            # Provides a better baseline than linear for curved surfaces if PySR fails
            x1, x2 = X[:, 0], X[:, 1]
            ones = np.ones_like(x1)
            # A*x1^2 + B*x2^2 + C*x1*x2 + D*x1 + E*x2 + F
            A_mat = np.column_stack([x1**2, x2**2, x1*x2, x1, x2, ones])
            coeffs, _, _, _ = np.linalg.lstsq(A_mat, y, rcond=None)
            
            # Construct prediction
            predictions = A_mat @ coeffs
            
            # Construct valid expression string
            terms = ["x1**2", "x2**2", "x1*x2", "x1", "x2", "1"]
            parts = [f"({c})*{t}" if t != "1" else f"({c})" for c, t in zip(coeffs, terms)]
            expression = " + ".join(parts)

        return {
            "expression": expression,
            "predictions": predictions.tolist(),
            "details": {}
        }
