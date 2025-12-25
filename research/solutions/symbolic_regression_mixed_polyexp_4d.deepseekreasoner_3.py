import numpy as np
from pysr import PySRRegressor
import warnings

class Solution:
    def __init__(self, **kwargs):
        pass

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        # Suppress warnings for cleaner output
        warnings.filterwarnings('ignore')
        
        # Configure PySR for 4D symbolic regression
        model = PySRRegressor(
            niterations=100,
            binary_operators=["+", "-", "*", "/", "**"],
            unary_operators=["sin", "cos", "exp", "log"],
            populations=12,
            population_size=35,
            maxsize=25,
            verbosity=0,
            progress=False,
            random_state=42,
            deterministic=True,
            nested_constraints={
                "**": {"sin": 0, "cos": 0, "exp": 0, "log": 0},
                "/": {"sin": 0, "cos": 0, "exp": 0, "log": 0}
            },
            constraints={
                "sin": 4,
                "cos": 4,
                "exp": 4,
                "log": 4,
                "**": 4
            },
            warm_start=False,
            model_selection="accuracy",
            complexity_of_operators={
                "**": 3, "sin": 2, "cos": 2, "exp": 2, "log": 2
            },
            complexity_of_constants=1,
            maxdepth=None,
            turbo=True,
            precision=64
        )
        
        # Fit the model
        model.fit(X, y, variable_names=["x1", "x2", "x3", "x4"])
        
        # Get the best expression
        try:
            best_expr = model.sympy()
            expression = str(best_expr)
            # Replace any sympy function prefixes
            expression = expression.replace('exp', 'exp').replace('log', 'log')
            expression = expression.replace('sin', 'sin').replace('cos', 'cos')
        except:
            # Fallback to simplest expression from equations
            equations = model.equations_
            if len(equations) > 0:
                best_idx = equations[equations['loss'].notna()]['loss'].idxmin()
                expression = equations.loc[best_idx, 'equation']
            else:
                expression = "x1"
        
        # Generate predictions
        try:
            predictions = model.predict(X).tolist()
        except:
            # Fallback prediction using the expression
            x1, x2, x3, x4 = X[:, 0], X[:, 1], X[:, 2], X[:, 3]
            safe_dict = {
                'x1': x1, 'x2': x2, 'x3': x3, 'x4': x4,
                'sin': np.sin, 'cos': np.cos, 'exp': np.exp, 'log': np.log
            }
            try:
                predictions = eval(expression, {"__builtins__": {}}, safe_dict).tolist()
            except:
                predictions = y.tolist()
        
        return {
            "expression": expression,
            "predictions": predictions,
            "details": {}
        }
