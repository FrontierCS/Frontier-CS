import numpy as np
import pandas as pd
import sympy
from pysr import PySRRegressor

class Solution:
    def __init__(self, **kwargs):
        pass

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        # Configure PySRRegressor for symbolic regression
        # Utilizing available 8 vCPUs with procs=8 and populations=24 (3 per core)
        model = PySRRegressor(
            niterations=50,
            binary_operators=["+", "-", "*", "/"],
            unary_operators=["sin", "cos", "exp", "log"],
            populations=24,
            population_size=33,
            maxsize=30,
            procs=8,
            multiprocessing=True,
            model_selection="best",
            verbosity=0,
            progress=False,
            random_state=42,
        )

        # Fit the model to the data
        # variable_names ensures the output expression uses "x1" and "x2"
        model.fit(X, y, variable_names=["x1", "x2"])

        # Extract the best expression as a string
        try:
            best_expr = model.sympy()
            expression = str(best_expr)
        except Exception:
            # Fallback if expression extraction fails
            expression = "0"

        # Generate predictions using the fitted model
        try:
            predictions = model.predict(X)
            # Ensure predictions is a flat 1D array/list
            if isinstance(predictions, np.ndarray):
                predictions = predictions.flatten()
            else:
                predictions = np.array(predictions).flatten()
        except Exception:
            # Fallback for predictions
            predictions = np.zeros(len(y))

        return {
            "expression": expression,
            "predictions": predictions.tolist(),
            "details": {}
        }