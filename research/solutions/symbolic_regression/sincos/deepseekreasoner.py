import numpy as np
from pysr import PySRRegressor

class Solution:
    def __init__(self, **kwargs):
        pass

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        model = PySRRegressor(
            niterations=40,
            binary_operators=["+", "-", "*", "/"],
            unary_operators=["sin", "cos", "exp", "log"],
            populations=15,
            population_size=33,
            maxsize=25,
            verbosity=0,
            progress=False,
            random_state=42,
            ncycles_per_iteration=400,
            early_stop_condition=1e-6,
            temp_equation_file=False,
            tempdir=None,
            update=False,
            deterministic=True,
            extra_sympy_mappings={},
            weight_optimize=0.02,
            procs=8
        )
        
        model.fit(X, y, variable_names=["x1", "x2"])
        
        expression = str(model.sympy())
        predictions = model.predict(X).tolist()
        
        return {
            "expression": expression,
            "predictions": predictions,
            "details": {}
        }