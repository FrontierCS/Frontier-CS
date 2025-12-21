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
        Finds a closed-form symbolic expression f(x1, x2, x3, x4) predicting y.
        """
        # Define variable names as per specification
        variable_names = ["x1", "x2", "x3", "x4"]

        # Configure PySRRegressor
        # Optimized settings for 4D Mixed PolyExp dataset on 8 vCPUs
        model = PySRRegressor(
            niterations=80,             # Sufficient iterations for convergence
            binary_operators=["+", "-", "*", "/"], # Basic arithmetic (powers via multiplication)
            unary_operators=["sin", "cos", "exp", "log"], # Required functions
            populations=16,             # Parallel populations (approx 2 per core)
            population_size=40,         # Individuals per population
            maxsize=45,                 # Allow higher complexity for mixed terms
            model_selection="best",     # Balance accuracy and complexity
            verbosity=0,                # Silent mode
            progress=False,             # No progress bar
            random_state=42,            # Reproducibility
            procs=8,                    # Utilize all 8 vCPUs
            multithreading=False,       # Use multiprocessing for stability
            temp_equation_file=False,   # Disable intermediate file logging
            delete_tempfiles=True,      # Cleanup temp files
            deterministic=True,         # Deterministic evolution
            timeout_in_seconds=600      # Safety timeout
        )

        try:
            # Fit the model to the data
            model.fit(X, y, variable_names=variable_names)
            
            # Retrieve the best expression as a SymPy object and convert to string
            best_eqn = model.sympy()
            expression = str(best_eqn)
            
            # Generate predictions
            predictions = model.predict(X)
            
            # Ensure predictions are a standard list
            if isinstance(predictions, np.ndarray):
                predictions = predictions.tolist()
                
        except Exception:
            # Fallback: Linear Regression
            # In case PySR fails (e.g., environment issues), return a valid linear baseline
            
            # Prepare data with intercept
            X_aug = np.column_stack([X, np.ones(X.shape[0])])
            
            # Solve least squares
            coeffs, _, _, _ = np.linalg.lstsq(X_aug, y, rcond=None)
            
            # formatting expression: a*x1 + b*x2 + ... + intercept
            terms = [f"({coeffs[i]}*x{i+1})" for i in range(4)]
            terms.append(f"{coeffs[4]}")
            expression = " + ".join(terms)
            
            # Calculate predictions
            predictions = (X_aug @ coeffs).tolist()

        return {
            "expression": expression,
            "predictions": predictions,
            "details": {}
        }
