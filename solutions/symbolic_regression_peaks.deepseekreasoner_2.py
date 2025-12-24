import numpy as np
from pysr import PySRRegressor
import warnings

class Solution:
    def __init__(self, **kwargs):
        pass

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", category=UserWarning)
            
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
                early_stop_condition="stop_if(loss, complexity) = loss < 1e-9 && complexity < 20",
                deterministic=True,
                loss="loss(prediction, target) = (prediction - target)^2",
                constraints={
                    "exp": 4,
                    "log": 4,
                    "sin": 4,
                    "cos": 4,
                    "**": 4
                },
                nested_constraints={
                    "sin": {"sin": 0, "cos": 0, "exp": 1, "log": 1},
                    "cos": {"sin": 0, "cos": 0, "exp": 1, "log": 1},
                    "exp": {"exp": 1, "log": 1, "sin": 1, "cos": 1},
                    "log": {"exp": 1, "log": 1, "sin": 1, "cos": 1},
                    "**": {"**": 1}
                },
                complexity_of_operators={
                    "**": 3,
                    "exp": 3,
                    "log": 3,
                    "sin": 2,
                    "cos": 2
                },
                weight_optimize=0.02,
                weight_simplify=0.02,
                turbo=True,
                multithreading=True,
                model_selection="best",
                extra_sympy_mappings={
                    "exp": lambda x: np.exp(x),
                    "log": lambda x: np.log(np.abs(x) + 1e-12)
                }
            )
            
            model.fit(X, y, variable_names=["x1", "x2"])
            
            try:
                best_expr = model.sympy()
                if best_expr is None:
                    best_expr = model.equations_.iloc[0]["sympy_format"]
                expression = str(best_expr)
                expression = expression.replace("Abs", "")
                expression = expression.replace("abs", "")
                expression = expression.replace("log", "np.log")
                expression = expression.replace("exp", "np.exp")
                expression = expression.replace("sin", "np.sin")
                expression = expression.replace("cos", "np.cos")
                
                predictions = model.predict(X)
                
                complexity = len(model.equations_)
                
                return {
                    "expression": expression,
                    "predictions": predictions.tolist(),
                    "details": {"complexity": int(complexity)}
                }
            except Exception as e:
                x1 = X[:, 0]
                x2 = X[:, 1]
                A = np.column_stack([x1, x2, x1**2, x2**2, x1*x2, 
                                    np.exp(-x1**2), np.exp(-x2**2),
                                    np.sin(x1), np.cos(x2), np.ones_like(x1)])
                coeffs, _, _, _ = np.linalg.lstsq(A, y, rcond=None)
                
                a, b, c, d, e, f, g, h, i, j = coeffs
                expression = f"{a:.6f}*x1 + {b:.6f}*x2 + {c:.6f}*x1**2 + {d:.6f}*x2**2 + {e:.6f}*x1*x2 + {f:.6f}*np.exp(-x1**2) + {g:.6f}*np.exp(-x2**2) + {h:.6f}*np.sin(x1) + {i:.6f}*np.cos(x2) + {j:.6f}"
                predictions = A @ coeffs
                
                return {
                    "expression": expression,
                    "predictions": predictions.tolist(),
                    "details": {"complexity": 10}
                }
