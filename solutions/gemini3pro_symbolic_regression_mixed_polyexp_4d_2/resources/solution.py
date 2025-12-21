import numpy as np
import pandas as pd
import sympy
import os
from pysr import PySRRegressor

class Solution:
    def __init__(self, **kwargs):
        pass

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        """
        Solves the symbolic regression problem using PySR.
        """
        # Unique temporary file for this execution
        temp_file = f"hall_of_fame_{os.getpid()}.csv"
        
        try:
            # Initialize PySRRegressor with settings optimized for 4D PolyExp
            # Using 8 vCPUs via procs=8 and multiprocessing=True
            model = PySRRegressor(
                niterations=150,  # Sufficient search depth
                binary_operators=["+", "-", "*", "/"],
                unary_operators=["sin", "cos", "exp", "log"],
                populations=20,
                population_size=50,
                maxsize=50,  # Allow for complex mixed expressions
                ncycles_per_iteration=500,
                model_selection="best",
                verbosity=0,
                progress=False,
                random_state=42,
                procs=8,
                multiprocessing=True,
                timeout_in_seconds=300,  # Time limit safeguard
                temp_equation_file=temp_file
            )

            # Fit the model to the data
            model.fit(X, y, variable_names=["x1", "x2", "x3", "x4"])
            
            # Retrieve the best expression found
            best_expr = model.sympy()
            expression = str(best_expr)
            
            # Generate predictions
            predictions = model.predict(X)
            
            # Ensure predictions are a flat list
            if isinstance(predictions, np.ndarray):
                predictions = predictions.flatten().tolist()
            elif not isinstance(predictions, list):
                predictions = list(predictions)

        except Exception:
            # Fallback to Linear Regression if symbolic regression fails
            A = np.column_stack([X, np.ones(X.shape[0])])
            coeffs, _, _, _ = np.linalg.lstsq(A, y, rcond=None)
            
            terms = [f"{coeffs[i]}*x{i+1}" for i in range(X.shape[1])]
            terms.append(str(coeffs[-1]))
            expression = " + ".join(terms)
            predictions = (A @ coeffs).tolist()

        # Clean up temporary file
        if os.path.exists(temp_file):
            try:
                os.remove(temp_file)
            except OSError:
                pass

        return {
            "expression": expression,
            "predictions": predictions,
            "details": {}
        }
