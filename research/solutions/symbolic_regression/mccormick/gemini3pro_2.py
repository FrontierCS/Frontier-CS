import numpy as np
import pandas as pd
import sympy as sp
from pysr import PySRRegressor
import os
import warnings

class Solution:
    def __init__(self, **kwargs):
        pass

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        """
        Solves the symbolic regression problem for the McCormick dataset.
        Uses PySRRegressor with a fallback to linear regression on expected basis functions.
        """
        warnings.filterwarnings("ignore")
        
        # Subsample dataset if too large to ensure efficient search
        n_samples = X.shape[0]
        if n_samples > 2000:
            rng = np.random.RandomState(42)
            indices = rng.choice(n_samples, 2000, replace=False)
            X_train = X[indices]
            y_train = y[indices]
        else:
            X_train = X
            y_train = y

        # Define a temporary file for equations to prevent conflicts
        pid = os.getpid()
        eq_file = f"equations_{pid}.csv"

        try:
            # Configure PySR
            # McCormick function involves polynomial and trigonometric terms
            # Limiting operators to +, -, *, sin, cos speeds up convergence
            model = PySRRegressor(
                niterations=40,
                binary_operators=["+", "-", "*"],
                unary_operators=["sin", "cos"],
                populations=8,
                population_size=40,
                maxsize=40,
                verbosity=0,
                progress=False,
                random_state=42,
                procs=8,
                model_selection="best",
                equation_file=eq_file,
                temp_equation_file=False
            )

            # Fit the model
            model.fit(X_train, y_train, variable_names=["x1", "x2"])
            
            # Extract best expression
            best_expr = model.sympy()
            expression = str(best_expr)
            
            # Generate predictions
            predictions = model.predict(X)
            
            # Cleanup
            if os.path.exists(eq_file):
                os.remove(eq_file)
                
            # Check for validity
            if np.any(np.isnan(predictions)) or np.any(np.isinf(predictions)):
                raise ValueError("Invalid predictions from PySR")

            return {
                "expression": expression,
                "predictions": predictions.tolist(),
                "details": {}
            }

        except Exception as e:
            # Fallback strategy: Linear Regression on McCormick basis functions
            # The McCormick function is: sin(x+y) + (x-y)^2 - 1.5x + 2.5y + 1
            # We expand this into a basis set to ensure a good fit if symbolic search fails.
            
            if os.path.exists(eq_file):
                os.remove(eq_file)
                
            x1 = X[:, 0]
            x2 = X[:, 1]
            
            # Construct basis features
            bases = [
                np.ones_like(x1),
                x1,
                x2,
                x1**2,
                x2**2,
                x1*x2,
                np.sin(x1 + x2),
                np.cos(x1 + x2)
            ]
            base_names = ["1", "x1", "x2", "x1**2", "x2**2", "x1*x2", "sin(x1 + x2)", "cos(x1 + x2)"]
            
            # Fit coefficients
            A = np.column_stack(bases)
            coeffs, _, _, _ = np.linalg.lstsq(A, y, rcond=None)
            
            # Construct expression string
            terms = []
            for c, name in zip(coeffs, base_names):
                if abs(c) > 1e-5:
                    if name == "1":
                        terms.append(f"({c:.6f})")
                    else:
                        terms.append(f"({c:.6f} * {name})")
            
            if not terms:
                expression = "0"
            else:
                expression = " + ".join(terms)
            
            # Compute predictions
            predictions = A @ coeffs
            
            return {
                "expression": expression,
                "predictions": predictions.tolist(),
                "details": {"fallback": True, "error": str(e)}
            }