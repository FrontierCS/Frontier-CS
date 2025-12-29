import numpy as np
from pysr import PySRRegressor

class Solution:
    def __init__(self, **kwargs):
        pass

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        # Configure PySR for efficient CPU execution
        model = PySRRegressor(
            niterations=30,
            binary_operators=["+", "-", "*", "/", "**"],
            unary_operators=["sin", "cos", "exp", "log"],
            populations=8,
            population_size=20,
            maxsize=15,
            early_stop_condition=(
                "stop_if(loss, complexity) = loss < 1e-6 && complexity < 10"
            ),
            deterministic=True,
            verbosity=0,
            progress=False,
            random_state=42,
            multithreading=True,
            turbo=True,
            warm_start=False,
            optimizer_algorithm="BFGS",
            optimizer_iterations=10,
            model_selection="best",
            loss="L2DistLoss()",
            complexity_of_operators={
                "+": 1, "-": 1, "*": 1, "/": 1, "**": 2,
                "sin": 2, "cos": 2, "exp": 2, "log": 2
            },
            use_frequency=True,
            optimizer_nrestarts=2,
            should_optimize_constants=True,
            weight_add_node=0.01,
            weight_insert_node=0.01,
            weight_delete_node=0.005,
            weight_do_nothing=0.05,
            weight_mutate_constant=0.15,
            weight_mutate_operator=0.15,
            weight_swap_operands=0.1,
            weight_simplify=0.02,
            weight_randomize=0.005,
            weight_optimize=0.1,
        )

        # Fit model
        model.fit(X, y, variable_names=["x1", "x2"])

        # Get best expression
        try:
            expression = str(model.sympy())
        except:
            # Fallback to best equation from equations_
            best_eq = model.equations_.iloc[model.equations_["loss"].argmin()]
            expression = best_eq["equation"]

        # Clean up expression formatting
        expression = expression.replace(" ", "").replace("np.", "")

        # Ensure variable names are x1 and x2
        expression = expression.replace("x0", "x1").replace("x1", "x1").replace("x2", "x2")

        # Generate predictions
        try:
            predictions = model.predict(X).tolist()
        except:
            # Manual evaluation fallback
            x1 = X[:, 0]
            x2 = X[:, 1]
            predictions = eval(expression, {"x1": x1, "x2": x2,
                                          "sin": np.sin, "cos": np.cos,
                                          "exp": np.exp, "log": np.log,
                                          "np": np}).tolist()

        # Compute complexity
        complexity = 0
        for op in ["+", "-", "*", "/"]:
            complexity += 2 * expression.count(op)
        complexity += 2 * expression.count("**")
        for fn in ["sin", "cos", "exp", "log"]:
            complexity += 2 * expression.count(fn)

        return {
            "expression": expression,
            "predictions": predictions,
            "details": {"complexity": complexity}
        }