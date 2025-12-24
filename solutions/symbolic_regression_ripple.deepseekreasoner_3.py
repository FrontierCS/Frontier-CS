import numpy as np
from pysr import PySRRegressor
import sympy
from typing import Dict, Any

class Solution:
    def __init__(self, **kwargs):
        pass

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        model = PySRRegressor(
            niterations=30,
            binary_operators=["+", "-", "*", "/", "**"],
            unary_operators=["sin", "cos", "exp", "log"],
            populations=10,
            population_size=30,
            maxsize=20,
            early_stop_condition=1e-8,
            verbosity=0,
            progress=False,
            random_state=42,
            deterministic=True,
            max_cycles=2,
            loss="L2DistLoss()",
            nested_constraints={
                "log": {"log": 1},
                "exp": {"exp": 1},
                "sin": {"sin": 1},
                "cos": {"cos": 1}
            },
            constraints={
                "**": (4, 1),
                "/": (4, 1),
                "log": 4,
                "exp": 4,
                "sin": 4,
                "cos": 4
            }
        )
        
        model.fit(X, y, variable_names=["x1", "x2"])
        
        best_expr = model.sympy()
        expression = str(best_expr)
        
        predictions = model.predict(X)
        
        complexity = 0
        if hasattr(best_expr, 'count_ops'):
            complexity = sympy.count_ops(best_expr)
        
        return {
            "expression": expression,
            "predictions": predictions.tolist(),
            "details": {"complexity": complexity}
        }
