import numpy as np
import sympy
from pysr import PySRRegressor

class Solution:
    def __init__(self, **kwargs):
        pass

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        """
        Solves the symbolic regression problem for the McCormick dataset using PySR.
        
        Args:
            X: Feature matrix of shape (n, 2)
            y: Target values of shape (n,)
            
        Returns:
            dict with "expression", "predictions", "details"
        """
        # Configure PySRRegressor with parameters optimized for the McCormick function structure
        # (trigonometric and polynomial terms) and the evaluation environment (8 vCPUs).
        model = PySRRegressor(
            niterations=80,                  # Sufficient iterations to find the structure
            binary_operators=["+", "-", "*"],# Division is not strictly necessary for McCormick
            unary_operators=["sin", "cos"],  # Required for the sine term
            populations=16,                  # Utilize available vCPUs
            population_size=40,
            maxsize=40,                      # Allow complexity for expanded polynomial terms
            procs=8,                         # Multiprocessing
            verbosity=0,
            progress=False,
            random_state=42,
            parsimony_coefficient=0.001,     # Slight penalty for complexity
            model_selection="best",          # Balance accuracy and complexity
        )

        # Fit the model
        # Explicitly define variable names to match output requirements (x1, x2)
        model.fit(X, y, variable_names=["x1", "x2"])

        # Retrieve the best symbolic expression
        best_expr = model.sympy()
        expression = str(best_expr)

        # Generate predictions using the fitted model
        predictions = model.predict(X)

        return {
            "expression": expression,
            "predictions": predictions.tolist(),
            "details": {}
        }
