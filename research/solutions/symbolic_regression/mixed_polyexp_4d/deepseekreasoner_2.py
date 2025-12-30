import numpy as np
from pysr import PySRRegressor

class Solution:
    def __init__(self, **kwargs):
        pass

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        model = PySRRegressor(
            niterations=80,
            binary_operators=["+", "-", "*", "/", "**"],
            unary_operators=["sin", "cos", "exp", "log"],
            populations=24,
            population_size=35,
            maxsize=32,
            verbosity=0,
            progress=False,
            random_state=42,
            complexity_of_constants=2,
            max_depth=12,
            nested_constants=False,
            warming_up=True,
            warm_start=True,
            deterministic=True,
            early_stop_condition=("stop_if(loss, complexity) = loss < 1e-12 && complexity < 20", 50),
            temp_scale=0.02,
            weight_optimize=0.02,
            update_test=False,
            precision=64,
            turbo=True,
            procs=8,
            multithreading=False,
            model_selection="best",
            loss="L2DistLoss()",
        )
        
        model.fit(X, y, variable_names=["x1", "x2", "x3", "x4"])
        
        best_expr = model.sympy()
        expression = str(best_expr).replace("**", "^").replace("^", "**")
        
        predictions = model.predict(X)
        
        return {
            "expression": expression,
            "predictions": predictions.tolist(),
            "details": {}
        }