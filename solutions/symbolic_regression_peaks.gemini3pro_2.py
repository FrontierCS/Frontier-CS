import numpy as np
import pandas as pd
import sympy
from pysr import PySRRegressor
import tempfile
import os
import shutil

class Solution:
    def __init__(self, **kwargs):
        pass

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        # Create a temporary directory for PySR output files
        temp_dir = tempfile.mkdtemp()
        equation_file = os.path.join(temp_dir, "hall_of_fame.csv")
        
        try:
            # Configure PySRRegressor
            # Optimized for Peaks dataset:
            # - exp, sin, cos for wavelike and gaussian features
            # - moderate complexity limit
            # - multiprocessing enabled
            model = PySRRegressor(
                niterations=50,
                binary_operators=["+", "-", "*", "/"],
                unary_operators=["exp", "sin", "cos"],
                populations=20,
                population_size=40,
                maxsize=35,
                verbosity=0,
                progress=False,
                random_state=42,
                procs=8,
                equation_file=equation_file,
                deterministic=True,
                model_selection="best",
            )
            
            # Fit the model
            model.fit(X, y, variable_names=["x1", "x2"])
            
            # Retrieve the best expression
            best_expr = model.sympy()
            expression_str = str(best_expr)
            
            # Generate predictions
            predictions = model.predict(X)
            
            # Check for validity
            if np.any(np.isnan(predictions)) or np.any(np.isinf(predictions)):
                raise ValueError("Model produced NaN or Inf predictions")
                
        except Exception:
            # Fallback to Linear Regression if Symbolic Regression fails
            x1 = X[:, 0]
            x2 = X[:, 1]
            # [x1, x2, 1]
            A = np.column_stack([x1, x2, np.ones_like(x1)])
            coeffs, _, _, _ = np.linalg.lstsq(A, y, rcond=None)
            a, b, c = coeffs
            
            expression_str = f"{a}*x1 + {b}*x2 + {c}"
            predictions = a * x1 + b * x2 + c
            
        finally:
            # Cleanup temporary files
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)

        return {
            "expression": expression_str,
            "predictions": predictions.tolist(),
            "details": {}
        }
