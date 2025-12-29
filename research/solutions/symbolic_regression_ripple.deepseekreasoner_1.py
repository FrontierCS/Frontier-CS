import numpy as np
from pysr import PySRRegressor
import sympy

class Solution:
    def __init__(self, **kwargs):
        pass

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        model = PySRRegressor(
            niterations=80,
            binary_operators=["+", "-", "*", "/", "**"],
            unary_operators=["sin", "cos", "exp", "log"],
            populations=30,
            population_size=50,
            maxsize=30,
            verbosity=0,
            progress=False,
            random_state=42,
            procs=8,
            model_selection="best",
            loss="loss(x, y) = (x - y)^2",
            temp_equation_file=True,
            temp_dir=".",
            update=False,
            deterministic=True,
            early_stop_condition=(
                "stop_if(loss, complexity) = loss < 1e-12 && complexity < 20"
            ),
        )
        
        try:
            model.fit(X, y, variable_names=["x1", "x2"])
            
            if model.equations_ is not None and not model.equations_.empty:
                best_expr = model.sympy()
                if best_expr is None:
                    expression = self._fit_fallback(X, y)
                else:
                    expression = self._clean_expression(str(best_expr))
            else:
                expression = self._fit_fallback(X, y)
                
            predictions = self._evaluate_expression(expression, X)
            
        except Exception as e:
            expression = self._fit_fallback(X, y)
            predictions = self._evaluate_expression(expression, X)
        
        complexity = self._compute_complexity(expression)
        
        return {
            "expression": expression,
            "predictions": predictions.tolist() if predictions is not None else None,
            "details": {"complexity": complexity}
        }
    
    def _fit_fallback(self, X: np.ndarray, y: np.ndarray) -> str:
        x1, x2 = X[:, 0], X[:, 1]
        
        A = np.column_stack([
            x1, x2,
            x1**2, x2**2, x1*x2,
            np.sin(x1), np.sin(x2),
            np.cos(x1), np.cos(x2),
            np.exp(-x1**2), np.exp(-x2**2),
            np.ones_like(x1)
        ])
        
        coeffs, _, _, _ = np.linalg.lstsq(A, y, rcond=None)
        
        terms = [
            f"{coeffs[0]:.6g}*x1",
            f"{coeffs[1]:.6g}*x2",
            f"{coeffs[2]:.6g}*x1**2",
            f"{coeffs[3]:.6g}*x2**2",
            f"{coeffs[4]:.6g}*x1*x2",
            f"{coeffs[5]:.6g}*sin(x1)",
            f"{coeffs[6]:.6g}*sin(x2)",
            f"{coeffs[7]:.6g}*cos(x1)",
            f"{coeffs[8]:.6g}*cos(x2)",
            f"{coeffs[9]:.6g}*exp(-x1**2)",
            f"{coeffs[10]:.6g}*exp(-x2**2)",
            f"{coeffs[11]:.6g}"
        ]
        
        expression = " + ".join(terms)
        return expression
    
    def _clean_expression(self, expr: str) -> str:
        expr = expr.replace("**", "**")
        expr = expr.replace("exp", "exp")
        expr = expr.replace("log", "log")
        expr = expr.replace("sin", "sin")
        expr = expr.replace("cos", "cos")
        
        for old, new in [("**", "**"), (" ", ""), ("\n", "")]:
            expr = expr.replace(old, new)
        
        return expr
    
    def _evaluate_expression(self, expr: str, X: np.ndarray) -> np.ndarray:
        x1, x2 = X[:, 0], X[:, 1]
        
        try:
            safe_dict = {
                "x1": x1, "x2": x2,
                "sin": np.sin, "cos": np.cos,
                "exp": np.exp, "log": np.log,
                "sqrt": np.sqrt
            }
            result = eval(expr, {"__builtins__": {}}, safe_dict)
            return np.array(result, dtype=float)
        except:
            try:
                expr_sympy = sympy.sympify(expr)
                func = sympy.lambdify(["x1", "x2"], expr_sympy, "numpy")
                return func(x1, x2)
            except:
                return None
    
    def _compute_complexity(self, expr: str) -> int:
        try:
            expr_sympy = sympy.sympify(expr)
            count = 0
            
            for atom in expr_sympy.atoms(sympy.Function):
                count += 1
            
            for atom in expr_sympy.atoms(sympy.Add, sympy.Mul, sympy.Pow):
                if isinstance(atom, (sympy.Add, sympy.Mul)):
                    count += 2 * (len(atom.args) - 1)
                elif isinstance(atom, sympy.Pow):
                    count += 2
            
            return max(1, count)
        except:
            return len(expr.split())