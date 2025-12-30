import numpy as np
from pysr import PySRRegressor

class Solution:
    def __init__(self, **kwargs):
        pass

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        model = PySRRegressor(
            niterations=60,
            binary_operators=["+", "-", "*", "/", "**"],
            unary_operators=["sin", "cos"],
            populations=12,
            population_size=35,
            maxsize=20,
            verbosity=0,
            progress=False,
            random_state=42,
            ncyclesperiteration=700,
            early_stop_condition=1e-12,
            loss="L2DistLoss()",
            complexity_of_constants=2,
        )
        
        model.fit(X, y, variable_names=["x1", "x2"])
        
        best_expr = model.sympy()
        expression = str(best_expr).replace("**", "^").replace("^", "**")
        
        x1 = X[:, 0]
        x2 = X[:, 1]
        
        try:
            predictions = model.predict(X)
        except:
            predictions = eval(expression, {"x1": x1, "x2": x2, "sin": np.sin, "cos": np.cos})
        
        ops = 0
        for op in ["+", "-", "*", "/"]:
            ops += expression.count(op)
        if "**" in expression:
            ops += expression.count("**")
        for func in ["sin", "cos", "exp", "log"]:
            ops += expression.count(func)
        
        return {
            "expression": expression,
            "predictions": predictions.tolist(),
            "details": {"complexity": ops}
        }