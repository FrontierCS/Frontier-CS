import numpy as np
from pysr import PySRRegressor

class Solution:
    def __init__(self, **kwargs):
        pass

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        model = PySRRegressor(
            niterations=60,
            binary_operators=["+", "-", "*", "/"],
            unary_operators=["sin", "cos", "exp", "log"],
            populations=8,
            population_size=40,
            maxsize=30,
            parsimony=0.001,
            verbosity=0,
            progress=False,
            random_state=42,
            ncyclesperiteration=400,
            early_stop_condition=1e-8,
            timeout_in_seconds=300,
            complexity_of_operators={"sin": 3, "cos": 3, "exp": 3, "log": 3},
            constraints={"**": (4, 1)},
            maxdepth=8,
        )
        
        model.fit(X, y, variable_names=["x1", "x2"])
        
        best_expr = model.sympy()
        expression = str(best_expr)
        predictions = model.predict(X)
        
        binary_ops = expression.count('+') + expression.count('-') + expression.count('*') + expression.count('/') + expression.count('**')
        unary_ops = expression.count('sin') + expression.count('cos') + expression.count('exp') + expression.count('log')
        complexity = 2 * binary_ops + unary_ops
        
        return {
            "expression": expression,
            "predictions": predictions.tolist(),
            "details": {"complexity": complexity}
        }
