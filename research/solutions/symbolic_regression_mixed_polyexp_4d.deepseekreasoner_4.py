import numpy as np
from pysr import PySRRegressor

class Solution:
    def __init__(self, **kwargs):
        pass

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        model = PySRRegressor(
            niterations=30,
            binary_operators=["+", "-", "*", "/", "**"],
            unary_operators=["sin", "cos", "exp", "log"],
            populations=12,
            population_size=25,
            maxsize=20,
            parsimony=0.02,
            verbosity=0,
            progress=False,
            random_state=42,
            deterministic=True,
            early_stop_condition=("stop_if(loss, complexity) = loss < 1e-8 && complexity < 12", 25),
            timeout_in_seconds=120,
            max_evals=200000,
            warm_start=True,
            nested_constraints={"**": {"**": 1}},
            constraints={"**": (9, 1)},
            batching=True,
            batch_size=500,
            turbo=True,
            ncycles_per_iteration=700,
            extra_sympy_mappings={"log": lambda x: f"log({x})"}
        )
        
        model.fit(X, y, variable_names=["x1", "x2", "x3", "x4"])
        
        best_expr = model.sympy()
        expression = str(best_expr)
        
        try:
            predictions = model.predict(X)
        except:
            predictions = None
        
        complexity = len(model.equations_) if hasattr(model, 'equations_') else None
        
        return {
            "expression": expression,
            "predictions": predictions.tolist() if predictions is not None else None,
            "details": {"complexity": complexity}
        }