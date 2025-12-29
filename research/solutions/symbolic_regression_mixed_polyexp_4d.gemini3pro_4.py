import numpy as np
from pysr import PySRRegressor
import sympy
import warnings

class Solution:
    def __init__(self, **kwargs):
        pass

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        """
        Solves the symbolic regression problem using PySRRegressor.
        """
        # Suppress warnings
        warnings.filterwarnings("ignore")
        
        # Define variable names corresponding to the 4 input features
        variable_names = ["x1", "x2", "x3", "x4"]
        
        # Configure PySRRegressor
        # Optimized for the available 8 vCPUs (procs=8)
        # Using niterations and timeout to ensure completion within reasonable time
        model = PySRRegressor(
            niterations=200,
            binary_operators=["+", "-", "*", "/"],
            unary_operators=["exp", "sin", "cos", "log"],
            populations=32,          # 4 populations per core
            population_size=50,
            maxsize=40,              # Allow enough complexity for 4D PolyExp interactions
            ncycles_per_iteration=500,
            model_selection="best",  # Selects best expression based on accuracy/complexity trade-off
            loss="loss(prediction, target) = (prediction - target)^2",
            verbosity=0,
            progress=False,
            random_state=42,
            procs=8,                 # Use all 8 vCPUs
            multithreading=False,    # Use multiprocessing (safer/faster for Julia backend)
            timeout_in_seconds=240,  # Safety timeout (4 minutes)
            deterministic=True
        )
        
        try:
            # Fit the model to the data
            model.fit(X, y, variable_names=variable_names)
            
            # Extract the best symbolic expression as a SymPy object
            best_expr = model.sympy()
            # Convert to string for output
            expression = str(best_expr)
            
            # Generate predictions
            predictions = model.predict(X)
            
        except Exception:
            # Fallback mechanism: Linear Regression
            # Used if PySR fails to converge or runs into runtime issues
            
            # Prepare data for linear regression (add intercept)
            X_aug = np.column_stack([X, np.ones(X.shape[0])])
            
            # Solve using least squares
            coeffs, _, _, _ = np.linalg.lstsq(X_aug, y, rcond=None)
            
            # Construct the linear expression string
            terms = [f"({coeffs[i]}*{var})" for i, var in enumerate(variable_names)]
            terms.append(str(coeffs[-1])) # Add intercept
            expression = " + ".join(terms)
            
            # Compute predictions
            predictions = X_aug @ coeffs

        return {
            "expression": expression,
            "predictions": predictions.tolist(),
            "details": {}
        }