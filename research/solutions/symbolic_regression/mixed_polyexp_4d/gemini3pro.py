import numpy as np
import pandas as pd
import sympy
from pysr import PySRRegressor

class Solution:
    def __init__(self, **kwargs):
        self.random_state = kwargs.get('random_state', 42)

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        """
        Solves the symbolic regression problem using PySR.
        Falls back to linear regression if symbolic regression fails.
        """
        try:
            # Initialize PySRRegressor
            # Using configurations optimized for 8 vCPUs and the problem complexity
            model = PySRRegressor(
                niterations=100,
                binary_operators=["+", "-", "*", "/", "^"],
                unary_operators=["sin", "cos", "exp", "log"],
                model_selection="best",
                maxsize=40,
                timeout_in_seconds=300,  # 5 minutes max
                random_state=self.random_state,
                verbosity=0,
                progress=False,
                populations=30,  # ~4x core count for better diversity
                deterministic=True
            )

            # Fit the model
            model.fit(X, y, variable_names=["x1", "x2", "x3", "x4"])

            # Retrieve the best expression found
            # PySR returns a sympy object which we convert to string
            best_expr = model.sympy()
            expression = str(best_expr)

            # Compute predictions using the fitted model
            predictions = model.predict(X)

            # Extract complexity if available, else 0
            complexity = 0
            if hasattr(model, 'equations_') and model.equations_ is not None:
                try:
                    # Get complexity of the selected model (score max or best selection)
                    best_idx = model.equations_['score'].idxmax()
                    complexity = int(model.equations_.loc[best_idx, 'complexity'])
                except:
                    pass

            return {
                "expression": expression,
                "predictions": predictions.tolist(),
                "details": {
                    "complexity": complexity
                }
            }

        except Exception as e:
            # Fallback to linear regression in case of any failure
            return self._linear_fallback(X, y)

    def _linear_fallback(self, X: np.ndarray, y: np.ndarray) -> dict:
        # Add bias term
        n_samples = X.shape[0]
        X_aug = np.hstack([X, np.ones((n_samples, 1))])

        # Least squares fit
        coeffs, _, _, _ = np.linalg.lstsq(X_aug, y, rcond=None)

        # Construct linear expression string
        terms = []
        for i in range(4):
            terms.append(f"({coeffs[i]} * x{i+1})")
        terms.append(f"({coeffs[4]})")  # Bias

        expression = " + ".join(terms)
        predictions = X_aug @ coeffs

        return {
            "expression": expression,
            "predictions": predictions.tolist(),
            "details": {"fallback": True, "complexity": 5}
        }