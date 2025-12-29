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
            populations=8,
            population_size=50,
            maxsize=30,
            maxdepth=12,
            temp_equation_file=True,
            tempdir=".",
            verbosity=0,
            progress=False,
            random_state=42,
            deterministic=True,
            complexity_of_constants=2,
            complexity_of_variables=1,
            parsimony=0.001,
            nested_constraints={
                "**": {"sin": 0, "cos": 0, "exp": 0, "log": 0},
                "/": {"sin": 0, "cos": 0, "exp": 0, "log": 0},
                "log": {"**": 0, "/": 0},
                "exp": {"**": 0, "/": 0},
            },
            warming_up=True,
            warm_start=True,
            update_test=False,
            turbo=True,
            batching=False,
            batch_size=50,
            model_selection="accuracy",
            loss="loss(x, y) = (x - y)^2",
            equation_file="ripple_equations.csv",
            early_stop_condition=(
                "stop_if(loss, complexity) = loss < 1e-9 && complexity > 5"
            ),
            timeout_in_seconds=300,
        )
        
        try:
            model.fit(X, y, variable_names=["x1", "x2"])
            
            best_expr = model.sympy()
            if best_expr is None:
                best_expr = model.equations_.iloc[0]["sympy_format"]
                expression = str(best_expr)
            else:
                expression = str(best_expr)
            
            predictions = model.predict(X)
            
        except Exception:
            x1, x2 = X[:, 0], X[:, 1]
            A = np.column_stack([
                x1, x2, x1**2, x2**2, x1*x2,
                np.sin(x1), np.cos(x1), np.sin(x2), np.cos(x2),
                np.sin(x1**2 + x2**2), np.cos(x1**2 + x2**2),
                np.exp(-0.1*(x1**2 + x2**2)), np.ones_like(x1)
            ])
            coeffs, _, _, _ = np.linalg.lstsq(A, y, rcond=None)
            
            terms = [
                f"{coeffs[0]:.6f}*x1",
                f"{coeffs[1]:.6f}*x2",
                f"{coeffs[2]:.6f}*x1**2",
                f"{coeffs[3]:.6f}*x2**2",
                f"{coeffs[4]:.6f}*x1*x2",
                f"{coeffs[5]:.6f}*sin(x1)",
                f"{coeffs[6]:.6f}*cos(x1)",
                f"{coeffs[7]:.6f}*sin(x2)",
                f"{coeffs[8]:.6f}*cos(x2)",
                f"{coeffs[9]:.6f}*sin(x1**2 + x2**2)",
                f"{coeffs[10]:.6f}*cos(x1**2 + x2**2)",
                f"{coeffs[11]:.6f}*exp(-0.1*(x1**2 + x2**2))",
                f"{coeffs[12]:.6f}"
            ]
            expression = " + ".join([t for t, c in zip(terms, coeffs) if abs(c) > 1e-10])
            if not expression:
                expression = "0"
            
            predictions = A @ coeffs
        
        return {
            "expression": expression,
            "predictions": predictions.tolist(),
            "details": {}
        }