import numpy as np
import pandas as pd
import sympy
import os
import warnings
from pysr import PySRRegressor

# Suppress warnings to keep output clean
warnings.filterwarnings("ignore")

class Solution:
    def __init__(self, **kwargs):
        pass

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        """
        Solves the symbolic regression problem for the Ripple dataset.
        Attempts to find a symbolic expression using PySR, with a quadratic regression fallback.
        """
        # Ensure inputs are clean (handle NaNs/Infs)
        X = np.nan_to_num(X)
        y = np.nan_to_num(y)
        
        # Default initialization
        expression = "0"
        predictions = np.zeros(len(y))
        
        # Attempt Symbolic Regression
        try:
            # Configure PySRRegressor
            # Optimized for 8 vCPUs and the specific nature of the Ripple dataset 
            # (polynomial amplitude modulation + trigonometric oscillations)
            model = PySRRegressor(
                niterations=50,                  # Sufficient iterations for convergence
                binary_operators=["+", "-", "*", "/"],
                unary_operators=["sin", "cos", "exp"], # exp/sin/cos cover the ripple function components
                maxsize=40,                      # Allow complexity for nested modulation
                populations=20,                  # Diversity in population
                population_size=40,
                model_selection="best",          # Balance accuracy and complexity
                loss="L2DistLoss()",
                
                # compute settings
                procs=8,                         # Use all available vCPUs
                multithreading=False,            # Multiprocessing is generally preferred for PySR
                verbosity=0,
                progress=False,
                random_state=42,
                
                # file handling
                temp_equation_file=f"pysr_eq_{os.getpid()}.csv",
                delete_tempfiles=True
            )
            
            # Fit model with specified variable names
            model.fit(X, y, variable_names=["x1", "x2"])
            
            # Retrieve best expression
            best_expr = model.sympy()
            
            if best_expr is not None:
                expression = str(best_expr)
                predictions = model.predict(X)
                
                return {
                    "expression": expression,
                    "predictions": predictions.tolist(),
                    "details": {"method": "pysr"}
                }
                
        except Exception:
            # Proceed to fallback on any PySR failure
            pass
            
        # Fallback: Quadratic Regression
        # Fits y = c0 + c1*x1 + c2*x2 + c3*x1^2 + c4*x2^2 + c5*x1*x2
        # This captures the polynomial modulation aspect even if oscillations are missed.
        try:
            x1 = X[:, 0]
            x2 = X[:, 1]
            
            # Construct Design Matrix
            A = np.column_stack([
                np.ones_like(x1),
                x1,
                x2,
                x1**2,
                x2**2,
                x1*x2
            ])
            
            # Least Squares Solve
            coeffs, _, _, _ = np.linalg.lstsq(A, y, rcond=None)
            
            # Generate Predictions
            predictions = A @ coeffs
            
            # Format Expression String
            def fmt(v): return f"{v:.6f}"
            c = coeffs
            terms = [
                fmt(c[0]),
                f"{fmt(c[1])}*x1",
                f"{fmt(c[2])}*x2",
                f"{fmt(c[3])}*x1**2",
                f"{fmt(c[4])}*x2**2",
                f"{fmt(c[5])}*x1*x2"
            ]
            expression = " + ".join(terms)
            
        except Exception:
            # Ultimate Fallback: Mean Prediction
            mean_val = np.mean(y)
            expression = str(mean_val)
            predictions = np.full_like(y, mean_val)

        return {
            "expression": expression,
            "predictions": predictions.tolist(),
            "details": {"method": "fallback"}
        }
