import numpy as np
from pysr import PySRRegressor
import sympy as sp

class Solution:
    def __init__(self, **kwargs):
        pass

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        model = PySRRegressor(
            niterations=40,
            binary_operators=["+", "-", "*", "/", "**"],
            unary_operators=["sin", "cos", "exp", "log"],
            populations=8,
            population_size=33,
            maxsize=30,
            verbosity=0,
            progress=False,
            random_state=42,
            ncycles_per_iteration=500,
            early_stop_condition="1e-8",
            temp_equation_file=True,
            delete_tempfiles=True,
            deterministic=True,
            maxdepth=None,
            constraints={
                "**": (4, 1),
                "log": (1, 0)
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
        if isinstance(best_expr, list):
            best_expr = best_expr[0]
        
        simplified = sp.nsimplify(
            sp.simplify(best_expr),
            [sp.pi, sp.E],
            tolerance=1e-8
        )
        
        expression = str(simplified).replace("**", "^").replace("^", "**")
        
        x1_sym, x2_sym = sp.symbols('x1 x2')
        sym_func = sp.lambdify((x1_sym, x2_sym), simplified, 'numpy')
        
        x1, x2 = X[:, 0], X[:, 1]
        predictions = sym_func(x1, x2).tolist()
        
        expr_str = str(simplified)
        binary_ops = expr_str.count('+') + expr_str.count('-') + expr_str.count('*') + expr_str.count('/') + expr_str.count('**')
        unary_ops = expr_str.count('sin') + expr_str.count('cos') + expr_str.count('exp') + expr_str.count('log')
        complexity = 2 * binary_ops + unary_ops
        
        return {
            "expression": expression,
            "predictions": predictions,
            "details": {"complexity": complexity}
        }
