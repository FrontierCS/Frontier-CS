import numpy as np
from pysr import PySRRegressor
import sympy

class Solution:
    def __init__(self, **kwargs):
        pass

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        """
        Perform symbolic regression using PySR with parameters optimized for
        the peaks-like function and given computational constraints.
        """
        # Configure PySR for the problem - optimized for CPU environment
        model = PySRRegressor(
            niterations=35,  # Reduced for faster convergence on CPU
            populations=12,  # Balanced for 8 vCPUs
            population_size=28,
            maxsize=22,  # Limit complexity to avoid overfitting
            binary_operators=["+", "-", "*", "/", "**"],
            unary_operators=["sin", "cos", "exp", "log"],
            verbosity=0,
            progress=False,
            random_state=42,
            ncycles_per_iteration=400,
            early_stop_condition=(
                "stop_if(loss, complexity) = loss < 1e-9 && complexity < 10"
            ),
            timeout_in_seconds=300,  # Limit training time
            deterministic=True,
            maxdepth=10,
            warm_start=True,
            temp_equation_file=True,
            tempdir="./",
            # Memory optimization for CPU environment
            turbo=True,
            # Complexity penalty to encourage simpler expressions
            parsimony=0.003,
            # Use all available CPUs efficiently
            procs=8,
            multithreading=True,
            cluster_manager=None,  # CPU-only, no cluster
            # Feature engineering hints for peaks function
            constraints={
                "**": (4, 2),  # Limit exponent nesting
                "log": 1,      # Limit log nesting
            },
            # Tournament selection for faster convergence
            tournament_selection_n=8,
            tournament_selection_p=0.86,
            weight_optimize=0.02,
            # Optimize for 2D input
            dimensionwise=False,
            # Memory limits
            optimizer_iterations=25,
        )
        
        try:
            # Fit the model
            model.fit(X, y, variable_names=["x1", "x2"])
            
            # Get the best expression
            best_expr = model.sympy()
            if best_expr is None:
                # Fallback to linear model if PySR fails
                return self._fallback_solution(X, y)
            
            # Convert to string and simplify
            expression_str = str(best_expr.simplify())
            
            # Ensure valid Python expression format
            expression_str = self._format_expression(expression_str)
            
            # Generate predictions
            predictions = model.predict(X)
            
            # Compute complexity
            complexity = self._compute_complexity(best_expr)
            
        except Exception:
            # If PySR fails, use polynomial approximation
            return self._polynomial_solution(X, y)
        
        return {
            "expression": expression_str,
            "predictions": predictions.tolist(),
            "details": {"complexity": complexity}
        }
    
    def _format_expression(self, expr_str: str) -> str:
        """Format expression to meet requirements."""
        # Replace any caret (^) with double asterisk (**)
        expr_str = expr_str.replace('^', '**')
        
        # Ensure function calls don't have 'np.' prefix
        expr_str = expr_str.replace('np.', '')
        
        # Replace any sympy function names if needed
        replacements = {
            'Abs': 'abs',
            'sqrt': 'sqrt',
            'exp': 'exp',
            'log': 'log',
            'sin': 'sin',
            'cos': 'cos',
        }
        
        for old, new in replacements.items():
            expr_str = expr_str.replace(old, new)
        
        return expr_str
    
    def _compute_complexity(self, expr) -> int:
        """Compute expression complexity as defined in scoring."""
        if hasattr(expr, 'count_ops'):
            # Use sympy's operation count
            op_count = expr.count_ops()
            # Count function calls (sin, cos, exp, log)
            func_count = 0
            if hasattr(expr, 'atoms'):
                funcs = [sympy.sin, sympy.cos, sympy.exp, sympy.log]
                for func in funcs:
                    func_count += len(list(expr.atoms(func)))
            # Approximate complexity: 2 * binary ops + unary ops
            complexity = 2 * (op_count - func_count) + func_count
            return max(1, complexity)
        return 1
    
    def _fallback_solution(self, X: np.ndarray, y: np.ndarray) -> dict:
        """Fallback to linear regression if PySR fails."""
        x1, x2 = X[:, 0], X[:, 1]
        
        # Simple linear combination
        A = np.column_stack([x1, x2, np.ones_like(x1)])
        coeffs, _, _, _ = np.linalg.lstsq(A, y, rcond=None)
        a, b, c = coeffs
        
        expression = f"{a:.6f}*x1 + {b:.6f}*x2 + {c:.6f}"
        predictions = a * x1 + b * x2 + c
        
        return {
            "expression": expression,
            "predictions": predictions.tolist(),
            "details": {"complexity": 2}  # 2 binary operations
        }
    
    def _polynomial_solution(self, X: np.ndarray, y: np.ndarray) -> dict:
        """Polynomial approximation for peaks-like function."""
        x1, x2 = X[:, 0], X[:, 1]
        
        # Create polynomial features up to degree 3
        # Terms: 1, x1, x2, x1^2, x1*x2, x2^2, x1^3, x1^2*x2, x1*x2^2, x2^3
        features = [
            np.ones_like(x1),
            x1, x2,
            x1**2, x1*x2, x2**2,
            x1**3, x1**2*x2, x1*x2**2, x2**3,
            np.exp(-x1**2 - x2**2),  # Gaussian term for peaks
            np.sin(x1)*np.cos(x2),   # Periodic component
        ]
        
        A = np.column_stack(features)
        coeffs, _, _, _ = np.linalg.lstsq(A, y, rcond=None)
        
        # Construct expression with only significant terms
        terms = []
        pred = np.zeros_like(y)
        threshold = 0.01 * np.abs(coeffs).max()  # Ignore small coefficients
        
        feature_names = [
            "1", "x1", "x2",
            "x1**2", "x1*x2", "x2**2",
            "x1**3", "x1**2*x2", "x1*x2**2", "x2**3",
            "exp(-x1**2 - x2**2)",
            "sin(x1)*cos(x2)"
        ]
        
        for i, (coef, name) in enumerate(zip(coeffs, feature_names)):
            if np.abs(coef) > threshold:
                if name == "1":
                    terms.append(f"{coef:.6f}")
                    pred += coef
                else:
                    terms.append(f"({coef:.6f})*({name})")
                    pred += coef * features[i]
        
        if not terms:
            expression = "0"
        else:
            expression = " + ".join(terms)
        
        # Compute complexity
        complexity = 0
        for term in terms:
            if '**' in term:
                complexity += 2  # binary operation
            elif '*' in term:
                complexity += 2
            elif 'exp' in term or 'sin' in term or 'cos' in term:
                complexity += 1  # unary operation
        
        return {
            "expression": expression,
            "predictions": pred.tolist(),
            "details": {"complexity": complexity}
        }