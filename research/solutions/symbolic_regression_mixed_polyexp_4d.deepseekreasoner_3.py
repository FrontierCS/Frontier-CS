import numpy as np
from pysr import PySRRegressor

class Solution:
    def __init__(self, **kwargs):
        pass

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        model = PySRRegressor(
            niterations=200,
            binary_operators=["+", "-", "*", "/", "**"],
            unary_operators=["exp", "log", "sin", "cos"],
            populations=15,
            population_size=40,
            maxsize=35,
            max_depth=12,
            warm_start=True,
            ncycles_per_iteration=800,
            timeout_in_seconds=60 * 5,
            early_stop_condition=1e-10,
            verbosity=0,
            progress=False,
            random_state=42,
            deterministic=True,
            loss="loss(x, y) = (x - y)^2",
            constraints={
                "**": (9, 2),
                "log": 1,
                "exp": 4,
                "sin": 2,
                "cos": 2
            },
            complexity_of_operators={
                "**": 3,
                "exp": 2,
                "log": 2,
                "sin": 2,
                "cos": 2
            },
            turbo=True,
            batching=True,
            batch_size=min(500, len(y)),
            should_optimize_constants=True,
            weight_optimize=0.02,
            update=False,
            model_selection="accuracy",
            extra_sympy_mappings={"exp": (lambda x: np.exp(x), "exp")}
        )
        
        try:
            model.fit(X, y, variable_names=["x1", "x2", "x3", "x4"])
            best_expr = model.sympy()
            expression = str(best_expr).replace("**", "^").replace("^", "**")
            predictions = model.predict(X)
        except Exception:
            # Fallback to optimized polynomial with exponential terms
            x1, x2, x3, x4 = X[:, 0], X[:, 1], X[:, 2], X[:, 3]
            features = np.column_stack([
                x1, x2, x3, x4,
                x1*x2, x1*x3, x1*x4, x2*x3, x2*x4, x3*x4,
                x1**2, x2**2, x3**2, x4**2,
                x1*x2*x3, x1*x2*x4, x1*x3*x4, x2*x3*x4,
                np.exp(-x1**2), np.exp(-x2**2), np.exp(-x3**2), np.exp(-x4**2),
                np.exp(-x1*x2), np.exp(-x1*x3), np.exp(-x1*x4),
                np.exp(-x2*x3), np.exp(-x2*x4), np.exp(-x3*x4),
                np.sin(x1), np.cos(x1), np.sin(x2), np.cos(x2),
                np.sin(x3), np.cos(x3), np.sin(x4), np.cos(x4),
                np.ones_like(x1)
            ])
            coeffs, _, _, _ = np.linalg.lstsq(features, y, rcond=None)
            
            # Build expression string from significant terms
            terms = []
            feature_names = [
                "x1", "x2", "x3", "x4",
                "x1*x2", "x1*x3", "x1*x4", "x2*x3", "x2*x4", "x3*x4",
                "x1**2", "x2**2", "x3**2", "x4**2",
                "x1*x2*x3", "x1*x2*x4", "x1*x3*x4", "x2*x3*x4",
                "exp(-x1**2)", "exp(-x2**2)", "exp(-x3**2)", "exp(-x4**2)",
                "exp(-x1*x2)", "exp(-x1*x3)", "exp(-x1*x4)",
                "exp(-x2*x3)", "exp(-x2*x4)", "exp(-x3*x4)",
                "sin(x1)", "cos(x1)", "sin(x2)", "cos(x2)",
                "sin(x3)", "cos(x3)", "sin(x4)", "cos(x4)",
                "1"
            ]
            for coef, name in zip(coeffs, feature_names):
                if abs(coef) > 1e-6:
                    terms.append(f"({coef:.8f})*{name}")
            expression = " + ".join(terms) if terms else "0"
            predictions = features @ coeffs
        
        # Validate expression uses only allowed operations
        allowed_funcs = ["sin", "cos", "exp", "log"]
        allowed_ops = ["+", "-", "*", "/", "**"]
        try:
            # Replace constants with 1 for validation
            import re
            test_expr = re.sub(r"\d*\.?\d+", "1", expression)
            # Remove whitespace
            test_expr = test_expr.replace(" ", "")
            # Check for disallowed functions
            for func in ["np.", "sqrt", "tan", "arc", "asin", "acos", "atan"]:
                if func in test_expr:
                    raise ValueError(f"Disallowed function: {func}")
        except:
            # If expression is invalid, use simple polynomial
            x1, x2, x3, x4 = X[:, 0], X[:, 1], X[:, 2], X[:, 3]
            features = np.column_stack([x1, x2, x3, x4, x1*x2, x1*x3, x1*x4, x2*x3, x2*x4, x3*x4, np.ones_like(x1)])
            coeffs, _, _, _ = np.linalg.lstsq(features, y, rcond=None)
            terms = []
            for i, name in enumerate(["x1", "x2", "x3", "x4", "x1*x2", "x1*x3", "x1*x4", "x2*x3", "x2*x4", "x3*x4", "1"]):
                if abs(coeffs[i]) > 1e-6:
                    terms.append(f"({coeffs[i]:.8f})*{name}")
            expression = " + ".join(terms) if terms else "0"
            predictions = features @ coeffs
        
        # Ensure predictions is a list
        if hasattr(predictions, 'tolist'):
            predictions = predictions.tolist()
        
        return {
            "expression": expression,
            "predictions": predictions,
            "details": {}
        }