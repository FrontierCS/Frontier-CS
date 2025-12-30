import numpy as np
import pandas as pd
import sympy
from pysr import PySRRegressor
import warnings

# Suppress warnings to keep output clean
warnings.filterwarnings("ignore")

class Solution:
    def __init__(self, **kwargs):
        pass

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        """
        Solves the symbolic regression problem for the Mixed PolyExp 4D dataset.
        """
        # Ensure inputs are standard numpy arrays
        X = np.array(X, dtype=np.float32)
        y = np.array(y, dtype=np.float32)
        n_samples = X.shape[0]

        # Subsample data if too large to ensure execution within time limits
        # Using 2000 points is usually sufficient for symbolic regression to find the structure
        if n_samples > 2000:
            rng = np.random.RandomState(42)
            indices = rng.choice(n_samples, 2000, replace=False)
            X_fit = X[indices]
            y_fit = y[indices]
        else:
            X_fit = X
            y_fit = y

        try:
            # Configure PySRRegressor
            # Optimized for 8 vCPUs and the specific problem type (Poly + Exp)
            model = PySRRegressor(
                niterations=60,                # Sufficient iterations for convergence
                binary_operators=["+", "-", "*", "/", "^"],
                unary_operators=["exp", "sin", "cos", "log"],
                populations=16,                # 2 populations per CPU core
                population_size=50,
                maxsize=45,                    # Allow for enough complexity (4D + interactions)
                procs=8,
                multiprocessing=True,
                denoise=False,
                optimizer_algorithm="Nelder-Mead",
                optimizer_nrestarts=3,
                verbosity=0,
                progress=False,
                random_state=42,
                parsimony_coefficient=0.001,   # Slight penalty to prefer simpler equations
                model_selection="best",        # Select best model based on score (accuracy vs complexity)
                constraints={
                    "^": ((-1, 3), (-1, 3)),   # Limit power complexity to avoid overfitting
                },
                complexity_of_operators={
                    "exp": 2, "log": 3, "sin": 3, "cos": 3, "^": 1
                },
                temp_equation_file=False,
                delete_tempfiles=True
            )

            # Fit the model
            model.fit(X_fit, y_fit, variable_names=["x1", "x2", "x3", "x4"])

            # Retrieve the best symbolic expression
            best_sympy = model.sympy()
            expression = str(best_sympy)

            # Generate predictions on the full dataset
            predictions = model.predict(X)

            # Safety check for invalid predictions
            if np.any(np.isnan(predictions)) or np.any(np.isinf(predictions)):
                raise ValueError("PySR predictions contain NaN or Inf.")

        except Exception:
            # Fallback to Linear Regression if symbolic regression fails or times out
            # Construct design matrix with bias
            X_bias = np.c_[X, np.ones(n_samples)]
            
            # Least squares solution
            coeffs, _, _, _ = np.linalg.lstsq(X_bias, y, rcond=None)
            
            # Construct linear expression string
            terms = []
            for i, var in enumerate(["x1", "x2", "x3", "x4"]):
                terms.append(f"({coeffs[i]} * {var})")
            terms.append(str(coeffs[4]))
            expression = " + ".join(terms)
            
            # Compute predictions
            predictions = X_bias @ coeffs

        # Ensure prediction format is a list
        return {
            "expression": expression,
            "predictions": predictions.tolist(),
            "details": {}
        }