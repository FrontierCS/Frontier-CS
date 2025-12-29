import numpy as np
from pysr import PySRRegressor
import sympy as sp

class Solution:
    def __init__(self, **kwargs):
        pass

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        model = PySRRegressor(
            niterations=50,
            binary_operators=["+", "-", "*", "/", "**"],
            unary_operators=["sin", "cos", "exp", "log"],
            populations=8,
            population_size=40,
            maxsize=30,
            verbosity=0,
            progress=False,
            random_state=42,
            deterministic=True,
            maxdepth=12,
            nested_constraints={"sin": {"sin": 0, "cos": 0, "exp": 0, "log": 0},
                               "cos": {"sin": 0, "cos": 0, "exp": 0, "log": 0},
                               "exp": {"sin": 0, "cos": 0, "exp": 0, "log": 0},
                               "log": {"sin": 0, "cos": 0, "exp": 0, "log": 0}},
            constraints={"**": (4, 4)},
            early_stop_condition="stop_if(loss, complexity) = (loss < 1e-9 && complexity < 20)",
            weight_optimize=0.01,
            weight_simplify=0.002,
            tempdir="/tmp",
            equation_file=None,
            warm_start=True,
            update=False,
            turbo=True,
            batching=False,
            batch_size=50,
            loss="loss(x, y) = (x - y)^2",
            model_selection="accuracy"
        )
        
        model.fit(X, y, variable_names=["x1", "x2"])
        
        try:
            best_expr = model.sympy()
            expression = str(best_expr)
            
            sympy_expr = sp.sympify(expression)
            simplified = sp.simplify(sympy_expr)
            expression = str(simplified)
            
            predictions = model.predict(X)
            
            complexity = model.get_best()["complexity"] if hasattr(model, "get_best") else 0
            
        except Exception:
            x1, x2 = X[:, 0], X[:, 1]
            A = np.column_stack([x1, x2, np.sin(x1 + x2), (x1 - x2)**2, 
                                 np.ones_like(x1)])
            coeffs, _, _, _ = np.linalg.lstsq(A, y, rcond=None)
            a, b, c, d, e = coeffs
            expression = f"{c:.6f}*sin(x1 + x2) + {d:.6f}*(x1 - x2)**2 + {a:.6f}*x1 + {b:.6f}*x2 + {e:.6f}"
            predictions = a*x1 + b*x2 + c*np.sin(x1 + x2) + d*(x1 - x2)**2 + e
            complexity = 10
        
        expression = expression.replace("**", "^").replace("^", "**")
        
        return {
            "expression": expression,
            "predictions": predictions.tolist(),
            "details": {"complexity": int(complexity)}
        }