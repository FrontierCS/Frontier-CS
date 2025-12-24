import numpy as np
from pysr import PySRRegressor

class Solution:
    def __init__(self, **kwargs):
        pass

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        model = PySRRegressor(
            niterations=50,
            binary_operators=["+", "-", "*", "/", "**"],
            unary_operators=["sin", "cos", "exp", "log"],
            populations=10,
            population_size=30,
            maxsize=30,
            verbosity=0,
            progress=False,
            random_state=42,
            constraints={
                "**": (4, 1),  # exponent between -4 and 4
                "log": (0, 0), # log only positive
            },
            warm_start=True,
            turbo=True,
            deterministic=True,
            max_evals=1000000,
            timeout_in_seconds=300,
            early_stop_condition=1e-8,
        )
        
        model.fit(X, y, variable_names=["x1", "x2"])
        
        best_expr = model.sympy()
        expression = str(best_expr).replace(" ", "")
        
        predictions = model.predict(X)
        
        complexity = 0
        expr_str = expression.lower()
        binary_ops = ['+', '-', '*', '/', '**']
        unary_ops = ['sin', 'cos', 'exp', 'log']
        
        for op in binary_ops:
            complexity += 2 * expr_str.count(op)
        for op in unary_ops:
            complexity += expr_str.count(op)
        
        return {
            "expression": expression,
            "predictions": predictions.tolist(),
            "details": {"complexity": complexity}
        }
