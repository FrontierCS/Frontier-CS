import numpy as np
from pysr import PySRRegressor

class Solution:
    def __init__(self, **kwargs):
        pass

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        model = PySRRegressor(
            niterations=100,
            binary_operators=["+", "-", "*", "/"],
            unary_operators=["sin", "cos", "exp", "log"],
            populations=30,
            population_size=50,
            maxsize=20,
            verbosity=0,
            progress=False,
            random_state=42,
            parsimony=1e-3,
            model_selection="best",
        )
        model.fit(X, y, variable_names=["x1", "x2"])

        best_expr = model.sympy()
        expression = str(best_expr)

        predictions = model.predict(X)

        details = {"complexity": model.equations_["complexity"].iloc[0] if not model.equations_.empty else 0}

        return {
            "expression": expression,
            "predictions": predictions.tolist(),
            "details": details
        }
