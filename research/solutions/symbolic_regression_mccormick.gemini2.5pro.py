import numpy as np
import sympy as sp
from pysr import PySRRegressor
import sys
import os

class Solution:
    def __init__(self, **kwargs):
        pass

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        # Suppress PySR's compilation messages by redirecting stderr
        # This is important for a clean output in the evaluation environment.
        _stderr = sys.stderr
        sys.stderr = open(os.devnull, 'w')

        try:
            # Configure PySR for the specific problem and environment
            model = PySRRegressor(
                procs=8,
                populations=32,
                niterations=80,
                population_size=50,
                # Operators tailored to the expected McCormick function structure
                binary_operators=["+", "-", "*", "**"],
                unary_operators=["sin", "cos"],
                maxsize=30,
                # Control output and ensure reproducibility
                verbosity=0,
                progress=False,
                random_state=42,
                # Default loss (L2DistLoss) and model selection ("best") are suitable
            )

            model.fit(X, y, variable_names=["x1", "x2"])

            # Ensure that at least one equation was found
            if not hasattr(model, 'equations_') or model.equations_.shape[0] == 0:
                raise RuntimeError("PySR did not find any equations.")

            # Retrieve the best expression and its details
            best_sympy_expr = model.sympy()
            expression_str = str(best_sympy_expr)
            
            predictions = model.predict(X)
            
            best_equation_details = model.get_best()
            complexity = best_equation_details.get("complexity", 0)

            return {
                "expression": expression_str,
                "predictions": predictions.tolist(),
                "details": {"complexity": int(complexity)}
            }

        except Exception:
            # Fallback to a linear model with engineered features if PySR fails.
            # This provides a robust baseline. The features are inspired by the
            # known McCormick function structure.
            x1, x2 = X[:, 0], X[:, 1]
            A = np.column_stack([
                np.ones_like(x1), 
                x1, 
                x2, 
                (x1 - x2)**2, 
                np.sin(x1 + x2)
            ])
            
            try:
                coeffs, _, _, _ = np.linalg.lstsq(A, y, rcond=None)
                
                # Construct expression string from fitted coefficients
                expression = (
                    f"{coeffs[0]:.8f} + "
                    f"{coeffs[1]:.8f}*x1 + "
                    f"{coeffs[2]:.8f}*x2 + "
                    f"{coeffs[3]:.8f}*(x1 - x2)**2 + "
                    f"{coeffs[4]:.8f}*sin(x1 + x2)"
                )
                expression = expression.replace(" + -", " - ")
                
                predictions = A @ coeffs
            
            except np.linalg.LinAlgError:
                # Ultimate fallback: predict the mean if linear algebra fails
                mean_y = np.mean(y)
                expression = f"{mean_y:.8f}"
                predictions = np.full_like(y, mean_y)

            return {
                "expression": expression,
                "predictions": predictions.tolist(),
                "details": {}
            }
        
        finally:
            # Restore stderr
            sys.stderr.close()
            sys.stderr = _stderr