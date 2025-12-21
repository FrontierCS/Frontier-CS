import numpy as np
from pysr import PySRRegressor
import sympy

class Solution:
    def __init__(self, **kwargs):
        pass

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        model = PySRRegressor(
            niterations=40,
            binary_operators=["+", "-", "*", "/", "**"],
            unary_operators=["sin", "cos", "exp", "log"],
            populations=15,
            population_size=33,
            maxsize=30,
            model_selection="best",
            temp_equation_file=False,
            verbosity=0,
            progress=False,
            random_state=42,
            deterministic=True,
            max_depth=10,
            early_stop_condition="stop_if(loss, complexity) = loss < 1e-6 && complexity < 10",
            nested_constraints={"log": {"log": 0}},
            extra_sympy_mappings={},
            constraints={"**": (9, 2)},
            weight_optimize=0.01,
        )
        
        try:
            model.fit(X, y, variable_names=["x1", "x2"])
        except Exception:
            # Fallback to polynomial fit if PySR fails
            return self._fallback_fit(X, y)
        
        try:
            best_expr = model.sympy()
            if best_expr is None:
                return self._fallback_fit(X, y)
            
            # Simplify expression
            expr_str = str(best_expr)
            
            # Replace any np.* or math.* functions
            expr_str = expr_str.replace("np.", "").replace("math.", "")
            
            # Ensure x1, x2 are used
            if "x1" not in expr_str and "x2" not in expr_str:
                return self._fallback_fit(X, y)
                
            # Get predictions
            predictions = model.predict(X)
            
            # Calculate complexity
            complexity = self._calculate_complexity(str(best_expr))
            
            return {
                "expression": expr_str,
                "predictions": predictions.tolist(),
                "details": {"complexity": complexity}
            }
            
        except Exception:
            return self._fallback_fit(X, y)
    
    def _fallback_fit(self, X: np.ndarray, y: np.ndarray) -> dict:
        """Fallback to polynomial regression if PySR fails."""
        x1, x2 = X[:, 0], X[:, 1]
        
        # Try polynomial features up to degree 3
        features = []
        feature_names = []
        
        # Add linear terms
        features.append(x1)
        features.append(x2)
        feature_names.extend(["x1", "x2"])
        
        # Add polynomial terms up to degree 3
        for i in range(2, 4):
            for j in range(i + 1):
                if j <= i:
                    feat = (x1 ** (i - j)) * (x2 ** j)
                    features.append(feat)
                    feature_names.append(f"x1**{i-j}*x2**{j}")
        
        # Add trigonometric terms
        for func in [np.sin, np.cos]:
            features.append(func(x1))
            features.append(func(x2))
            features.append(func(x1 + x2))
            feature_names.extend([f"{func.__name__}(x1)", f"{func.__name__}(x2)", f"{func.__name__}(x1+x2)"])
        
        # Add interaction terms
        features.append(x1 * x2)
        features.append(x1 * np.sin(x2))
        features.append(x2 * np.sin(x1))
        feature_names.extend(["x1*x2", "x1*sin(x2)", "x2*sin(x1)"])
        
        A = np.column_stack(features)
        
        # Add intercept
        A = np.column_stack([A, np.ones_like(x1)])
        feature_names.append("1")
        
        # Solve with ridge regression for stability
        coeffs = np.linalg.lstsq(A, y, rcond=1e-10)[0]
        
        # Build expression string
        terms = []
        for coef, name in zip(coeffs[:-1], feature_names):
            if abs(coef) > 1e-10:
                sign = "+" if coef >= 0 else "-"
                term = f"{sign}{abs(coef):.6f}*{name}"
                terms.append(term)
        
        # Add intercept
        if abs(coeffs[-1]) > 1e-10:
            sign = "+" if coeffs[-1] >= 0 else "-"
            terms.append(f"{sign}{abs(coeffs[-1]):.6f}")
        
        expr = " ".join(terms).strip()
        if expr.startswith("+"):
            expr = expr[1:].strip()
        
        predictions = A @ coeffs
        complexity = self._calculate_complexity(expr)
        
        return {
            "expression": expr,
            "predictions": predictions.tolist(),
            "details": {"complexity": complexity}
        }
    
    def _calculate_complexity(self, expr_str: str) -> int:
        """Calculate expression complexity."""
        complexity = 0
        
        # Count binary operators
        binary_ops = ["+", "-", "*", "/", "**"]
        for op in binary_ops:
            complexity += 2 * expr_str.count(op)
        
        # Count unary functions
        unary_funcs = ["sin", "cos", "exp", "log"]
        for func in unary_funcs:
            complexity += expr_str.count(func)
        
        return max(1, complexity)
