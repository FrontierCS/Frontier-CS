import numpy as np
from pysr import PySRRegressor
import sympy

class Solution:
    def __init__(self, **kwargs):
        self.model = PySRRegressor(
            niterations=200,
            populations=32,
            population_size=50,
            binary_operators=["+", "-", "*", "/"],
            unary_operators=["exp", "cos", "sin", "log"],
            constraints={'exp': -1, 'log': 1},
            nested_constraints={
                'exp': {'exp': 0},
                'sin': {'exp': 0, 'sin': 0},
                'cos': {'exp': 0, 'cos': 0},
                'log': {'exp': 0, 'log': 0},
            },
            complexity_of_operators={"exp": 2, "cos": 2, "sin": 2, "log": 2},
            maxsize=40,
            procs=8,
            multithreading=True,
            verbosity=0,
            progress=False,
            random_state=42,
            deterministic=True,
            model_selection="best",
            temp_equation_file=True,
        )

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        self.model.fit(X, y, variable_names=["x1", "x2", "x3", "x4"])

        if not hasattr(self.model, 'equations_') or self.model.equations_.empty:
            A = np.c_[X, np.ones(X.shape[0])]
            try:
                coeffs, _, _, _ = np.linalg.lstsq(A, y, rcond=None)
                expression = " + ".join(f"{c:.6f}*{v}" for c, v in zip(coeffs[:-1], ["x1", "x2", "x3", "x4"]))
                expression += f" + {coeffs[-1]:.6f}"
                
                x1, x2, x3, x4 = X[:, 0], X[:, 1], X[:, 2], X[:, 3]
                predictions = (coeffs[0] * x1 + coeffs[1] * x2 + coeffs[2] * x3 + 
                               coeffs[3] * x4 + coeffs[4])
                complexity = 16
            except np.linalg.LinAlgError:
                expression = "0.0"
                predictions = np.zeros_like(y)
                complexity = 1

            return {
                "expression": expression,
                "predictions": predictions.tolist(),
                "details": {"complexity": complexity}
            }

        best_equation = self.model.get_best()
        
        sympy_expr = best_equation.sympy_format
        if sympy_expr is None:
             sympy_expr = sympy.sympify(best_equation.equation)

        expression = str(sympy_expr)
        
        complexity = best_equation.complexity
        
        predictions = self.model.predict(X)

        return {
            "expression": expression,
            "predictions": predictions.tolist(),
            "details": {
                "complexity": int(complexity)
            }
        }