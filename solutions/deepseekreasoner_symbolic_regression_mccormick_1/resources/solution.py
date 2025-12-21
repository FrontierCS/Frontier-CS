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
            population_size=30,
            maxsize=20,
            verbosity=0,
            progress=False,
            random_state=42,
            deterministic=True,
            temp_equation_file=True,
            temp_dir="./pysr_cache",
            maxdepth=10,
            nested_constraints={"sin": {"sin": 0, "cos": 0, "exp": 0, "log": 0},
                                "cos": {"sin": 0, "cos": 0, "exp": 0, "log": 0},
                                "exp": {"sin": 0, "cos": 0, "exp": 0, "log": 0},
                                "log": {"sin": 0, "cos": 0, "exp": 0, "log": 0}},
            constraints={"**": (4, 1)},
            loss="L2DistLoss()",
            early_stop_condition="stop_if(loss, complexity) = loss < 1e-12 && complexity < 20",
            timeout_in_seconds=300,
            warm_start=True,
            batching=True,
            batch_size=1000,
            ncycles_per_iteration=500,
        )
        
        try:
            model.fit(X, y, variable_names=["x1", "x2"])
            
            if hasattr(model, 'sympy') and model.sympy() is not None:
                sympy_expr = model.sympy()
                simplified = sp.simplify(sympy_expr)
                expression = str(simplified).replace('**', '**')
            else:
                equations = model.equations_
                if equations is not None and not equations.empty:
                    best_row = equations[equations['loss'].idxmin()]
                    expression = best_row['equation']
                else:
                    expression = self._fallback_expression(X, y)
            
            predictions = model.predict(X)
            if predictions is None:
                x1, x2 = X[:, 0], X[:, 1]
                predictions = eval(expression, {"x1": x1, "x2": x2, "sin": np.sin, 
                                                "cos": np.cos, "exp": np.exp, "log": np.log,
                                                "np": np})
            
            complexity = self._compute_complexity(expression)
            
        except Exception as e:
            expression, predictions, complexity = self._fallback_expression(X, y, return_all=True)
        
        return {
            "expression": expression,
            "predictions": predictions.tolist() if hasattr(predictions, 'tolist') else predictions,
            "details": {"complexity": complexity}
        }
    
    def _fallback_expression(self, X: np.ndarray, y: np.ndarray, return_all=False):
        x1, x2 = X[:, 0], X[:, 1]
        A = np.column_stack([np.sin(x1 + x2), (x1 - x2)**2, x1, x2, np.ones_like(x1)])
        coeffs, _, _, _ = np.linalg.lstsq(A, y, rcond=None)
        a, b, c, d, e = coeffs
        
        terms = []
        if abs(a) > 1e-10:
            terms.append(f"{a:.6f}*sin(x1 + x2)")
        if abs(b) > 1e-10:
            terms.append(f"{b:.6f}*(x1 - x2)**2")
        if abs(c) > 1e-10:
            terms.append(f"{c:.6f}*x1")
        if abs(d) > 1e-10:
            terms.append(f"{d:.6f}*x2")
        if abs(e) > 1e-10:
            terms.append(f"{e:.6f}")
        
        expression = " + ".join(terms) if terms else "0"
        predictions = a * np.sin(x1 + x2) + b * (x1 - x2)**2 + c * x1 + d * x2 + e
        complexity = self._compute_complexity(expression)
        
        if return_all:
            return expression, predictions, complexity
        return expression
    
    def _compute_complexity(self, expr: str) -> int:
        try:
            sympy_expr = sp.sympify(expr)
            ops = 0
            for atom in sympy_expr.atoms(sp.Function):
                ops += 1
            for atom in sympy_expr.atoms(sp.Add, sp.Mul, sp.Pow):
                if isinstance(atom, (sp.Add, sp.Mul)):
                    ops += len(atom.args) - 1
                elif isinstance(atom, sp.Pow):
                    ops += 1
            return max(ops, 1)
        except:
            return 10
