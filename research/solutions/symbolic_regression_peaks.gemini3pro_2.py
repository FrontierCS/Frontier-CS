import numpy as np
import pandas as pd
import sympy
from pysr import PySRRegressor

class Solution:
    def __init__(self, **kwargs):
        pass

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        try:
            # Subsample for efficiency if dataset is large
            n_samples = X.shape[0]
            if n_samples > 2000:
                rng = np.random.default_rng(42)
                indices = rng.choice(n_samples, 2000, replace=False)
                X_train = X[indices]
                y_train = y[indices]
            else:
                X_train = X
                y_train = y

            # Configure PySRRegressor
            # Optimized for Peaks function (exponentials + polynomials)
            # Using 8 vCPUs implicitly via populations and backend
            model = PySRRegressor(
                niterations=100,
                binary_operators=["+", "-", "*", "/", "^"],
                unary_operators=["sin", "cos", "exp", "log"],
                populations=16,
                population_size=40,
                maxsize=50,
                timeout_in_seconds=300,
                verbosity=0,
                progress=False,
                random_state=42,
                temp_equation_file=True,
                model_selection="best",
            )

            # Fit model
            model.fit(X_train, y_train, variable_names=["x1", "x2"])

            # Retrieve best expression
            best_expr = model.sympy()
            expression = str(best_expr)

            # Predict on full dataset
            predictions = model.predict(X)

            return {
                "expression": expression,
                "predictions": predictions.tolist(),
                "details": {}
            }

        except Exception as e:
            # Fallback to linear regression if symbolic regression fails
            x1, x2 = X[:, 0], X[:, 1]
            A = np.column_stack([x1, x2, np.ones_like(x1)])
            coeffs, _, _, _ = np.linalg.lstsq(A, y, rcond=None)
            a, b, c = coeffs
            
            expression = f"{a} * x1 + {b} * x2 + {c}"
            predictions = a * x1 + b * x2 + c
            
            return {
                "expression": expression,
                "predictions": predictions.tolist(),
                "details": {"error": str(e)}
            }