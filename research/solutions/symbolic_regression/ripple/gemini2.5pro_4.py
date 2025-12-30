import numpy as np
from pysr import PySRRegressor

class Solution:
    def __init__(self, **kwargs):
        self.model = PySRRegressor(
            procs=8,
            niterations=60,
            populations=16,
            population_size=40,
            maxsize=35,
            binary_operators=["+", "-", "*", "/", "pow"],
            unary_operators=["sin", "cos", "exp", "log"],
            optimizer_nrestarts=3,
            timeout_in_seconds=300,
            random_state=42,
            verbosity=0,
            progress=False,
        )

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        try:
            self.model.fit(X, y, variable_names=["x1", "x2"])
            
            if self.model.equations_ is not None and not self.model.equations_.empty:
                best_equation = self.model.get_best()
                expression = str(best_equation.sympy_format)
                
                predictions = self.model.predict(X)

                return {
                    "expression": expression,
                    "predictions": predictions.tolist(),
                    "details": {
                        "complexity": int(best_equation.complexity)
                    }
                }
            else:
                return self._fallback_linear(X, y)
        except Exception:
            return self._fallback_linear(X, y)

    def _fallback_linear(self, X: np.ndarray, y: np.ndarray) -> dict:
        x1, x2 = X[:, 0], X[:, 1]
        
        A = np.c_[x1, x2, np.ones_like(x1)]
        
        try:
            coeffs, _, _, _ = np.linalg.lstsq(A, y, rcond=None)
            a, b, c = coeffs
        except np.linalg.LinAlgError:
            a, b, c = 0.0, 0.0, np.mean(y)

        expression = f"{a:.6f}*x1 + {b:.6f}*x2 + {c:.6f}"
        predictions = a * x1 + b * x2 + c

        return {
            "expression": expression,
            "predictions": predictions.tolist(),
            "details": {}
        }