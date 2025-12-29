import numpy as np
import pandas as pd
from pysr import PySRRegressor
import sympy
import warnings
import os

# Suppress warnings to keep output clean
warnings.filterwarnings("ignore")

class Solution:
    def __init__(self, **kwargs):
        pass

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        """
        Solves the symbolic regression problem using PySR.
        Targeting ripple-like functions using trigonometric operators.
        """
        
        # Data handling: Subsample if the dataset is too large for rapid fitting
        # but large enough to capture high-frequency oscillations.
        n_samples = X.shape[0]
        MAX_SAMPLES = 3000
        
        if n_samples > MAX_SAMPLES:
            rng = np.random.RandomState(42)
            indices = rng.choice(n_samples, MAX_SAMPLES, replace=False)
            X_fit = X[indices]
            y_fit = y[indices]
        else:
            X_fit = X
            y_fit = y

        # Configure PySRRegressor
        # Settings tuned for 8 vCPUs and Ripple dataset characteristics
        model = PySRRegressor(
            niterations=100,                  # Sufficient iterations for convergence
            binary_operators=["+", "-", "*", "/"], 
            unary_operators=["sin", "cos", "exp", "log"], # Trigonometric ops are key for ripples
            populations=16,                   # 2 populations per vCPU (8 vCPUs available)
            population_size=40,               # Size of each population
            ncyclesperiteration=500,          # Evolution steps per iteration
            maxsize=40,                       # Allow complex expressions for nested terms
            parsimony=0.001,                  # Low penalty to encourage finding the correct structure
            verbosity=0,                      # Suppress output
            progress=False,                   # Suppress progress bar
            random_state=42,                  # Reproducibility
            procs=8,                          # Use all 8 cores
            model_selection="best",           # Select best model based on accuracy/complexity trade-off
            timeout_in_seconds=300,           # 5 minute timeout safety
            tempdir=os.getcwd(),              # Use current working directory for temp files
            delete_tempfiles=True             # Cleanup
        )

        try:
            # Fit the model
            # variable_names ensure the output string uses x1, x2
            model.fit(X_fit, y_fit, variable_names=["x1", "x2"])

            # Retrieve the best expression found
            # model.sympy() returns a SymPy object, str() converts it to Python expression string
            best_expr = model.sympy()
            expression = str(best_expr)

            # Generate predictions for the full dataset
            predictions = model.predict(X)
            
        except Exception as e:
            # Fallback mechanism if symbolic regression fails (e.g. timeout)
            # Returns mean of target variable
            mean_val = float(np.mean(y))
            expression = str(mean_val)
            predictions = np.full(n_samples, mean_val)

        # Ensure predictions are a list/array as required
        if hasattr(predictions, "tolist"):
            predictions = predictions.tolist()

        return {
            "expression": expression,
            "predictions": predictions,
            "details": {}
        }