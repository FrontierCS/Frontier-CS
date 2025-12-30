import numpy as np
from pysr import PySRRegressor

class Solution:
    def __init__(self, **kwargs):
        pass

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        model = PySRRegressor(
            niterations=30,
            binary_operators=["+", "-", "*", "/", "**"],
            unary_operators=["sin", "cos", "exp", "log"],
            populations=12,
            population_size=30,
            maxsize=20,
            verbosity=0,
            progress=False,
            random_state=42,
            early_stop_condition=1e-10,
            deterministic=True,
            max_depth=12,
            timeout_in_seconds=60,
            ncyclesperiteration=400,
            parsimony=0.003,
            complexity_of_operators={
                "sin": 1, "cos": 1, "exp": 2, "log": 2,
                "+": 1, "-": 1, "*": 1, "/": 1, "**": 2
            }
        )
        model.fit(X, y, variable_names=["x1", "x2"])
        
        best_expr = model.sympy()
        expression = str(best_expr).replace("**", "^").replace("^", "**")
        
        predictions = model.predict(X)
        
        binary_ops = expression.count('+') + expression.count('-') + expression.count('*') + expression.count('/') + expression.count('**')
        unary_ops = expression.count('sin') + expression.count('cos') + expression.count('exp') + expression.count('log')
        complexity = 2 * binary_ops + unary_ops
        
        return {
            "expression": expression,
            "predictions": predictions.tolist(),
            "details": {"complexity": complexity}
        }