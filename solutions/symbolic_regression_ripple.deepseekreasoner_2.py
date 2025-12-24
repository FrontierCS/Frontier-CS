import numpy as np
from pysr import PySRRegressor
import sympy

class Solution:
    def __init__(self, **kwargs):
        pass

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        model = PySRRegressor(
            niterations=100,
            binary_operators=["+", "-", "*", "/", "**"],
            unary_operators=["sin", "cos", "exp", "log"],
            populations=8,
            population_size=50,
            maxsize=30,
            verbosity=0,
            progress=False,
            random_state=42,
            deterministic=True,
            maxdepth=10,
            temp_equation_file=True,
            tempdir=None,
            delete_tempfiles=True,
            warm_start=True,
            weight_optimize=0.02,
            update=False,
            precision=64,
            constraints={'**': (9, 1)},
            nested_constraints={'sin': {'sin': 0, 'cos': 0, 'exp': 0},
                                'cos': {'sin': 0, 'cos': 0, 'exp': 0},
                                'exp': {'sin': 0, 'cos': 0, 'exp': 0},
                                'log': {'sin': 0, 'cos': 0, 'exp': 0}},
            complexity_of_operators={'sin': 3, 'cos': 3, 'exp': 3, 'log': 3},
            complexity_of_constants=2,
            batching=True,
            batch_size=100,
            loss="L2DistLoss()",
            early_stop_condition=("stop_if(loss, complexity) = "
                                  "loss < 1e-12 && complexity < 10"),
            timeout_in_seconds=None,
            model_selection="best",
        )
        
        model.fit(X, y, variable_names=["x1", "x2"])
        
        best_expr = model.sympy()
        if best_expr is None:
            expression = "0"
        else:
            expression = str(best_expr)
        
        predictions = model.predict(X)
        
        return {
            "expression": expression,
            "predictions": predictions.tolist(),
            "details": {}
        }
