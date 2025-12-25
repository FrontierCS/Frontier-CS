import numpy as np
from pysr import PySRRegressor

class Solution:
    def __init__(self, **kwargs):
        pass

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        model = PySRRegressor(
            niterations=100,
            binary_operators=["+", "-", "*", "/", "**"],
            unary_operators=["sin", "cos", "exp", "log"],
            populations=20,
            population_size=40,
            maxsize=30,
            verbosity=0,
            progress=False,
            random_state=42,
        )
        model.fit(X, y, variable_names=["x1", "x2", "x3", "x4"])

        best_expr = model.sympy()
        expression = str(best_expr)

        predictions = model.predict(X).tolist()

        complexity = int(model.equations_['complexity'].iloc[0])

        return {
            "expression": expression,
            "predictions": predictions,
            "details": {"complexity": complexity}
        }
