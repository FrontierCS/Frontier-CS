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
        Solves the symbolic regression problem using PySR.
        
        Args:
            X: Feature matrix of shape (n, 2)
            y: Target values of shape (n,)

        Returns:
            dict with keys "expression", "predictions", "details"
        """
        
        # 1. Data Subsampling for Efficiency
        # Symbolic regression is computationally intensive. Subsampling preserves 
        # the function structure while reducing iteration time.
        n_samples = X.shape[0]
        if n_samples > 2000:
            rng = np.random.RandomState(42)
            indices = rng.choice(n_samples, 2000, replace=False)
            X_fit = X[indices]
            y_fit = y[indices]
        else:
            X_fit = X
            y_fit = y

        # 2. Configure PySRRegressor
        # The Peaks function relies on exponentials of polynomials (Gaussians).
        # We enable '^' (power) in search to efficiently find x^2, y^2 terms.
        # We enable 'exp' as a primary unary operator.
        model = PySRRegressor(
            niterations=60,                   # Balance between search depth and runtime
            binary_operators=["+", "-", "*", "/", "^"],
            unary_operators=["exp", "log", "sin", "cos"],
            populations=20,                   # Parallel populations
            population_size=33,
            maxsize=45,                       # Allow sufficient complexity for Peaks function
            model_selection="best",           # Choose best model based on score (accuracy vs complexity)
            loss="loss(prediction, target) = (prediction - target)^2", # MSE
            verbosity=0,
            progress=False,
            random_state=42,
            procs=8,                          # Utilize all 8 vCPUs
            multithreading=False,             # PySR uses multiprocessing
            timeout_in_seconds=600,           # Safety timeout (10 mins)
            deterministic=True,
            temp_equation_file=True,
            delete_tempfiles=True
        )

        try:
            # 3. Fit Model
            # variable_names=["x1", "x2"] ensures the resulting expression uses required variable names.
            model.fit(X_fit, y_fit, variable_names=["x1", "x2"])

            # 4. Extract Expression
            # model.sympy() returns a sympy object representing the best equation.
            best_expr = model.sympy()
            
            # Convert to string. SymPy renders powers as '**', matching the requirement.
            expression = str(best_expr)
            
            # 5. Generate Predictions
            # Predict on the full original dataset X
            predictions = model.predict(X)
            
            # Handle potential NaNs/Infs in predictions (e.g. from log of negative)
            if np.any(np.isnan(predictions)) or np.any(np.isinf(predictions)):
                predictions = np.nan_to_num(predictions)

        except Exception:
            # 6. Fallback: Linear Regression
            # If PySR fails or times out, return a baseline linear model.
            x1, x2 = X[:, 0], X[:, 1]
            A = np.column_stack([x1, x2, np.ones_like(x1)])
            # Least squares fit
            coeffs, _, _, _ = np.linalg.lstsq(A, y, rcond=None)
            a, b, c = coeffs
            
            expression = f"{a}*x1 + {b}*x2 + {c}"
            predictions = a * x1 + b * x2 + c

        # Ensure predictions are a list as per spec examples
        if isinstance(predictions, np.ndarray):
            predictions = predictions.tolist()

        return {
            "expression": expression,
            "predictions": predictions,
            "details": {}
        }
