import numpy as np
from pysr import PySRRegressor
import sympy as sp

class Solution:
    def __init__(self, **kwargs):
        pass

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        model = PySRRegressor(
            niterations=60,
            binary_operators=["+", "-", "*", "/", "**"],
            unary_operators=["sin", "cos", "exp", "log"],
            populations=12,
            population_size=35,
            maxsize=30,
            parsimony=0.001,
            verbosity=0,
            progress=False,
            random_state=42,
            ncycles_per_iteration=700,
            early_stop_condition=("stop_if(loss, complexity) = (loss < 1e-9) && (complexity < 30)", 1),
            warm_start=True,
            constraints={"**": (9, 1)},
            maxdepth=12,
            timeout_in_seconds=30,
            deterministic=True,
            batching=True,
            batch_size=100,
            model_selection="accuracy",
            loss="loss(x, y) = (x - y)^2",
            turbo=True,
            precision=64
        )
        
        try:
            model.fit(X, y, variable_names=["x1", "x2"])
            
            if hasattr(model, 'sympy') and model.sympy() is not None:
                sympy_expr = model.sympy()
                if isinstance(sympy_expr, list) and len(sympy_expr) > 0:
                    sympy_expr = sympy_expr[0]
                expression = str(sp.nsimplify(sympy_expr, [sp.pi], tolerance=1e-5))
            else:
                expression = self._fallback_expression(X, y)
                
            predictions = model.predict(X)
            
        except Exception:
            expression = self._fallback_expression(X, y)
            x1, x2 = X[:, 0], X[:, 1]
            predictions = self._evaluate_expression(expression, x1, x2)
        
        return {
            "expression": expression,
            "predictions": predictions.tolist() if hasattr(predictions, 'tolist') else list(predictions),
            "details": {"complexity": self._compute_complexity(expression)}
        }
    
    def _fallback_expression(self, X: np.ndarray, y: np.ndarray) -> str:
        x1, x2 = X[:, 0], X[:, 1]
        
        basis_functions = [
            np.ones_like(x1), x1, x2, x1**2, x2**2, x1*x2,
            np.sin(x1), np.cos(x1), np.sin(x2), np.cos(x2),
            np.sin(x1 + x2), np.cos(x1 + x2), np.exp(x1), np.exp(x2),
            np.log(np.abs(x1) + 1e-9), np.log(np.abs(x2) + 1e-9)
        ]
        
        A = np.column_stack(basis_functions)
        coeffs, residuals, rank, s = np.linalg.lstsq(A, y, rcond=None)
        
        terms = []
        term_names = [
            "1", "x1", "x2", "x1**2", "x2**2", "x1*x2",
            "sin(x1)", "cos(x1)", "sin(x2)", "cos(x2)",
            "sin(x1 + x2)", "cos(x1 + x2)", "exp(x1)", "exp(x2)",
            "log(abs(x1))", "log(abs(x2))"
        ]
        
        for i, (coeff, name) in enumerate(zip(coeffs, term_names)):
            if abs(coeff) > 1e-6:
                terms.append(f"({coeff:.8f})*{name}")
        
        if not terms:
            terms.append("0")
        
        expression = " + ".join(terms).replace(" + -", " - ")
        expression = expression.replace("(1.0)*", "").replace("(-1.0)*", "-")
        
        return expression
    
    def _evaluate_expression(self, expr: str, x1: np.ndarray, x2: np.ndarray) -> np.ndarray:
        try:
            namespace = {
                "x1": x1, "x2": x2, "sin": np.sin, "cos": np.cos,
                "exp": np.exp, "log": np.log, "abs": np.abs
            }
            return eval(expr, {"__builtins__": {}}, namespace)
        except Exception:
            return np.zeros_like(x1)
    
    def _compute_complexity(self, expr: str) -> int:
        try:
            sympy_expr = sp.sympify(expr)
            binary_ops = sympy_expr.count_ops(visual=False)
            unary_ops = 0
            
            for func in [sp.sin, sp.cos, sp.exp, sp.log]:
                unary_ops += len(sympy_expr.find(func))
            
            return 2 * binary_ops + unary_ops
        except Exception:
            return 100