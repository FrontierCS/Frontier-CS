import numpy as np
from pysr import PySRRegressor

class Solution:
    def __init__(self, **kwargs):
        pass

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        model = PySRRegressor(
            niterations=60,
            binary_operators=["+", "-", "*", "/"],
            unary_operators=["sin", "cos"],
            populations=8,
            population_size=30,
            maxsize=20,
            maxdepth=8,
            ncycles_per_iteration=500,
            parsimony=0.008,
            constraints={
                "sin": 2,
                "cos": 2,
                "/": (-1, 1)
            },
            complexity_of_operators={
                "sin": 3,
                "cos": 3,
                "+": 1,
                "-": 1,
                "*": 2,
                "/": 2
            },
            verbosity=0,
            progress=False,
            random_state=42,
            deterministic=True,
            model_selection="best",
            early_stop_condition=1e-6,
            loss="L2DistLoss()",
            multithreading=True,
            cluster_manager=None,
            update=False
        )
        
        model.fit(X, y, variable_names=["x1", "x2"])
        
        best_expr = model.sympy()
        expression = str(best_expr).replace("**", "^")
        expression = expression.replace("^", "**")
        
        predictions = model.predict(X)
        
        binary_ops = expression.count("+") + expression.count("-") + \
                     expression.count("*") + expression.count("/") + \
                     expression.count("**")
        unary_ops = expression.count("sin(") + expression.count("cos(") + \
                    expression.count("exp(") + expression.count("log(")
        complexity = 2 * binary_ops + unary_ops
        
        return {
            "expression": expression,
            "predictions": predictions.tolist(),
            "details": {"complexity": complexity}
        }
