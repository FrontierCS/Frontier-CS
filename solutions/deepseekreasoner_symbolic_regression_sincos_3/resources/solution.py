import numpy as np
from pysr import PySRRegressor
import warnings

class Solution:
    def __init__(self, **kwargs):
        pass

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            
            model = PySRRegressor(
                niterations=30,
                binary_operators=["+", "-", "*", "/"],
                unary_operators=["sin", "cos"],
                populations=8,
                population_size=30,
                maxsize=20,
                verbosity=0,
                progress=False,
                random_state=42,
                deterministic=True,
                early_stop_condition="stop_if(loss, complexity) = loss < 1e-12 && complexity < 10",
                timeout_in_seconds=30,
                max_evals=10000,
                constraints={"sin": 4, "cos": 4},
                nested_constraints={"sin": {"sin": 0, "cos": 0},
                                   "cos": {"sin": 0, "cos": 0}},
                use_frequency=True,
                use_frequency_in_tournament=True,
                parsimony=0.003,
                annealing=True,
                model_selection="accuracy",
                temp_scale=0.02,
                temp_decay=0.999,
                should_optimize_constants=True,
                optimizer_algorithm="BFGS",
                optimizer_iterations=30,
            )
            
            try:
                model.fit(X, y, variable_names=["x1", "x2"])
                
                best_expr = model.sympy()
                expression = str(best_expr).replace("**", "^").replace("^", "**")
                
                predictions = model.predict(X)
                
                return {
                    "expression": expression,
                    "predictions": predictions.tolist(),
                    "details": {}
                }
                
            except Exception:
                x1, x2 = X[:, 0], X[:, 1]
                
                A = np.column_stack([
                    np.sin(x1), np.cos(x1), np.sin(x2), np.cos(x2),
                    np.sin(x1) * np.sin(x2), np.sin(x1) * np.cos(x2),
                    np.cos(x1) * np.sin(x2), np.cos(x1) * np.cos(x2),
                    np.ones_like(x1)
                ])
                
                coeffs, _, _, _ = np.linalg.lstsq(A, y, rcond=None)
                
                terms = [
                    f"{coeffs[0]:.6f}*sin(x1)",
                    f"{coeffs[1]:.6f}*cos(x1)",
                    f"{coeffs[2]:.6f}*sin(x2)",
                    f"{coeffs[3]:.6f}*cos(x2)",
                    f"{coeffs[4]:.6f}*sin(x1)*sin(x2)",
                    f"{coeffs[5]:.6f}*sin(x1)*cos(x2)",
                    f"{coeffs[6]:.6f}*cos(x1)*sin(x2)",
                    f"{coeffs[7]:.6f}*cos(x1)*cos(x2)",
                    f"{coeffs[8]:.6f}"
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
