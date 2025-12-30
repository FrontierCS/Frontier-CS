import numpy as np
from pysr import PySRRegressor
import sympy

class Solution:
    def __init__(self, **kwargs):
        pass

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        
        def fallback():
            mean_y = np.mean(y)
            expression = f"{mean_y:.8f}"
            predictions = np.full(y.shape, mean_y)
            return {
                "expression": expression,
                "predictions": predictions.tolist(),
                "details": {}
            }

        model = PySRRegressor(
            niterations=75,
            populations=30,
            population_size=45,
            binary_operators=["+", "-", "*", "/", "pow"],
            unary_operators=["sin", "cos"],
            maxsize=32,
            complexity_of_operators={
                "/": 2, 
                "pow": 2, 
                "sin": 2, 
                "cos": 2
            },
            nested_constraints={
                "sin": {"sin": 0, "cos": 0},
                "cos": {"sin": 0, "cos": 0},
            },
            procs=8,
            random_state=42,
            verbosity=0,
            progress=False,
        )
        
        try:
            model.fit(X, y, variable_names=["x1", "x2"])
        except Exception:
            return fallback()

        if not hasattr(model, 'equations_') or model.equations_.shape[0] == 0:
            return fallback()

        try:
            best_equation = model.get_best()
            complexity = int(best_equation['complexity'])
            
            sympy_expr = model.sympy()
            expression = str(sympy_expr)
            
            predictions = model.predict(X)

            return {
                "expression": expression,
                "predictions": predictions.tolist(),
                "details": {"complexity": complexity}
            }
        except (IndexError, RuntimeError):
            return fallback()