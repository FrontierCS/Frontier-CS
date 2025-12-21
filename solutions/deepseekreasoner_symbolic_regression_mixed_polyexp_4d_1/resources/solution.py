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
            populations=15,
            population_size=50,
            maxsize=40,
            verbosity=0,
            progress=False,
            random_state=42,
            deterministic=True,
            max_evals=100000,
            model_selection="accuracy",
            loss="loss(prediction, target) = (prediction - target)^2",
            complexity_of_operators={
                "sin": 2, "cos": 2, "exp": 2, "log": 2,
                "+": 1, "-": 1, "*": 1, "/": 1, "**": 2
            },
            nested_constraints={
                "sin": {"sin": 0, "cos": 0, "exp": 0, "log": 0},
                "cos": {"sin": 0, "cos": 0, "exp": 0, "log": 0},
                "exp": {"sin": 0, "cos": 0, "exp": 0, "log": 0},
                "log": {"sin": 0, "cos": 0, "exp": 0, "log": 0},
            },
            turbo=True,
            early_stop_condition=(
                "stop_if(loss, complexity) = (loss < 1e-9) && (complexity < 20)"
            )
        )
        
        try:
            model.fit(X, y, variable_names=["x1", "x2", "x3", "x4"])
            best_expr = model.sympy()
            expression = str(best_expr).replace("x0", "x1").replace("x1", "x2").replace("x2", "x3").replace("x3", "x4")
            predictions = model.predict(X).tolist()
            details = {}
        except Exception as e:
            x1, x2, x3, x4 = X[:, 0], X[:, 1], X[:, 2], X[:, 3]
            A = np.column_stack([x1, x2, x3, x4, np.ones_like(x1)])
            coeffs, _, _, _ = np.linalg.lstsq(A, y, rcond=None)
            a, b, c, d, e = coeffs
            expression = f"{a:.12f}*x1 + {b:.12f}*x2 + {c:.12f}*x3 + {d:.12f}*x4 + {e:.12f}"
            predictions = (a * x1 + b * x2 + c * x3 + d * x4 + e).tolist()
            details = {"fallback": "linear"}

        return {
            "expression": expression,
            "predictions": predictions,
            "details": details
        }
