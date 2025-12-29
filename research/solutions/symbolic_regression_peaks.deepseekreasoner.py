import numpy as np
from pysr import PySRRegressor

class Solution:
    def __init__(self, **kwargs):
        pass

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        model = PySRRegressor(
            niterations=35,
            binary_operators=["+", "-", "*", "/", "**"],
            unary_operators=["sin", "cos", "exp", "log"],
            populations=8,
            population_size=25,
            maxsize=20,
            verbosity=0,
            progress=False,
            random_state=42,
            procs=8,
            deterministic=True,
            early_stop_condition="(loss <= 1e-8)",
            max_depth=10,
            constraints={
                "**": (9, 2)
            },
            nested_constraints={
                "sin": {"sin": 0, "cos": 0, "exp": 0, "log": 0},
                "cos": {"sin": 0, "cos": 0, "exp": 0, "log": 0},
                "exp": {"sin": 0, "cos": 0, "exp": 0, "log": 0},
                "log": {"sin": 0, "cos": 0, "exp": 0, "log": 0}
            }
        )
        
        model.fit(X, y, variable_names=["x1", "x2"])
        
        best_expr = model.sympy()
        if best_expr is None:
            expression = "x1 + x2"
        else:
            expression = str(best_expr)
        
        predictions = model.predict(X)
        
        complexity = 0
        if best_expr is not None:
            expr_str = str(best_expr)
            binary_ops = expr_str.count('+') + expr_str.count('-') + expr_str.count('*') + expr_str.count('/') + expr_str.count('**')
            unary_ops = expr_str.count('sin') + expr_str.count('cos') + expr_str.count('exp') + expr_str.count('log')
            complexity = 2 * binary_ops + unary_ops
        
        return {
            "expression": expression,
            "predictions": predictions.tolist(),
            "details": {"complexity": complexity}
        }