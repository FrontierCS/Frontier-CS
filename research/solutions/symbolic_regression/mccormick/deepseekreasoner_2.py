import numpy as np
from pysr import PySRRegressor
import sympy as sp

class Solution:
    def __init__(self, **kwargs):
        pass

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        model = PySRRegressor(
            niterations=50,
            binary_operators=["+", "-", "*", "/", "**"],
            unary_operators=["sin", "cos", "exp", "log"],
            populations=12,
            population_size=35,
            maxsize=30,
            maxdepth=10,
            verbosity=0,
            progress=False,
            random_state=42,
            deterministic=True,
            ncycles_per_iteration=700,
            warm_start=True,
            turbo=True,
            early_stop_condition=("stop_if(loss, complexity) = loss < 1e-12 && complexity < 15", 100),
            complexity_of_operators={"sin": 3, "cos": 3, "exp": 3, "log": 3, "**": 2},
            complexity_of_constants=1,
            nested_constraints={"sin": {"sin": 0, "cos": 0, "exp": 0, "log": 0},
                               "cos": {"sin": 0, "cos": 0, "exp": 0, "log": 0},
                               "exp": {"sin": 0, "cos": 0, "exp": 0, "log": 0},
                               "log": {"sin": 0, "cos": 0, "exp": 0, "log": 0}},
            weight_optimize=0.02,
            weight_simplify=0.02,
            loss="loss(x, y) = (x - y)^2",
            select_k_features=2,
            update_test=False,
            should_optimize_constants=True,
        )
        
        model.fit(X, y, variable_names=["x1", "x2"])
        
        best_expr = model.sympy()
        expression = str(sp.simplify(best_expr))
        
        predictions = model.predict(X)
        
        binary_ops = expression.count('+') + expression.count('-') + expression.count('*') + expression.count('/') + expression.count('**')
        unary_ops = expression.count('sin') + expression.count('cos') + expression.count('exp') + expression.count('log')
        complexity = 2 * binary_ops + unary_ops
        
        return {
            "expression": expression,
            "predictions": predictions.tolist(),
            "details": {"complexity": complexity}
        }