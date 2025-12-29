import numpy as np
from pysr import PySRRegressor
from typing import Dict, Any
import warnings

class Solution:
    def __init__(self, **kwargs):
        pass

    def solve(self, X: np.ndarray, y: np.ndarray) -> Dict[str, Any]:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            
            model = PySRRegressor(
                niterations=30,
                binary_operators=["+", "-", "*", "/", "**"],
                unary_operators=["exp", "sin", "cos", "log"],
                populations=8,
                population_size=30,
                maxsize=20,
                early_stop_condition=(
                    "stop_if(loss, complexity) = loss < 1e-6 && complexity < 10"
                ),
                temp_equation_file=True,
                delete_tempfiles=True,
                verbosity=0,
                progress=False,
                random_state=42,
                deterministic=True,
                warm_start=True,
                tempdir="/tmp",
                multithreading=True,
                nested_constraints={
                    "exp": {"exp": 0, "log": 0},
                    "log": {"exp": 0, "log": 0}
                }
            )
            
            try:
                model.fit(X, y, variable_names=["x1", "x2"])
                
                if hasattr(model, "sympy") and callable(model.sympy):
                    try:
                        expression = str(model.sympy())
                    except:
                        if len(model.equations_) > 0:
                            best_eq = model.equations_.iloc[0]
                            expression = best_eq["equation"]
                        else:
                            expression = self._linear_fallback(X, y)
                else:
                    expression = self._linear_fallback(X, y)
                    
                predictions = model.predict(X)
                
                return {
                    "expression": expression,
                    "predictions": predictions.tolist(),
                    "details": {}
                }
                
            except Exception:
                return self._linear_fallback_result(X, y)
    
    def _linear_fallback(self, X: np.ndarray, y: np.ndarray) -> str:
        x1, x2 = X[:, 0], X[:, 1]
        A = np.column_stack([x1, x2, np.ones_like(x1)])
        coeffs, *_ = np.linalg.lstsq(A, y, rcond=None)
        a, b, c = coeffs
        return f"{a:.8f}*x1 + {b:.8f}*x2 + {c:.8f}"
    
    def _linear_fallback_result(self, X: np.ndarray, y: np.ndarray) -> Dict[str, Any]:
        expr = self._linear_fallback(X, y)
        x1, x2 = X[:, 0], X[:, 1]
        a, b, c = map(float, expr.replace('*x1', '').replace('*x2', '').replace('+', '').split())
        predictions = a * x1 + b * x2 + c
        return {
            "expression": expr,
            "predictions": predictions.tolist(),
            "details": {}
        }