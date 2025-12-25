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
            populations=10,
            population_size=30,
            maxsize=20,
            verbosity=0,
            progress=False,
            random_state=42,
            timeout_in_seconds=300,
        )
        model.fit(X, y, variable_names=["x1", "x2"])

        best_expr = model.sympy()
        expression = str(best_expr)

        predictions = model.predict(X).tolist()

        details = {}
        if not model.equations_.empty:
            details["complexity"] = int(model.equations_.iloc[0]["Complexity"])

        return {
            "expression": expression,
            "predictions": predictions,
            "details": details
        }
