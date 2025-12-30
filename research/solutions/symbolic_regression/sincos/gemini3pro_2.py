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
        """
        Solves the symbolic regression problem using PySR.
        """
        # Create a temporary directory for PySR's equation file
        temp_dir = tempfile.mkdtemp()
        equation_file = os.path.join(temp_dir, "hall_of_fame.csv")

        try:
            # Initialize PySRRegressor
            # Configured for trigonometric discovery based on 'SinCos' dataset
            model = PySRRegressor(
                niterations=100,
                binary_operators=["+", "-", "*", "/", "^"],
                unary_operators=["sin", "cos", "exp", "log"],
                populations=20,
                population_size=33,
                maxsize=30,
                verbosity=0,
                progress=False,
                random_state=42,
                equation_file=equation_file,
                model_selection="best",
                temp_equation_file=True,
                delete_tempfiles=True,
                loss="L2DistLoss()",
            )

            # Fit the model
            model.fit(X, y, variable_names=["x1", "x2"])

            # Retrieve the best expression as a sympy object
            best_expr = model.sympy()
            expression = str(best_expr)

            # Compute predictions
            predictions = model.predict(X)
            predictions = predictions.tolist()

        except Exception:
            # Fallback to linear regression if PySR fails
            x1, x2 = X[:, 0], X[:, 1]
            A = np.column_stack([x1, x2, np.ones_like(x1)])
            coeffs, _, _, _ = np.linalg.lstsq(A, y, rcond=None)
            a, b, c = coeffs
            
            expression = f"{a}*x1 + {b}*x2 + {c}"
            predictions = (a * x1 + b * x2 + c).tolist()

        finally:
            # Cleanup temporary directory
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)

        return {
            "expression": expression,
            "predictions": predictions,
            "details": {}
        }