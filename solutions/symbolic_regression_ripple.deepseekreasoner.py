import numpy as np
import sympy as sp
from pysr import PySRRegressor
from typing import Dict, Any
import warnings

class Solution:
    def __init__(self, **kwargs):
        pass

    def solve(self, X: np.ndarray, y: np.ndarray) -> Dict[str, Any]:
        # Suppress warnings for cleaner output
        warnings.filterwarnings('ignore')
        
        # Extract features
        x1 = X[:, 0]
        x2 = X[:, 1]
        
        # Configure PySR for ripple-like function
        model = PySRRegressor(
            niterations=100,
            binary_operators=["+", "-", "*", "/", "**"],
            unary_operators=["sin", "cos", "exp", "log"],
            populations=20,
            population_size=50,
            maxsize=30,
            parsimony=0.001,
            warming_up=True,
            warm_start=True,
            verbosity=0,
            progress=False,
            random_state=42,
            model_selection="best",
            loss="L2DistLoss()",
            turbo=True,
            early_stop_condition=(
                "stop_if(loss, complexity) = (loss < 0.001 && complexity < 15) ||"
                "(loss < 0.0001 && complexity < 20)"
            ),
            complexity_of_operators={
                "+": 1, "-": 1, "*": 1, "/": 1, "**": 2,
                "sin": 3, "cos": 3, "exp": 3, "log": 3
            },
            nested_constraints={
                "sin": {"sin": 0, "cos": 0, "exp": 0, "log": 0},
                "cos": {"sin": 0, "cos": 0, "exp": 0, "log": 0},
                "exp": {"sin": 0, "cos": 0, "exp": 0, "log": 0},
                "log": {"sin": 0, "cos": 0, "exp": 0, "log": 0},
            },
            maxdepth=None,
            deterministic=True,
            weight_optimize=0.02,
            weight_simplify=0.01,
            weight_randomize=0.005,
        )
        
        # Fit the model
        try:
            model.fit(X, y, variable_names=["x1", "x2"])
            
            # Get best expression
            best_eq = model.equations_.iloc[-1]
            expression = str(best_eq["sympy_format"])
            
            # Clean up expression
            expression = expression.replace("**", "^")
            expression = expression.replace("^", "**")
            
            # Ensure it's a valid expression string
            try:
                # Test evaluation
                test_expr = sp.sympify(expression)
                # Replace sympy functions with plain python
                expr_str = str(test_expr)
                expr_str = expr_str.replace("sin", "np.sin")
                expr_str = expr_str.replace("cos", "np.cos")
                expr_str = expr_str.replace("exp", "np.exp")
                expr_str = expr_str.replace("log", "np.log")
                
                # Final test with numpy
                test_func = eval(f"lambda x1, x2: {expr_str}")
                test_pred = test_func(x1, x2)
                
                # If test passes, use cleaned expression
                expression = expr_str.replace("np.", "")
            except:
                # Fallback to raw expression
                pass
                
            # Get predictions
            predictions = model.predict(X).tolist()
            
            # Calculate complexity
            eq_complexity = int(best_eq["complexity"])
            
        except Exception as e:
            # Fallback: Fit a polynomial model with trigonometric terms
            # This handles cases where PySR fails
            expression, predictions, eq_complexity = self._fallback_fit(X, y)
        
        return {
            "expression": expression,
            "predictions": predictions,
            "details": {"complexity": eq_complexity}
        }
    
    def _fallback_fit(self, X: np.ndarray, y: np.ndarray):
        """Fallback fitting method using feature engineering and linear regression"""
        x1 = X[:, 0]
        x2 = X[:, 1]
        
        # Create feature matrix with potential ripple terms
        features = []
        feature_names = []
        
        # Basic terms
        features.extend([x1, x2, x1**2, x2**2, x1*x2])
        feature_names.extend(['x1', 'x2', 'x1**2', 'x2**2', 'x1*x2'])
        
        # Distance from origin (for concentric patterns)
        r = np.sqrt(x1**2 + x2**2)
        features.extend([r, r**2, r**3])
        feature_names.extend(['r', 'r**2', 'r**3'])
        
        # Trigonometric terms (ripple patterns)
        features.extend([np.sin(r), np.cos(r), np.sin(2*r), np.cos(2*r)])
        feature_names.extend(['sin(r)', 'cos(r)', 'sin(2*r)', 'cos(2*r)'])
        
        # Angular terms
        theta = np.arctan2(x2, x1)
        features.extend([np.sin(theta), np.cos(theta), np.sin(2*theta), np.cos(2*theta)])
        feature_names.extend(['sin(theta)', 'cos(theta)', 'sin(2*theta)', 'cos(2*theta)'])
        
        # Mixed terms
        features.extend([r*np.sin(r), r*np.cos(r), x1*np.sin(r), x2*np.cos(r)])
        feature_names.extend(['r*sin(r)', 'r*cos(r)', 'x1*sin(r)', 'x2*cos(r)'])
        
        # Exponential decay (for amplitude modulation)
        features.extend([np.exp(-r), np.exp(-r**2)])
        feature_names.extend(['exp(-r)', 'exp(-r**2)'])
        
        # Stack features
        A = np.column_stack(features)
        
        # Add intercept
        A = np.column_stack([A, np.ones_like(x1)])
        feature_names.append('1')
        
        # Solve with regularization (Ridge regression)
        try:
            # Try ridge regression first
            alpha = 0.1
            coeffs = np.linalg.lstsq(A.T @ A + alpha * np.eye(A.shape[1]), A.T @ y, rcond=None)[0]
        except:
            # Fall back to ordinary least squares
            coeffs = np.linalg.lstsq(A, y, rcond=None)[0]
        
        # Build expression string
        terms = []
        for i, (coeff, name) in enumerate(zip(coeffs, feature_names)):
            if abs(coeff) > 1e-10:  # Only include significant terms
                if i == len(coeffs) - 1:  # Constant term
                    terms.append(f"{coeff:.6f}")
                else:
                    terms.append(f"({coeff:.6f})*({name})")
        
        if not terms:
            expression = "0"
            predictions = np.zeros_like(y).tolist()
        else:
            expression = " + ".join(terms)
            # Clean up the expression
            expression = expression.replace("r", "sqrt(x1**2 + x2**2)")
            expression = expression.replace("theta", "arctan2(x2, x1)")
        
        # Calculate predictions
        try:
            pred_func = eval(f"lambda x1, x2: {expression}")
            predictions = pred_func(x1, x2).tolist()
        except:
            predictions = (A @ coeffs).tolist()
        
        # Estimate complexity (simplified count)
        complexity = expression.count('+') + expression.count('-') + expression.count('*') + \
                     expression.count('/') + 2*expression.count('**') + \
                     3*expression.count('sin') + 3*expression.count('cos') + \
                     3*expression.count('exp') + 3*expression.count('log') + \
                     3*expression.count('sqrt') + 3*expression.count('arctan2')
        
        return expression, predictions, complexity
