import numpy as np
from pysr import PySRRegressor

class Solution:
    def __init__(self, **kwargs):
        pass

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        model = PySRRegressor(
            niterations=200,
            binary_operators=["+", "-", "*", "/", "**"],
            unary_operators=["sin", "cos", "exp", "log"],
            populations=32,
            population_size=50,
            maxsize=30,
            parsimony=0.003,
            ncycles_per_iteration=800,
            nprocs=8,
            verbosity=0,
            progress=False,
            random_state=42,
            deterministic=True,
            early_stop_condition=1e-8,
            constraints={
                '**': (4, 1),
                'log': 1,
                'exp': 4
            },
            complexity_of_operators={
                '**': 3,
                'exp': 2,
                'log': 2,
                'sin': 2,
                'cos': 2
            }
        )
        
        model.fit(X, y, variable_names=["x1", "x2"])
        
        best_expr = model.sympy()
        expression = str(best_expr).replace('**', '**').replace('exp', 'exp').replace('log', 'log')
        
        predictions = model.predict(X)
        
        binary_ops = ['+', '-', '*', '/', '**']
        unary_ops = ['sin', 'cos', 'exp', 'log']
        expr_str = expression
        complexity = 0
        for op in binary_ops:
            complexity += 2 * expr_str.count(op)
        for op in unary_ops:
            complexity += expr_str.count(op)
        
        return {
            "expression": expression,
            "predictions": predictions.tolist(),
            "details": {"complexity": complexity}
        }
