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
        # The problem description suggests a complex function with exponential terms,
        # so we configure PySR for a more intensive search.
        model = PySRRegressor(
            # Increased search effort for a complex problem
            niterations=50,
            populations=24,
            population_size=40,
            
            # All allowed operators, especially 'exp' and '**' which are likely key
            binary_operators=["+", "-", "*", "/", "**"],
            unary_operators=["exp", "cos", "sin", "log"],
            
            # Allow for reasonably complex expressions
            maxsize=30,
            
            # Slightly encourage simpler expressions to manage complexity score
            parsimony=0.005,
            
            # Utilize all available CPU cores in the environment
            procs=8,
            
            # Select the best model based on the score (accuracy vs complexity)
            model_selection="best",
            
            # Add constraints to prevent redundant or unstable combinations
            nested_constraints={
                "log": {"exp": 0}, "exp": {"log": 0},
                "sin": {"sin": 0, "cos": 0}, "cos": {"sin": 0, "cos": 0},
            },
            
            # Gradually increase maxsize to find good building blocks first
            warmup_maxsize_by=0.5,
            
            # For reproducibility and clean output
            random_state=42,
            verbosity=0,
            progress=False,
        )

        try:
            model.fit(X, y, variable_names=["x1", "x2"])

            # Check if PySR found any valid equations
            if model.equations_ is not None and len(model.equations_) > 0:
                best_expr_sympy = model.sympy()
                expression = str(best_expr_sympy)
                predictions = model.predict(X)

                return {
                    "expression": expression,
                    "predictions": predictions.tolist(),
                    "details": {}
                }
            else:
                # Fallback if no equations are found
                return self._fallback_solution(X, y)

        except Exception:
            # Fallback in case of any unexpected errors during PySR execution
            return self._fallback_solution(X, y)

    def _fallback_solution(self, X: np.ndarray, y: np.ndarray) -> dict:
        """
        A simple linear regression model as a robust fallback.
        """
        x1, x2 = X[:, 0], X[:, 1]
        A = np.c_[x1, x2, np.ones_like(x1)]
        
        try:
            coeffs, _, _, _ = np.linalg.lstsq(A, y, rcond=None)
            a, b, c = coeffs
        except np.linalg.LinAlgError:
            # Handle cases where least squares might fail
            a, b, c = 0.0, 0.0, np.mean(y)

        expression = f"{a:.8f}*x1 + {b:.8f}*x2 + {c:.8f}"
        predictions = a * x1 + b * x2 + c

        return {
            "expression": expression,
            "predictions": predictions.tolist(),
            "details": {"fallback": True}
        }
