import numpy as np
import pandas as pd
import sympy
from pysr import PySRRegressor

class Solution:
    def __init__(self, **kwargs):
        pass

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        try:
            # Configure PySRRegressor
            # Optimized for Peaks dataset: includes exp/log/trig and power operators
            # 8 vCPUs -> procs=8
            model = PySRRegressor(
                niterations=50,
                binary_operators=["+", "-", "*", "/", "^"],
                unary_operators=["exp", "sin", "cos", "log"],
                populations=16,
                population_size=40,
                maxsize=50,
                verbosity=0,
                progress=False,
                random_state=42,
                procs=8,
                multithreading=False,
                model_selection="best",
                temp_equation_file=True,
                delete_tempfiles=True
            )

            # Fit model with specified variable names
            model.fit(X, y, variable_names=["x1", "x2"])

            # Retrieve best expression and predictions
            # PySR's sympy() returns a SymPy expression object
            # str(expr) converts it to Python-compatible string (e.g. ** for power)
            best_expr = model.sympy()
            expression = str(best_expr)
            predictions = model.predict(X)

        except Exception:
            # Fallback to linear regression if symbolic regression fails
            x1, x2 = X[:, 0], X[:, 1]
            A = np.column_stack([x1, x2, np.ones_like(x1)])
            coeffs, _, _, _ = np.linalg.lstsq(A, y, rcond=None)
            a, b, c = coeffs
            expression = f"{a}*x1 + {b}*x2 + {c}"
            predictions = a * x1 + b * x2 + c

        return {
            "expression": expression,
            "predictions": predictions.tolist(),
            "details": {}
        }