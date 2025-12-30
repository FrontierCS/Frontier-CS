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
            populations=12,
            population_size=50,
            maxsize=30,
            verbosity=0,
            progress=False,
            random_state=42,
            loss="loss(x, y) = (x - y)^2",
            early_stop_condition="stop_if(loss, complexity) = loss < 1e-8 && complexity < 10",
            deterministic=True,
            max_evals=200000,
        )
        
        model.fit(X, y, variable_names=["x1", "x2"])
        
        best_expr = model.sympy()
        expression = str(best_expr)
        
        try:
            predictions = model.predict(X)
        except:
            try:
                predictions = [float(best_expr.subs({"x1": xi[0], "x2": xi[1]})) for xi in X]
            except:
                predictions = None
        
        return {
            "expression": expression,
            "predictions": predictions.tolist() if predictions is not None else None,
            "details": {}
        }