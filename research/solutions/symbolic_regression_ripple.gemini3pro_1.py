import numpy as np
import pandas as pd
from pysr import PySRRegressor
import sympy
import tempfile
import os

class Solution:
    def __init__(self, **kwargs):
        pass

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        # Use a temporary directory to avoid creating persistent files
        with tempfile.TemporaryDirectory() as tmp_dir:
            # Configure PySRRegressor with parameters optimized for the environment
            model = PySRRegressor(
                niterations=100,
                binary_operators=["+", "-", "*", "/"],
                unary_operators=["sin", "cos", "exp", "log"],
                populations=16,  # Leverage the 8 vCPUs
                population_size=40,
                maxsize=40,      # Allow sufficient complexity for ripple patterns
                verbosity=0,
                progress=False,
                random_state=42,
                temp_equation_file=os.path.join(tmp_dir, "hall_of_fame.csv"),
                model_selection="best",
                loss="L2DistLoss()",
            )
            
            # Fit the symbolic regression model
            # Mapping columns 0, 1 to x1, x2 explicitly
            model.fit(X, y, variable_names=["x1", "x2"])
            
            try:
                # Retrieve the best expression as a sympy object and convert to string
                best_expr = model.sympy()
                expression = str(best_expr)
                
                # Generate predictions
                predictions = model.predict(X)
            except Exception:
                # Fallback in unlikely case of failure
                expression = "0.0 * x1"
                predictions = np.zeros(len(y))
            
            return {
                "expression": expression,
                "predictions": predictions.tolist(),
                "details": {}
            }