import numpy as np
import sympy
from pysr import PySRRegressor
import tempfile
import os

class Solution:
    def __init__(self, **kwargs):
        pass

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        """
        Symbolic regression solver using PySR.
        """
        # Define variable names as required
        variable_names = ["x1", "x2"]

        # Subsample data if dataset is large to maintain efficiency
        # The Peaks function structure can typically be resolved with ~2000 points
        n_samples = X.shape[0]
        if n_samples > 3000:
            rng = np.random.RandomState(42)
            indices = rng.choice(n_samples, 3000, replace=False)
            X_fit = X[indices]
            y_fit = y[indices]
        else:
            X_fit = X
            y_fit = y

        # Use a temporary directory for PySR's intermediate files
        with tempfile.TemporaryDirectory() as tmpdir:
            equation_file = os.path.join(tmpdir, "hall_of_fame.csv")

            # Configure PySRRegressor
            # Optimized for 8 vCPUs and complexity of the Peaks function
            model = PySRRegressor(
                niterations=60,               # Sufficient iterations for convergence on this complexity
                binary_operators=["+", "-", "*", "/", "^"],
                unary_operators=["exp", "sin", "cos", "log"],
                populations=16,               # Parallel populations (2x vCPUs)
                population_size=40,           # Size per population
                maxsize=50,                   # Allow complex expressions (Peaks function is ~40-50 nodes)
                verbosity=0,
                progress=False,
                random_state=42,
                procs=8,                      # Utilize all 8 vCPUs
                multiprocessing=True,
                equation_file=equation_file,
                model_selection="best",       # Select best model based on score/complexity
                loss="squared_error"
            )

            try:
                # Fit the model to the training data
                model.fit(X_fit, y_fit, variable_names=variable_names)

                # Retrieve the best expression found as a SymPy object
                best_expr = model.sympy()
                
                # Convert SymPy expression to Python string
                # SymPy automatically handles operator precedence and converts ^ to **
                expression = str(best_expr)

                # Generate predictions for the full dataset using the fitted model
                predictions = model.predict(X)

                return {
                    "expression": expression,
                    "predictions": predictions.tolist(),
                    "details": {}
                }

            except Exception as e:
                # Fallback to linear regression if symbolic regression fails
                x1, x2 = X[:, 0], X[:, 1]
                # Design matrix for linear regression: [x1, x2, 1]
                A = np.column_stack([x1, x2, np.ones_like(x1)])
                coeffs, _, _, _ = np.linalg.lstsq(A, y, rcond=None)
                a, b, c = coeffs

                # Fallback expression
                expression = f"({a})*x1 + ({b})*x2 + ({c})"
                predictions = a * x1 + b * x2 + c

                return {
                    "expression": expression,
                    "predictions": predictions.tolist(),
                    "details": {"error": str(e), "fallback": True}
                }
