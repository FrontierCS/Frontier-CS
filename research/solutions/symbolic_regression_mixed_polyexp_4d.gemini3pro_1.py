import numpy as np
from pysr import PySRRegressor
import sympy

class Solution:
    def __init__(self, **kwargs):
        pass

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        """
        Args:
            X: Feature matrix of shape (n, 4)
            y: Target values of shape (n,)

        Returns:
            dict containing "expression", "predictions", and "details"
        """
        # Configure PySR for symbolic regression
        # Optimized for 8 vCPUs and Mixed PolyExp 4D complexity
        model = PySRRegressor(
            niterations=100,            # Sufficient iterations for convergence
            binary_operators=["+", "-", "*", "/"],
            unary_operators=["sin", "cos", "exp", "log"],
            procs=8,                    # Use all 8 vCPUs
            populations=8,              # One population per core
            population_size=50,         # Population size
            ncyclesperiteration=500,    # Inner evolution loop
            maxsize=45,                 # Allow complex expressions for 4D
            model_selection="best",     # specific "best" strategy (accuracy vs complexity)
            loss="L2DistLoss()",        # Minimize MSE
            temp_equation_file=True,    # Use temp files to keep directory clean
            verbosity=0,                # Silent execution
            progress=False,             # Disable progress bar
            random_state=42,            # Reproducibility
            deterministic=True,         # Deterministic behavior
            timeout_in_seconds=600,     # Time limit safety
        )

        try:
            # Fit the model
            # variable_names ensures the output expression uses x1, x2, x3, x4
            model.fit(X, y, variable_names=["x1", "x2", "x3", "x4"])

            # Extract the best symbolic expression
            best_expr = model.sympy()
            expression = str(best_expr)

            # Generate predictions using the fitted model
            predictions = model.predict(X)

        except Exception:
            # Fallback strategy: Linear Regression if symbolic regression fails
            # This ensures the function always returns a valid result
            X_bias = np.column_stack([X, np.ones(len(X))])
            coeffs, _, _, _ = np.linalg.lstsq(X_bias, y, rcond=None)
            
            # Construct a linear expression string
            terms = [f"({coeffs[i]} * x{i+1})" for i in range(4)]
            terms.append(str(coeffs[4]))
            expression = " + ".join(terms)
            
            # Compute predictions
            predictions = X_bias @ coeffs

        # Ensure predictions are in list format
        if isinstance(predictions, np.ndarray):
            predictions = predictions.tolist()

        return {
            "expression": expression,
            "predictions": predictions,
            "details": {}
        }