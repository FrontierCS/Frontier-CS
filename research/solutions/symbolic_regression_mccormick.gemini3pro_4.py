import numpy as np
from pysr import PySRRegressor

class Solution:
    def __init__(self, **kwargs):
        pass

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        try:
            # Configure PySRRegressor for the McCormick dataset
            # Using parameters balanced for the 8 vCPU environment
            model = PySRRegressor(
                niterations=50,
                binary_operators=["+", "-", "*", "/"],
                unary_operators=["sin", "cos", "exp", "log"],
                populations=16,
                population_size=40,
                maxsize=35,
                model_selection="best",
                verbosity=0,
                progress=False,
                random_state=42,
            )
            
            # Fit the model specifying variable names to match output requirements
            model.fit(X, y, variable_names=["x1", "x2"])
            
            # Retrieve the best symbolic expression
            best_expr = model.sympy()
            expression = str(best_expr)
            
            # Generate predictions
            predictions = model.predict(X)
            
            # Ensure predictions is a list
            if hasattr(predictions, "tolist"):
                predictions = predictions.tolist()

            return {
                "expression": expression,
                "predictions": predictions,
                "details": {}
            }
            
        except Exception:
            # Fallback to Linear Regression if symbolic regression fails
            x1, x2 = X[:, 0], X[:, 1]
            A = np.column_stack([x1, x2, np.ones_like(x1)])
            coeffs, _, _, _ = np.linalg.lstsq(A, y, rcond=None)
            a, b, c = coeffs
            
            expression = f"{a}*x1 + {b}*x2 + {c}"
            predictions = (a * x1 + b * x2 + c).tolist()
            
            return {
                "expression": expression,
                "predictions": predictions,
                "details": {"fallback": True}
            }