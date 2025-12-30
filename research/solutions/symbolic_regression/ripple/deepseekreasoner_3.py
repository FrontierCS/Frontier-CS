import numpy as np
from pysr import PySRRegressor
import sympy
from typing import Dict, Any

class Solution:
    def __init__(self, **kwargs):
        pass

    def solve(self, X: np.ndarray, y: np.ndarray) -> Dict[str, Any]:
        try:
            model = PySRRegressor(
                niterations=200,
                binary_operators=["+", "-", "*", "/", "**"],
                unary_operators=["sin", "cos", "exp", "log"],
                populations=8,
                population_size=100,
                maxsize=30,
                verbosity=0,
                progress=False,
                random_state=42,
                ncyclesperiteration=1000,
                early_stop_condition=(
                    "stop_if(loss, complexity) = loss < 1e-6 && complexity < 10"
                ),
                deterministic=True,
                weight_optimize=0.02,
                model_selection="best",
                temp_equation_file=True,
                temp_state_file=True,
                update_test=False,
                multithreading=True,
                cluster_manager=None,
                equation_file=None,
                state_file=None,
                should_optimize_constants=True,
                batching=False,
                batch_size=50,
                warm_start=False,
                julia_project=None,
                precision=64,
                loss="loss(x, y) = (x - y)^2",
                constraints={
                    "**": (9, 1),
                    "sin": 9,
                    "cos": 9,
                    "exp": 9,
                    "log": 9,
                },
                complexity_of_constants=1,
                complexity_of_operators={
                    "+": 1, "-": 1, "*": 1, "/": 1, "**": 2,
                    "sin": 1, "cos": 1, "exp": 1, "log": 1,
                },
                maxdepth=10,
                fast_cycle=False,
                turbo=True,
                extra_sympy_mappings={"log": lambda x: sympy.log(x)},
            )
            
            model.fit(X, y, variable_names=["x1", "x2"])
            
            if model.equations_ is not None and len(model.equations_) > 0:
                best_idx = model.equations_.loss.idxmin()
                expression_str = model.equations_.iloc[best_idx].equation
                
                try:
                    sympy_expr = model.sympy()
                    if sympy_expr is not None:
                        expression = str(sympy_expr)
                    else:
                        expression = expression_str
                except:
                    expression = expression_str
                
                predictions = model.predict(X)
            else:
                raise ValueError("No equations found")
                
        except Exception as e:
            x1 = X[:, 0]
            x2 = X[:, 1]
            
            A = np.column_stack([
                x1, x2, x1**2, x2**2, x1*x2,
                np.sin(x1), np.cos(x1), np.sin(x2), np.cos(x2),
                np.exp(-x1**2), np.exp(-x2**2), np.ones_like(x1)
            ])
            coeffs, _, _, _ = np.linalg.lstsq(A, y, rcond=None)
            
            a, b, c, d, e, f, g, h, i, j, k, l = coeffs
            
            expression = (
                f"{a:.6f}*x1 + {b:.6f}*x2 + {c:.6f}*x1**2 + {d:.6f}*x2**2 + "
                f"{e:.6f}*x1*x2 + {f:.6f}*sin(x1) + {g:.6f}*cos(x1) + "
                f"{h:.6f}*sin(x2) + {i:.6f}*cos(x2) + {j:.6f}*exp(-x1**2) + "
                f"{k:.6f}*exp(-x2**2) + {l:.6f}"
            )
            predictions = A @ coeffs
        
        return {
            "expression": expression,
            "predictions": predictions.tolist() if hasattr(predictions, 'tolist') else predictions,
            "details": {}
        }