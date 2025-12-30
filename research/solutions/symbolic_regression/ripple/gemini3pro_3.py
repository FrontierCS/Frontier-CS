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
        """
        try:
            # Configure PySRRegressor
            # Utilizing 8 vCPUs with specific population settings for efficiency
            model = PySRRegressor(
                niterations=40,
                binary_operators=["+", "-", "*", "/"],
                unary_operators=["sin", "cos", "exp", "log"],
                population_size=40,
                populations=16,
                maxsize=45,
                procs=8,
                multiprocessing=True,
                verbosity=0,
                progress=False,
                random_state=42,
                deterministic=True,
                model_selection="best",
                temp_equation_file=None,
                delete_tempfiles=True
            )

            # Fit the model to the data
            # variable_names are set to ensure the output expression uses x1, x2
            model.fit(X, y, variable_names=["x1", "x2"])

            # Retrieve the best symbolic expression found
            best_expr = model.sympy()
            expression = str(best_expr)

            # Generate predictions
            predictions = model.predict(X)
            
            # Convert predictions to list if numpy array
            if isinstance(predictions, np.ndarray):
                predictions = predictions.tolist()

            return {
                "expression": expression,
                "predictions": predictions,
                "details": {}
            }

        except Exception as e:
            # Robust fallback: Linear Regression using numpy
            # Solves y = w1*x1 + w2*x2 + b
            N = len(y)
            A = np.column_stack([X, np.ones(N)])
            w, _, _, _ = np.linalg.lstsq(A, y, rcond=None)
            
            # w contains [slope_x1, slope_x2, intercept]
            expression = f"({w[0]}) * x1 + ({w[1]}) * x2 + ({w[2]})"
            predictions = (A @ w).tolist()

            return {
                "expression": expression,
                "predictions": predictions,
                "details": {"fallback_error": str(e)}
            }