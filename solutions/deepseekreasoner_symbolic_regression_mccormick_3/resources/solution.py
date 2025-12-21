import numpy as np
from pysr import PySRRegressor
import sympy as sp

class Solution:
    def __init__(self, **kwargs):
        pass

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        model = PySRRegressor(
            niterations=40,
            binary_operators=["+", "-", "*", "/", "**"],
            unary_operators=["sin", "cos", "exp", "log"],
            populations=8,
            population_size=40,
            maxsize=30,
            maxdepth=10,
            ncycles_per_iteration=700,
            complexity_of_operators={"sin": 3, "cos": 3, "exp": 3, "log": 3, "**": 2},
            early_stop_condition=(
                "stop_if(loss, complexity) = loss < 1e-12 && complexity < 30"
            ),
            verbosity=0,
            progress=False,
            random_state=42,
            deterministic=True,
            extra_sympy_mappings={"log": lambda x: sp.log(sp.Abs(x) + 1e-12)},
            constraints={
                "log": (5,),
                "exp": (5,),
                "**": (-1, 5),
            }
        )
        
        model.fit(X, y, variable_names=["x1", "x2"])
        
        best_expr = model.sympy()
        if best_expr is None:
            best_expr = sp.Float(0.0)
        
        try:
            simplified_expr = sp.simplify(best_expr)
            expression = str(simplified_expr)
        except:
            expression = str(best_expr)
        
        expression = expression.replace("Abs", "")
        expression = expression.replace(" ", "")
        
        predictions = model.predict(X)
        if predictions is None:
            x1 = X[:, 0]
            x2 = X[:, 1]
            predictions = eval(expression, {"x1": x1, "x2": x2, "sin": np.sin, 
                                           "cos": np.cos, "exp": np.exp, 
                                           "log": np.log, "np": np})
        
        return {
            "expression": expression,
            "predictions": predictions.tolist() if hasattr(predictions, 'tolist') else predictions,
            "details": {}
        }
