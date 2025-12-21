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
            populations=30,
            population_size=50,
            maxsize=35,
            verbosity=0,
            progress=False,
            random_state=42,
            deterministic=True,
            extra_sympy_mappings={"log": lambda x: sympy.log(abs(x) + 1e-8)},
            nested_constraints={"log": {"log": 0, "exp": 0}},
            constraints={"**": (4, 2)},
            early_stop_condition=(
                "stop_if(loss, complexity) = loss < 1e-9 && complexity < 20"
            ),
        )
        
        model.fit(X, y, variable_names=["x1", "x2", "x3", "x4"])
        
        best_expr = model.sympy()
        expression = str(best_expr).replace("**", "^")
        
        predictions = model.predict(X)
        
        return {
            "expression": expression,
            "predictions": predictions.tolist(),
            "details": {}
        }
