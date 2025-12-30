import numpy as np
from pysr import PySRRegressor
import sympy as sp

class Solution:
    def __init__(self, **kwargs):
        pass

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        model = PySRRegressor(
            niterations=80,
            binary_operators=["+", "-", "*", "/", "**"],
            unary_operators=["sin", "cos", "exp", "log"],
            populations=12,
            population_size=35,
            maxsize=30,
            verbosity=0,
            progress=False,
            random_state=42,
            ncycles_per_iteration=500,
            early_stop_condition="1e-8",
            maxdepth=12,
            complexity_of_operators={"+": 1, "-": 1, "*": 1, "/": 1, "**": 2,
                                     "sin": 2, "cos": 2, "exp": 3, "log": 3},
            batching=True,
            batch_size=100,
            warm_start=True,
            precision=64
        )
        
        model.fit(X, y, variable_names=["x1", "x2"])
        
        best_expr = model.sympy()
        if best_expr is None:
            best_expr = sp.sympify("x1 + x2")
        
        simplified = sp.simplify(best_expr)
        expression = str(simplified).replace("**", "^").replace("^", "**")
        
        try:
            predictions = model.predict(X)
            predictions = predictions.tolist()
        except:
            x1 = X[:, 0]
            x2 = X[:, 1]
            predictions = [float(simplified.subs({"x1": xi1, "x2": xi2}))
                          for xi1, xi2 in zip(x1, x2)]
        
        binary_ops = 0
        unary_ops = 0
        expr_str = str(simplified)
        binary_ops += expr_str.count('+') + expr_str.count('-') + expr_str.count('*')
        binary_ops += expr_str.count('/') + expr_str.count('**')
        unary_ops += expr_str.count('sin') + expr_str.count('cos')
        unary_ops += expr_str.count('exp') + expr_str.count('log')
        
        complexity = 2 * binary_ops + unary_ops
        
        return {
            "expression": expression,
            "predictions": predictions,
            "details": {"complexity": complexity}
        }