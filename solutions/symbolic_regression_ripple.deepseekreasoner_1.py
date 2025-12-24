import numpy as np
from pysr import PySRRegressor

class Solution:
    def __init__(self, **kwargs):
        pass

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        model = PySRRegressor(
            niterations=50,
            binary_operators=["+", "-", "*", "/", "**"],
            unary_operators=["sin", "cos", "exp", "log"],
            populations=20,
            population_size=50,
            maxsize=30,
            verbosity=0,
            progress=False,
            random_state=42,
            deterministic=True,
            multithreading=False,
            model_selection="accuracy",
            early_stop_condition=(
                "stop_if(loss, complexity) = loss < 1e-12 && complexity < 10"
            ),
            nested_constraints={
                "sin": {"sin": 0, "cos": 0, "exp": 0, "log": 0},
                "cos": {"sin": 0, "cos": 0, "exp": 0, "log": 0},
                "exp": {"sin": 0, "cos": 0, "exp": 0, "log": 0},
                "log": {"sin": 0, "cos": 0, "exp": 0, "log": 0},
            },
        )
        
        try:
            model.fit(X, y, variable_names=["x1", "x2"])
        except Exception:
            # Fallback to linear model if PySR fails
            x1, x2 = X[:, 0], X[:, 1]
            A = np.column_stack([x1, x2, np.ones_like(x1)])
            coeffs, _, _, _ = np.linalg.lstsq(A, y, rcond=None)
            a, b, c = coeffs
            expression = f"{a:.6f}*x1 + {b:.6f}*x2 + {c:.6f}"
            predictions = a * x1 + b * x2 + c
            return {
                "expression": expression,
                "predictions": predictions.tolist(),
                "details": {"complexity": 2}
            }
        
        try:
            best_expr = model.sympy()
            if best_expr is None:
                raise ValueError("No valid expression found")
            expression = str(best_expr).replace("**", "^").replace("^", "**")
        except Exception:
            expression = str(model.equations_.iloc[-1]["sympy_format"])
            expression = expression.replace("**", "^").replace("^", "**")
        
        predictions = model.predict(X)
        
        complexity = 0
        if "complexity" in model.equations_.columns:
            best_idx = model.equations_["loss"].idxmin()
            complexity = int(model.equations_.iloc[best_idx]["complexity"])
        
        return {
            "expression": expression,
            "predictions": predictions.tolist(),
            "details": {"complexity": complexity}
        }
