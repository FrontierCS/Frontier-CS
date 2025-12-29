import numpy as np
from pysr import PySRRegressor

class Solution:
    def __init__(self, **kwargs):
        pass

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        """
        Finds a symbolic expression for the SinCos dataset.
        
        This solution uses PySR, a genetic programming-based symbolic regression
        library, to discover the underlying mathematical expression.
        
        The configuration is tuned for the specific problem and environment:
        - Unary operators are limited to 'sin' and 'cos' based on the problem
          description hinting at periodic behavior. This significantly prunes the
          search space and accelerates discovery of the correct functional form.
        - Multiprocessing is enabled to utilize all 8 vCPUs available in the
          evaluation environment.
        - Population size and number of populations are increased to improve
          search diversity.
        - A generous timeout is set to allow PySR to run for as long as possible
          within typical contest limits.
        - A fallback to a simple linear regression model is implemented in case
          PySR fails to find an expression or times out.
        """
        try:
            model = PySRRegressor(
                niterations=40,
                populations=16,
                population_size=50,
                binary_operators=["+", "-", "*", "/"],
                unary_operators=["sin", "cos"],
                maxsize=20,
                procs=8,
                verbosity=0,
                progress=False,
                random_state=42,
                timeout_in_seconds=550
            )
            
            model.fit(X, y, variable_names=["x1", "x2"])

            if not hasattr(model, 'equations_') or model.equations_.empty:
                raise RuntimeError("PySR did not find any equations.")

            best_expr_sympy = model.sympy()
            expression = str(best_expr_sympy)
            predictions = model.predict(X)

            return {
                "expression": expression,
                "predictions": predictions.tolist(),
                "details": {}
            }
        except Exception:
            x1, x2 = X[:, 0], X[:, 1]
            A = np.column_stack([x1, x2, np.ones_like(x1)])
            try:
                coeffs, _, _, _ = np.linalg.lstsq(A, y, rcond=None)
                a, b, c = coeffs
                expression = f"{a:.6f}*x1 + {b:.6f}*x2 + {c:.6f}"
                predictions = a * x1 + b * x2 + c
            except np.linalg.LinAlgError:
                mean_y = np.mean(y)
                expression = f"{mean_y:.6f}"
                predictions = np.full_like(y, mean_y)
            
            return {
                "expression": expression,
                "predictions": predictions.tolist(),
                "details": {}
            }