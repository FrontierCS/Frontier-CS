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
        Solves the symbolic regression problem using PySR.
        Targeting the McCormick function structure.
        """
        # Create a temporary directory to store PySR's intermediate files
        with tempfile.TemporaryDirectory() as tmpdir:
            equation_file = os.path.join(tmpdir, "hall_of_fame.csv")
            
            # Initialize PySRRegressor with parameters optimized for the environment and problem
            # Using 8 processes to match the 8 vCPUs
            # Restricting operators to those likely needed for McCormick (Trig + Poly)
            model = PySRRegressor(
                niterations=40,
                binary_operators=["+", "-", "*"],
                unary_operators=["sin", "cos"],
                populations=16,
                population_size=40,
                maxsize=45,
                verbosity=0,
                progress=False,
                random_state=42,
                tempdir=tmpdir,
                equation_file=equation_file,
                procs=8,
                model_selection="best",
            )
            
            # Subsample training data if dataset is large to ensure completion within time limits
            n_samples = X.shape[0]
            if n_samples > 2000:
                rng = np.random.RandomState(42)
                indices = rng.choice(n_samples, 2000, replace=False)
                X_train = X[indices]
                y_train = y[indices]
            else:
                X_train = X
                y_train = y
            
            # Fit the symbolic regression model
            # Ensure variable names match the required output format
            model.fit(X_train, y_train, variable_names=["x1", "x2"])
            
            # Retrieve the best expression found as a sympy object
            best_expr = model.sympy()
            
            # Convert sympy expression to a Python-evaluable string
            expression = str(best_expr)
            
            # Generate predictions for the full dataset using the fitted model
            predictions = model.predict(X)
            
            return {
                "expression": expression,
                "predictions": predictions.tolist(),
                "details": {}
            }