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
            population_size=30,
            maxsize=20,
            verbosity=0,
            progress=False,
            random_state=42,
            deterministic=True,
            max_evals=100000,
            constraints={
                "**": (4, 1),
                "exp": 4,
                "log": 4
            },
            early_stop_condition=1e-8,
            loss="L2DistLoss()",
            model_selection="accuracy",
        )
        model.fit(X, y, variable_names=["x1", "x2"])
        
        best_expr = model.sympy()
        if best_expr is None:
            expression = "0.0"
            predictions = np.zeros_like(y)
        else:
            expression = str(best_expr).replace("**", "^").replace("^", "**")
            predictions = model.predict(X)
        
        return {
            "expression": expression,
            "predictions": predictions.tolist(),
            "details": {}
        }
