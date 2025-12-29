import numpy as np
from pysr import PySRRegressor

class Solution:
    def __init__(self, **kwargs):
        pass

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        """
        Args:
            X: Feature matrix of shape (n, 2)
            y: Target values of shape (n,)

        Returns:
            dict with keys:
              - "expression": str, a Python-evaluable expression using x1, x2
              - "predictions": list/array of length n (optional)
              - "details": dict with optional "complexity" int
        """
        model = PySRRegressor(
            procs=8,
            niterations=100,
            populations=32,
            population_size=50,
            binary_operators=["+", "-", "*", "/", "pow"],
            unary_operators=["sin", "cos"],
            maxsize=30,
            early_stop_condition="stop_if_no_improvement_for(20)",
            temp_equation_file=True,
            random_state=42,
            verbosity=0,
            progress=False,
            # Add a small amount of noise to the data to avoid overly-specialized constants
            # and to regularize the search process slightly.
            denoise=True
        )

        model.fit(X, y, variable_names=["x1", "x2"])

        if len(model.equations_) > 0:
            # Use model.sympy() to get the best expression in sympy format,
            # which correctly uses the provided variable_names.
            best_expr_sympy = model.sympy()
            expression = str(best_expr_sympy)
            
            # Use the model's predict method for consistency.
            predictions = model.predict(X)
        else:
            # Fallback in case PySR fails to find any equations.
            # This returns a constant zero, which is a safe baseline.
            expression = "0.0"
            predictions = np.zeros_like(y)

        return {
            "expression": expression,
            "predictions": predictions.tolist(),
            "details": {}
        }