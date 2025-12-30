import numpy as np
from pysr import PySRRegressor
import sympy

class Solution:
    def __init__(self, **kwargs):
        pass

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        model = PySRRegressor(
            niterations=100,
            binary_operators=["+", "-", "*", "/", "**"],
            unary_operators=["sin", "cos", "exp", "log"],
            populations=15,
            population_size=35,
            maxsize=25,
            verbosity=0,
            progress=False,
            random_state=42,
            deterministic=True,
            early_stop_condition=(
                "stop_if(loss, complexity) = loss < 1e-9 && complexity < 20"
            ),
            timeout_in_seconds=300,
            ncyclesperiteration=700,
            complexity_of_operators={
                "**": 3,
                "exp": 2,
                "log": 2,
                "sin": 2,
                "cos": 2,
            },
            nested_constraints={
                "**": {"**": 0},
                "log": {"log": 0, "exp": 0},
                "exp": {"log": 0, "exp": 0},
            },
        )
        
        try:
            model.fit(X, y, variable_names=["x1", "x2", "x3", "x4"])
            
            best_expr = model.sympy()
            if best_expr is not None:
                expression = str(best_expr)
                predictions = model.predict(X)
            else:
                expression = self._fallback_expression(X, y)
                predictions = self._evaluate_expression(expression, X)
        except Exception:
            expression = self._fallback_expression(X, y)
            predictions = self._evaluate_expression(expression, X)
        
        return {
            "expression": expression,
            "predictions": predictions.tolist() if hasattr(predictions, 'tolist') else predictions,
            "details": {}
        }
    
    def _fallback_expression(self, X: np.ndarray, y: np.ndarray) -> str:
        x1, x2, x3, x4 = X[:, 0], X[:, 1], X[:, 2], X[:, 3]
        
        features = np.column_stack([
            x1, x2, x3, x4,
            x1*x2, x1*x3, x1*x4, x2*x3, x2*x4, x3*x4,
            x1**2, x2**2, x3**2, x4**2,
            np.exp(-x1**2), np.exp(-x2**2), np.exp(-x3**2), np.exp(-x4**2),
            np.sin(x1), np.sin(x2), np.sin(x3), np.sin(x4),
            np.cos(x1), np.cos(x2), np.cos(x3), np.cos(x4),
            np.log(np.abs(x1) + 1e-6), np.log(np.abs(x2) + 1e-6),
            np.log(np.abs(x3) + 1e-6), np.log(np.abs(x4) + 1e-6)
        ])
        
        coeffs, _, _, _ = np.linalg.lstsq(features, y, rcond=None)
        
        terms = []
        term_names = [
            'x1', 'x2', 'x3', 'x4',
            'x1*x2', 'x1*x3', 'x1*x4', 'x2*x3', 'x2*x4', 'x3*x4',
            'x1**2', 'x2**2', 'x3**2', 'x4**2',
            'exp(-x1**2)', 'exp(-x2**2)', 'exp(-x3**2)', 'exp(-x4**2)',
            'sin(x1)', 'sin(x2)', 'sin(x3)', 'sin(x4)',
            'cos(x1)', 'cos(x2)', 'cos(x3)', 'cos(x4)',
            'log(abs(x1)+1e-6)', 'log(abs(x2)+1e-6)',
            'log(abs(x3)+1e-6)', 'log(abs(x4)+1e-6)'
        ]
        
        for coef, name in zip(coeffs, term_names):
            if abs(coef) > 1e-6:
                terms.append(f"({coef:.10f})*({name})")
        
        if not terms:
            terms = ["0"]
        
        return " + ".join(terms)
    
    def _evaluate_expression(self, expression: str, X: np.ndarray) -> np.ndarray:
        x1 = X[:, 0]
        x2 = X[:, 1]
        x3 = X[:, 2]
        x4 = X[:, 3]
        
        try:
            return eval(expression, {
                'x1': x1, 'x2': x2, 'x3': x3, 'x4': x4,
                'sin': np.sin, 'cos': np.cos, 'exp': np.exp, 'log': np.log,
                'abs': np.abs, 'np': np
            })
        except Exception:
            try:
                expr = sympy.sympify(expression)
                func = sympy.lambdify(['x1', 'x2', 'x3', 'x4'], expr, modules='numpy')
                return func(x1, x2, x3, x4)
            except Exception:
                return np.zeros(len(X))