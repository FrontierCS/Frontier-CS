import numpy as np
from pysr import PySRRegressor

class Solution:
    def __init__(self, **kwargs):
        pass

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        model = PySRRegressor(
            niterations=30,
            binary_operators=["+", "-", "*", "/", "**"],
            unary_operators=["sin", "cos", "exp", "log"],
            populations=8,
            population_size=25,
            maxsize=20,
            verbosity=0,
            progress=False,
            random_state=42,
            ncyclesperiteration=500,
            early_stop_condition=("stop_if(loss, 1e-6)", 5),
            timeout_in_seconds=300,
        )
        
        model.fit(X, y, variable_names=["x1", "x2"])
        
        best_expr = model.sympy()
        if best_expr is None:
            expression = "0"
            predictions = np.zeros_like(y)
        else:
            expression = str(best_expr).replace(" ", "")
            predictions = model.predict(X)
        
        return {
            "expression": expression,
            "predictions": predictions.tolist(),
            "details": {}
        }
