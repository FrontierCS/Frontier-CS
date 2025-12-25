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
            populations=8,
            population_size=40,
            maxsize=30,
            verbosity=0,
            progress=False,
            random_state=42,
            ncycles_per_iteration=400,
            maxdepth=12,
            weight_optimize=0.02,
            early_stop_condition=1e-8,
            timeout_in_seconds=None,
            warm_start=True,
            model_selection="best",
            loss="loss(prediction, target) = (prediction - target)^2",
            constraints={
                "sin": 4,
                "cos": 4,
                "exp": 2,
                "log": 2,
                "**": 2,
                "/": 4
            },
            complexity_of_operators={
                "sin": 3,
                "cos": 3,
                "exp": 4,
                "log": 4,
                "**": 3,
                "/": 2
            },
            temp_equation_file=False
        )
        
        try:
            model.fit(X, y, variable_names=["x1", "x2"])
            
            best_expr = model.sympy()
            if best_expr is not None:
                expression = str(best_expr)
                predictions = model.predict(X)
            else:
                expression = "0"
                predictions = np.zeros_like(y)
        except Exception:
            x1, x2 = X[:, 0], X[:, 1]
            A = np.column_stack([
                np.sin(x1), np.cos(x1), 
                np.sin(x2), np.cos(x2),
                np.sin(x1 + x2), np.cos(x1 + x2),
                np.sin(x1 * x2), np.cos(x1 * x2),
                np.ones_like(x1)
            ])
            coeffs, _, _, _ = np.linalg.lstsq(A, y, rcond=None)
            
            expression_parts = []
            for i, (coeff, term) in enumerate(zip(
                coeffs,
                ["sin(x1)", "cos(x1)", "sin(x2)", "cos(x2)", 
                 "sin(x1+x2)", "cos(x1+x2)", "sin(x1*x2)", "cos(x1*x2)", ""]
            )):
                if abs(coeff) > 1e-10:
                    if term:
                        expression_parts.append(f"{coeff:.8f}*{term}")
                    else:
                        expression_parts.append(f"{coeff:.8f}")
            
            if expression_parts:
                expression = " + ".join(expression_parts).replace("+ -", "- ")
            else:
                expression = "0"
            
            predictions = A @ coeffs
        
        return {
            "expression": expression,
            "predictions": predictions.tolist() if hasattr(predictions, 'tolist') else predictions,
            "details": {}
        }
