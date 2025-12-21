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
            maxsize=30,
            verbosity=0,
            progress=False,
            random_state=42,
            loss="loss(sum of squares)",
            model_selection="best"
        )
        model.fit(X, y, variable_names=["x1", "x2"])

        best_expr = model.sympy()
        expression = str(best_expr).replace('**', '^') if '^' in str(best_expr) else str(best_expr)

        predictions = model.predict(X).tolist()

        complexity = int(model.equations_['complexity'].iloc[0]) if not model.equations_.empty else 0

        return {
            "expression": expression,
            "predictions": predictions,
            "details": {"complexity": complexity}
        }
