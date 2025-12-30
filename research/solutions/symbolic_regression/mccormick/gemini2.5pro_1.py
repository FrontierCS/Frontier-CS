import numpy as np
from pysr import PySRRegressor

class Solution:
    def __init__(self, **kwargs):
        self.model = PySRRegressor(
            niterations=50,
            populations=16,
            population_size=35,
            binary_operators=["+", "-", "*"],
            unary_operators=["sin", "cos"],
            maxsize=30,
            nested_constraints={
                "sin": {"sin": 0, "cos": 0},
                "cos": {"sin": 0, "cos": 0},
            },
            procs=0,
            random_state=42,
            verbosity=0,
            progress=False,
            temp_equation_file=True,
        )

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        try:
            self.model.fit(X, y, variable_names=["x1", "x2"])
            
            if not hasattr(self.model, 'equations_') or self.model.equations_.empty:
                raise RuntimeError("PySR did not find any equations.")

            sympy_expr = self.model.sympy()
            expression = str(sympy_expr)
            
        except (RuntimeError, ValueError):
            x1, x2 = X[:, 0], X[:, 1]
            A = np.column_stack([np.ones_like(x1), x1, x2])
            
            try:
                coeffs, _, _, _ = np.linalg.lstsq(A, y, rcond=None)
                c, a, b = coeffs
                expression = f"{a:.8f}*x1 + {b:.8f}*x2 + {c:.8f}"
            except np.linalg.LinAlgError:
                expression = f"{np.mean(y):.8f}"

        return {
            "expression": expression,
            "predictions": None,
            "details": {}
        }