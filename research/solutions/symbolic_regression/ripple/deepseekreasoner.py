import numpy as np
from pysr import PySRRegressor

class Solution:
    def __init__(self, **kwargs):
        pass

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        # Configure PySR for ripple dataset
        model = PySRRegressor(
            niterations=80,
            binary_operators=["+", "-", "*", "/", "**"],
            unary_operators=["sin", "cos", "exp", "log"],
            populations=8,
            population_size=40,
            maxsize=35,
            maxdepth=12,
            early_stop_condition=(
                "stop_if(loss, complexity) = loss < 1e-9 && complexity < 20"
            ),
            timeout_in_seconds=None,
            deterministic=True,
            warm_start=True,
            verbosity=0,
            progress=False,
            random_state=42,
            multithreading=True,
            nested_constraints={
                "sin": ["sin", "cos", "exp", "log", "x1", "x2", "constant"],
                "cos": ["sin", "cos", "exp", "log", "x1", "x2", "constant"],
                "exp": ["sin", "cos", "exp", "log", "x1", "x2", "constant"],
                "log": ["x1", "x2", "constant", "+", "-", "*", "/", "**"]
            },
            complexity_of_operators={
                "sin": 3, "cos": 3, "exp": 3, "log": 3,
                "+": 1, "-": 1, "*": 2, "/": 2, "**": 4
            },
            complexity_of_constants=1,
            complexity_of_variables=0,
            weight_optimize=0.02,
            weight_simplify=0.02,
            use_frequency=True,
            use_frequency_in_tournament=True,
            adaptive_parsimony_scaling=50.0,
            parsimony=1e-4,
            tournament_selection_p=0.86,
            tournament_selection_n=7,
            hof_migration=True,
            should_optimize_constants=True,
            should_simplify=True,
            extra_sympy_mappings={'log': lambda x: f"log({x})"},
        )
        
        try:
            model.fit(X, y, variable_names=["x1", "x2"])
            
            # Get best expression
            best_expr = model.sympy()
            if best_expr is None:
                # Fallback to simplest valid expression
                best_expr_str = "0.0"
                predictions = np.zeros_like(y)
            else:
                best_expr_str = str(best_expr)
                # Clean up expression format
                best_expr_str = best_expr_str.replace("**", "^").replace("^", "**")
                predictions = model.predict(X)
        except Exception as e:
            # Fallback to polynomial approximation if PySR fails
            best_expr_str, predictions = self._fallback_solution(X, y)
        
        # Compute complexity
        complexity = self._compute_complexity(best_expr_str)
        
        return {
            "expression": best_expr_str,
            "predictions": predictions.tolist() if predictions is not None else None,
            "details": {"complexity": complexity}
        }
    
    def _fallback_solution(self, X: np.ndarray, y: np.ndarray):
        """Fallback solution using polynomial regression with trigonometric terms"""
        x1, x2 = X[:, 0], X[:, 1]
        
        # Build feature matrix with polynomial and trigonometric terms
        features = []
        feature_names = []
        
        # Polynomial terms up to degree 3
        for i in range(4):
            for j in range(4-i):
                if i == 0 and j == 0:
                    continue
                features.append((x1**i) * (x2**j))
                feature_names.append(f"x1**{i}*x2**{j}")
        
        # Trigonometric terms
        for freq in [1.0, 2.0, 3.0, 4.0]:
            features.append(np.sin(freq * x1))
            feature_names.append(f"sin({freq}*x1)")
            features.append(np.cos(freq * x1))
            feature_names.append(f"cos({freq}*x1)")
            features.append(np.sin(freq * x2))
            feature_names.append(f"sin({freq}*x2)")
            features.append(np.cos(freq * x2))
            feature_names.append(f"cos({freq}*x2)")
        
        # Cross terms with trigonometry
        for freq in [1.0, 2.0]:
            features.append(np.sin(freq * np.sqrt(x1**2 + x2**2)))
            feature_names.append(f"sin({freq}*sqrt(x1**2+x2**2))")
        
        # Add constant term
        features.append(np.ones_like(x1))
        feature_names.append("1")
        
        A = np.column_stack(features)
        
        # Solve with regularization
        try:
            coeffs = np.linalg.lstsq(A, y, rcond=1e-6)[0]
            
            # Build expression string
            terms = []
            for i, (coeff, name) in enumerate(zip(coeffs, feature_names)):
                if abs(coeff) > 1e-10:
                    if name == "1":
                        terms.append(f"{coeff:.10f}")
                    else:
                        terms.append(f"({coeff:.10f})*{name}")
            
            if not terms:
                expression = "0.0"
            else:
                expression = " + ".join(terms)
            
            predictions = A @ coeffs
            
        except np.linalg.LinAlgError:
            # Ultimate fallback: simple linear model
            A_simple = np.column_stack([x1, x2, np.ones_like(x1)])
            coeffs = np.linalg.lstsq(A_simple, y, rcond=None)[0]
            expression = f"{coeffs[0]:.10f}*x1 + {coeffs[1]:.10f}*x2 + {coeffs[2]:.10f}"
            predictions = A_simple @ coeffs
        
        return expression, predictions
    
    def _compute_complexity(self, expression: str) -> int:
        """Compute expression complexity according to scoring formula"""
        if not expression or expression == "0.0":
            return 0
            
        # Count operators and functions
        binary_ops = expression.count('+') + expression.count('-') + \
                     expression.count('*') + expression.count('/') + \
                     expression.count('**')
        
        unary_ops = expression.count('sin(') + expression.count('cos(') + \
                   expression.count('exp(') + expression.count('log(')
        
        # Note: Some counts might be inflated due to nested expressions
        # This is a simplified approximation
        complexity = 2 * binary_ops + unary_ops
        return max(0, complexity)