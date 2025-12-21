import numpy as np
from pysr import PySRRegressor

class Solution:
    def __init__(self, **kwargs):
        pass

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        model = PySRRegressor(
            niterations=40,
            binary_operators=["+", "-", "*", "/", "**"],
            unary_operators=["sin", "cos", "exp", "log"],
            populations=15,
            population_size=33,
            maxsize=30,
            verbosity=0,
            progress=False,
            random_state=42,
            deterministic=True,
            early_stop_condition=1e-6,
            timeout_in_seconds=300,
            max_cycles=100,
            nested_constraints={"sin": {"sin": 0, "cos": 0},
                               "cos": {"sin": 0, "cos": 0}},
            complexity_of_constants=2,
        )
        
        model.fit(X, y, variable_names=["x1", "x2"])
        
        best_expr = model.sympy()
        expression = str(best_expr).replace("**", "^").replace("^", "**")
        
        try:
            predictions = model.predict(X)
        except:
            try:
                predictions = eval(f"lambda x1, x2: {expression}")(X[:, 0], X[:, 1])
            except:
                predictions = None
        
        complexity = 0
        if predictions is None:
            predictions = []
        else:
            predictions = predictions.tolist()
            
            expr_str = expression
            complexity = (expr_str.count("+") + expr_str.count("-") + 
                         expr_str.count("*") + expr_str.count("/") +
                         expr_str.count("**")) * 2
            complexity += (expr_str.count("sin") + expr_str.count("cos") + 
                          expr_str.count("exp") + expr_str.count("log"))
        
        return {
            "expression": expression,
            "predictions": predictions,
            "details": {"complexity": complexity}
        }
