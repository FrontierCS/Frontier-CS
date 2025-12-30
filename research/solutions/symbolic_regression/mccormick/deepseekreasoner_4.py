import numpy as np
from pysr import PySRRegressor
import sympy as sp

class Solution:
    def __init__(self, **kwargs):
        pass

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        model = PySRRegressor(
            niterations=60,
            binary_operators=["+", "-", "*", "/", "**"],
            unary_operators=["sin", "cos", "exp", "log"],
            populations=12,
            population_size=40,
            maxsize=30,
            ncycles_per_iteration=700,
            verbosity=0,
            progress=False,
            random_state=42,
            deterministic=True,
            early_stop_condition=(
                "stop_if(loss, complexity) = loss < 1e-9 && complexity < 10"
            ),
            constraints={
                "**": (9, 2),
                "log": 9,
                "exp": 9,
            },
            complexity_of_operators={
                "sin": 3, "cos": 3, "exp": 3, "log": 3,
                "+": 1, "-": 1, "*": 1, "/": 1, "**": 2
            },
            maxdepth=10,
            weight_optimize=0.02,
            warm_start=True,
            turbo=True,
            model_selection="accuracy",
            loss="loss(x, y) = (x - y)^2",
            extra_sympy_mappings={"log": lambda x: sp.log(sp.Abs(x))},
            precision=64
        )
        
        model.fit(X, y, variable_names=["x1", "x2"])
        
        best_expr = model.sympy()
        if best_expr is None:
            best_expr = sp.sympify("x1 + x2")
        
        simplified = sp.simplify(best_expr)
        expression = str(simplified).replace("Abs", "").replace("(", "").replace(")", "")
        
        x1_sym, x2_sym = sp.symbols("x1 x2")
        expr_func = sp.lambdify((x1_sym, x2_sym), simplified, modules="numpy")
        predictions = expr_func(X[:, 0], X[:, 1])
        
        tree = model.equations_.iloc[-1]["tree"]
        binary_ops = 0
        unary_ops = 0
        if hasattr(tree, "__iter__"):
            for node in tree:
                if node is None:
                    continue
                if isinstance(node, dict):
                    if node.get("op") in ["+", "-", "*", "/", "**"]:
                        binary_ops += 1
                    elif node.get("op") in ["sin", "cos", "exp", "log"]:
                        unary_ops += 1
        
        complexity = 2 * binary_ops + unary_ops
        
        return {
            "expression": expression,
            "predictions": predictions.tolist(),
            "details": {"complexity": complexity}
        }