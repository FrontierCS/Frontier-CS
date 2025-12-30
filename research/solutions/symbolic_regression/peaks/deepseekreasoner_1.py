import numpy as np
from pysr import PySRRegressor
import sympy

class Solution:
    def __init__(self, **kwargs):
        pass

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        model = PySRRegressor(
            niterations=100,
            binary_operators=["+", "-", "*", "/", "**"],
            unary_operators=["sin", "cos", "exp", "log"],
            populations=20,
            population_size=50,
            maxsize=30,
            ncycles_per_iteration=8,
            parsimony=0.003,
            annealing=True,
            use_frequency=False,
            use_custom_variable_names=True,
            variable_names=["x1", "x2"],
            verbosity=0,
            progress=False,
            random_state=42,
            deterministic=True,
            early_stop_condition=("stop_if(loss, complexity) = loss < 1e-12 && complexity < 20", 50, 10),
            timeout_in_seconds=None,
            warm_start=True,
            update_test_loss=True,
            precision=64,
            multithreading=True,
            cluster_manager=None,
            equation_file=None,
            temp_equation_file=True,
            delete_tempfiles=True,
            extra_sympy_mappings={"log": lambda x: sympy.log(sympy.Abs(x) + 1e-12)},
            extra_torch_mappings={},
            output_torch_format=False,
            denoise=True,
            select_k_features=None,
            weight_optimize=None,
            weight_optimize_steps=100,
            weight_optimize_iterations=3,
            optimise_constraints={"min": -1e12, "max": 1e12},
            should_optimize_constants=True,
            should_simplify=False,
            turbo=True,
            batching=False,
            batch_size=50,
            fast_cycle=False,
            complexity_of_operators={"**": 3, "exp": 2, "log": 2},
            complexity_of_constants=1,
            constraints={},
            nested_constraints={},
            maxdepth=None,
            elementwise_loss=None,
            loss="loss(x, y) = (x - y)^2",
            tournament_selection_n=10,
            tournament_selection_p=0.86,
            fractional_simplification=[1.0, 1.0, 1.0, 1.0],
            enable_autodiff=False,
        )
        
        model.fit(X, y)
        
        best_expr = model.sympy()
        if isinstance(best_expr, list):
            best_expr = best_expr[0]
        
        expression = str(best_expr).replace("Abs", "").replace("(", "").replace(")", "")
        
        try:
            predictions = model.predict(X).tolist()
        except:
            predictions = None
        
        complexity = 0
        expr_str = expression
        binary_ops = ["+", "-", "*", "/", "**"]
        unary_ops = ["sin", "cos", "exp", "log"]
        
        for op in binary_ops:
            complexity += 2 * expr_str.count(op)
        for op in unary_ops:
            complexity += expr_str.count(op)
        
        return {
            "expression": expression,
            "predictions": predictions,
            "details": {"complexity": complexity}
        }