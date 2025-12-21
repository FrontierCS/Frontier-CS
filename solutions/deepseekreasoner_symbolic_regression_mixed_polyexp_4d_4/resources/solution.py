import numpy as np
from pysr import PySRRegressor
import sympy
from sklearn.linear_model import Ridge
from sklearn.preprocessing import PolynomialFeatures

class Solution:
    def __init__(self, **kwargs):
        pass

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        # Two-stage approach: first try PySR, fallback to polynomial if PySR fails
        try:
            # Configure PySR for 4D symbolic regression
            model = PySRRegressor(
                niterations=40,
                binary_operators=["+", "-", "*", "/", "**"],
                unary_operators=["sin", "cos", "exp", "log"],
                populations=8,  # Match CPU count
                population_size=35,
                maxsize=25,
                verbosity=0,
                progress=False,
                random_state=42,
                ncycles_per_iteration=700,
                early_stop_condition="stop_if(loss, complexity) = loss < 1e-9 && complexity < 10",
                model_selection="best",
                maxdepth=8,
                temp_annealing_rate=0.95,
                weight_optimize=0.02,
                deterministic=False,
                warm_start=False,
                use_frequency=True,
                use_custom_variable_names=True,
                variable_names=["x1", "x2", "x3", "x4"],
                constraints={
                    "**": (9, 9),  # Limit power complexity
                    "log": 9,
                    "exp": 9,
                },
                loss="L2DistLoss()",
                update=False,
                precision=64
            )
            
            # Fit model
            model.fit(X, y)
            
            # Get best expression
            best_expr = model.sympy()
            
            # Convert to string and clean up
            expr_str = str(best_expr)
            
            # Replace sympy function names if needed
            expr_str = expr_str.replace("sin", "sin")
            expr_str = expr_str.replace("cos", "cos")
            expr_str = expr_str.replace("exp", "exp")
            expr_str = expr_str.replace("log", "log")
            
            # Make sure variables are named correctly
            expr_str = expr_str.replace("x_1", "x1")
            expr_str = expr_str.replace("x_2", "x2")
            expr_str = expr_str.replace("x_3", "x3")
            expr_str = expr_str.replace("x_4", "x4")
            
            # Generate predictions
            try:
                predictions = model.predict(X).tolist()
            except:
                # Fallback prediction using sympy
                x1, x2, x3, x4 = sympy.symbols('x1 x2 x3 x4')
                func = sympy.lambdify((x1, x2, x3, x4), best_expr, 'numpy')
                predictions = func(X[:, 0], X[:, 1], X[:, 2], X[:, 3]).tolist()
            
            return {
                "expression": expr_str,
                "predictions": predictions,
                "details": {"complexity": self._calculate_complexity(expr_str)}
            }
            
        except Exception as e:
            # Fallback to polynomial regression with interaction terms
            return self._fallback_solution(X, y)
    
    def _calculate_complexity(self, expr_str: str) -> int:
        """Calculate expression complexity as defined in scoring."""
        complexity = 0
        # Count binary operators
        binary_ops = ['+', '-', '*', '/', '**']
        for op in binary_ops:
            complexity += 2 * expr_str.count(op)
        
        # Count unary operators (functions)
        unary_funcs = ['sin', 'cos', 'exp', 'log']
        for func in unary_funcs:
            complexity += expr_str.count(func)
        
        return complexity
    
    def _fallback_solution(self, X: np.ndarray, y: np.ndarray) -> dict:
        """Fallback solution using polynomial regression with interactions."""
        # Generate polynomial features up to degree 3 with interactions
        poly = PolynomialFeatures(degree=3, include_bias=False, interaction_only=False)
        X_poly = poly.fit_transform(X)
        
        # Use ridge regression to avoid overfitting
        model = Ridge(alpha=1.0, random_state=42)
        model.fit(X_poly, y)
        
        # Get feature names
        feature_names = poly.get_feature_names_out(['x1', 'x2', 'x3', 'x4'])
        
        # Build expression string
        terms = []
        for i, coef in enumerate(model.coef_):
            if abs(coef) > 1e-8:  # Only include significant terms
                terms.append(f"{coef:.6f}*{feature_names[i]}")
        
        if abs(model.intercept_) > 1e-8:
            terms.append(f"{model.intercept_:.6f}")
        
        if not terms:
            terms = ["0"]
        
        expression = " + ".join(terms)
        expression = expression.replace("+ -", "- ")
        expression = expression.replace("^", "**")
        
        # Generate predictions
        predictions = model.predict(X_poly).tolist()
        
        return {
            "expression": expression,
            "predictions": predictions,
            "details": {"complexity": self._calculate_complexity(expression), "fallback": True}
        }
