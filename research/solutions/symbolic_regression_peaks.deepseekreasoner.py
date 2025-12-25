import numpy as np
from pysr import PySRRegressor

class Solution:
    def __init__(self, **kwargs):
        pass

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        model = PySRRegressor(
            niterations=30,
            binary_operators=["+", "-", "*", "/", "**"],
            unary_operators=["exp", "sin", "cos", "log"],
            populations=10,
            population_size=30,
            maxsize=20,
            verbosity=0,
            progress=False,
            random_state=42,
            deterministic=True,
            early_stop_condition=(
                "stop_if(loss, complexity) = (loss < 1e-3) && (complexity < 10)"
            ),
            temp_annealing=0.9,
            temp_decay=0.5,
            weight_optimize=0.02,
        )
        
        model.fit(X, y, variable_names=["x1", "x2"])
        
        best_expr = model.sympy()
        expression = str(best_expr).replace("**", "^").replace("^", "**")
        
        try:
            predictions = model.predict(X).tolist()
        except:
            x1, x2 = X[:, 0], X[:, 1]
            try:
                predictions = eval(expression, {"x1": x1, "x2": x2, "exp": np.exp, 
                                                "sin": np.sin, "cos": np.cos, "log": np.log}).tolist()
            except:
                predictions = None
        
        return {
            "expression": expression,
            "predictions": predictions,
            "details": {}
        }
