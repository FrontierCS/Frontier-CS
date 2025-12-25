import numpy as np
import pandas as pd
import sympy
from pysr import PySRRegressor
import os

class Solution:
    def __init__(self, **kwargs):
        pass

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        """
        Solves the symbolic regression problem using PySR.
        """
        feature_names = ["x1", "x2", "x3", "x4"]
        
        # Configure PySRRegressor
        # Using settings optimized for the provided environment (8 vCPUs) and problem type
        model = PySRRegressor(
            niterations=100,             # Sufficient iterations for 4D complexity
            binary_operators=["+", "-", "*", "/"],
            unary_operators=["exp", "sin", "cos", "log"],
            populations=20,             # Parallel populations matching CPU scale
            population_size=40,
            maxsize=40,                 # Allow for larger expressions (poly interactions + exp)
            model_selection="best",     # Optimize for mix of accuracy and complexity
            verbosity=0,
            progress=False,
            random_state=42,
            procs=8,                    # Use all available vCPUs
            multithreading=False,       # Multiprocessing is generally more stable for PySR
            timeout_in_seconds=300,     # Time limit to ensure return
            deterministic=True
        )

        try:
            # Clean up potential artifacts from previous runs
            if os.path.exists("hall_of_fame.csv"):
                try:
                    os.remove("hall_of_fame.csv")
                except OSError:
                    pass

            # Fit the model
            model.fit(X, y, variable_names=feature_names)
            
            # Retrieve the best expression
            # PySR returns a sympy object which can be converted to a Python string
            best_expr = model.sympy()
            expression = str(best_expr)
            
            # Generate predictions
            predictions = model.predict(X)
            if isinstance(predictions, np.ndarray):
                predictions = predictions.tolist()
                
        except Exception:
            # Fallback: Linear Regression
            # In case of environment issues or search failure, return a valid linear baseline
            X_bias = np.c_[X, np.ones(X.shape[0])]
            coeffs, _, _, _ = np.linalg.lstsq(X_bias, y, rcond=None)
            
            terms = []
            for i in range(4):
                terms.append(f"({coeffs[i]} * x{i+1})")
            terms.append(f"{coeffs[4]}")
            expression = " + ".join(terms)
            
            predictions = (X_bias @ coeffs).tolist()

        return {
            "expression": expression,
            "predictions": predictions,
            "details": {}
        }
