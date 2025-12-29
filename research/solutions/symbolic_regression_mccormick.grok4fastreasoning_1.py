import numpy as np
from pysr import PySRRegressor
import sympy as sp

class Solution:
    def __init__(self, **kwargs):
        pass

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        model = PySRRegressor(
            niterations=100,
            binary_operators=["+", "-", "*", "/"],
            unary_operators=["sin", "cos", "exp", "log"],
            populations=10,
            population_size=30,
            maxsize=20,
            verbosity=0,
            progress=False,
            random_state=42,
            parsimony=0.01,
            model_selection="best"
        )
        model.fit(X, y, variable_names=["x1", "x2"])

        sympy_expr = model.sympy()
        simplified = sp.simplify(sympy_expr)
        expression = str(simplified)

        predictions = model.predict(X).tolist()

        return {
            "expression": expression,
            "predictions": predictions,
            "details": {}
        }