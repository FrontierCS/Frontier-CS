import numpy as np
import pandas as pd
import sympy
from pysr import PySRRegressor

class Solution:
    def __init__(self, **kwargs):
        pass

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        """
        Solves the Symbolic Regression problem on the Peaks dataset using PySR.
        """
        # Subsample dataset if too large to ensure timely execution
        n_samples = X.shape[0]
        train_limit = 2000
        if n_samples > train_limit:
            rng = np.random.RandomState(42)
            indices = rng.choice(n_samples, train_limit, replace=False)
            X_train = X[indices]
            y_train = y[indices]
        else:
            X_train = X
            y_train = y

        # Configure PySRRegressor
        # Optimized for 8 vCPUs and peaks-like functions (exponentials, polynomials)
        model = PySRRegressor(
            niterations=200,  # Adequate iterations for convergence
            binary_operators=["+", "-", "*", "/", "^"],
            unary_operators=["exp", "sin", "cos", "log"],
            # Prevent unrealistic nesting of transcendental functions
            nested_constraints={
                "exp": {"exp": 0, "log": 0, "sin": 0, "cos": 0},
                "log": {"exp": 0, "log": 0, "sin": 0, "cos": 0},
                "sin": {"sin": 0, "cos": 0, "exp": 0, "log": 0},
                "cos": {"sin": 0, "cos": 0, "exp": 0, "log": 0},
            },
            maxsize=50,  # Allow complex expressions typical of Peaks function
            populations=24,  # Parallel populations (approx 3 per core)
            population_size=40,
            ncycles_per_iteration=500,
            model_selection="best",
            loss="L2DistLoss",
            procs=8,
            multiprocessing=True,
            turbo=True,
            verbosity=0,
            progress=False,
            random_state=42,
            deterministic=True,
            timeout_in_seconds=300,  # 5 minute timeout for fitting
            temp_equation_file=None,
            delete_tempfiles=True,
        )

        expression = "0"
        predictions = np.zeros(n_samples)

        try:
            # Fit the model to the training data
            model.fit(X_train, y_train, variable_names=["x1", "x2"])

            # Retrieve the best symbolic expression as a string
            sympy_expr = model.sympy()
            expression = str(sympy_expr)

            # Generate predictions on the full dataset
            predictions = model.predict(X)
            
            # Handle potential numerical instabilities (NaN/Inf)
            predictions = np.nan_to_num(predictions, nan=0.0, posinf=0.0, neginf=0.0)

        except Exception:
            # Fallback to Linear Regression if PySR fails
            A = np.column_stack([X[:, 0], X[:, 1], np.ones(n_samples)])
            coeffs, _, _, _ = np.linalg.lstsq(A, y, rcond=None)
            a, b, c = coeffs
            expression = f"{a}*x1 + {b}*x2 + {c}"
            predictions = A @ coeffs

        return {
            "expression": expression,
            "predictions": predictions.tolist(),
            "details": {}
        }