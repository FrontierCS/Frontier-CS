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
            population_size=50,
            maxsize=35,
            verbosity=0,
            progress=False,
            random_state=42,
            nprocs=8,
            early_stop_condition=1e-6,
            complexity_of_constants=2,
            weight_optimize=0.02,
            update_test_best=15,
            model_selection="accuracy"
        )
        
        try:
            model.fit(X, y, variable_names=["x1", "x2", "x3", "x4"])
        except Exception as e:
            return self._fallback_solution(X, y, str(e))
        
        best_expr = model.sympy()
        if best_expr is None:
            return self._fallback_solution(X, y, "No valid expression found")
        
        expression = str(best_expr).replace("**", "^").replace("^", "**")
        
        try:
            predictions = model.predict(X)
        except:
            predictions = self._evaluate_expression(expression, X)
        
        complexity = self._compute_complexity(expression)
        
        return {
            "expression": expression,
            "predictions": predictions.tolist() if hasattr(predictions, "tolist") else predictions,
            "details": {"complexity": complexity}
        }
    
    def _fallback_solution(self, X: np.ndarray, y: np.ndarray, error_msg: str) -> dict:
        x1, x2, x3, x4 = X[:, 0], X[:, 1], X[:, 2], X[:, 3]
        
        A = np.column_stack([x1, x2, x3, x4, 
                             x1*x2, x1*x3, x1*x4, x2*x3, x2*x4, x3*x4,
                             x1**2, x2**2, x3**2, x4**2,
                             np.exp(-x1**2), np.exp(-x2**2), np.exp(-x3**2), np.exp(-x4**2),
                             np.ones_like(x1)])
        
        try:
            coeffs = np.linalg.lstsq(A, y, rcond=None)[0]
        except:
            coeffs = np.ones(A.shape[1]) * 0.1
        
        terms = [
            f"{coeffs[0]:.6f}*x1", f"{coeffs[1]:.6f}*x2", f"{coeffs[2]:.6f}*x3", f"{coeffs[3]:.6f}*x4",
            f"{coeffs[4]:.6f}*x1*x2", f"{coeffs[5]:.6f}*x1*x3", f"{coeffs[6]:.6f}*x1*x4",
            f"{coeffs[7]:.6f}*x2*x3", f"{coeffs[8]:.6f}*x2*x4", f"{coeffs[9]:.6f}*x3*x4",
            f"{coeffs[10]:.6f}*x1**2", f"{coeffs[11]:.6f}*x2**2", f"{coeffs[12]:.6f}*x3**2", f"{coeffs[13]:.6f}*x4**2",
            f"{coeffs[14]:.6f}*exp(-x1**2)", f"{coeffs[15]:.6f}*exp(-x2**2)",
            f"{coeffs[16]:.6f}*exp(-x3**2)", f"{coeffs[17]:.6f}*exp(-x4**2)",
            f"{coeffs[18]:.6f}"
        ]
        
        expression = " + ".join(terms).replace("+ -", "- ")
        predictions = A @ coeffs
        
        return {
            "expression": expression,
            "predictions": predictions.tolist(),
            "details": {"complexity": 50, "fallback": True, "error": error_msg}
        }
    
    def _evaluate_expression(self, expr: str, X: np.ndarray) -> np.ndarray:
        x1, x2, x3, x4 = X[:, 0], X[:, 1], X[:, 2], X[:, 3]
        try:
            return eval(expr, {"np": np, "sin": np.sin, "cos": np.cos, 
                               "exp": np.exp, "log": np.log, 
                               "x1": x1, "x2": x2, "x3": x3, "x4": x4})
        except:
            return np.zeros(len(X))
    
    def _compute_complexity(self, expr: str) -> int:
        binary_ops = sum(expr.count(op) for op in ["+", "-", "*", "/", "**"])
        unary_ops = sum(expr.count(f"({op}") for op in ["sin", "cos", "exp", "log"])
        return 2 * binary_ops + unary_ops
