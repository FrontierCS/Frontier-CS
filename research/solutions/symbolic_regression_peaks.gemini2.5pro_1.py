import numpy as np
from pysr import PySRRegressor

class Solution:
    def __init__(self, **kwargs):
        """
        No-op constructor.
        """
        pass

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        """
        Finds a symbolic expression for the given data using PySR,
        with a fallback to a quadratic model if PySR fails.
        """
        model = PySRRegressor(
            niterations=150,
            populations=32,
            population_size=50,
            procs=8,
            maxsize=30,
            binary_operators=["+", "-", "*", "/", "**"],
            unary_operators=["exp", "cos", "sin", "log"],
            model_selection="best",
            loss="L2DistLoss()",
            # Align PySR's complexity score with the evaluation metric
            complexity_of_operators={
                "+": 2, "-": 2, "*": 2, "/": 2, "**": 2,
                "exp": 1, "cos": 1, "sin": 1, "log": 1
            },
            # Allow nested complexity for key functions
            constraints={'exp': 10, 'cos': 10, 'sin': 10},
            # For reproducibility
            random_state=42,
            # Suppress verbose output
            verbosity=0,
            progress=False,
            # Use a temporary file for equations; good practice for long runs
            temp_equation_file=True,
            # Set a timeout to avoid exceeding evaluation time limits
            timeout_in_seconds=550,
        )

        try:
            model.fit(X, y, variable_names=["x1", "x2"])

            if not hasattr(model, 'equations_') or model.equations_.shape[0] == 0:
                raise RuntimeError("PySR search failed to find any equations.")

            best_idx = model.get_best_index()
            best_equation = model.equations_.iloc[best_idx]
            
            expression = str(model.sympy(best_idx))
            predictions = model.predict(X, best_idx)
            complexity = best_equation['complexity']

            return {
                "expression": expression,
                "predictions": predictions.tolist(),
                "details": {"complexity": int(complexity)}
            }

        except (RuntimeError, ValueError):
            # Fallback to a simpler model if PySR fails or finds no equations
            x1, x2 = X[:, 0], X[:, 1]
            # Quadratic model: y ~ c0 + c1*x1 + c2*x2 + c3*x1*x2 + c4*x1**2 + c5*x2**2
            A = np.c_[np.ones_like(x1), x1, x2, x1 * x2, x1**2, x2**2]
            
            try:
                coeffs, _, _, _ = np.linalg.lstsq(A, y, rcond=None)
                c0, c1, c2, c3, c4, c5 = coeffs
                expression = (
                    f"{c0:.8f} + {c1:.8f}*x1 + {c2:.8f}*x2 + "
                    f"{c3:.8f}*x1*x2 + {c4:.8f}*x1**2 + {c5:.8f}*x2**2"
                )
                predictions = A @ coeffs
                
                return {
                    "expression": expression,
                    "predictions": predictions.tolist(),
                    "details": {}
                }
            except np.linalg.LinAlgError:
                # Ultimate fallback: predict the mean
                mean_y = np.mean(y)
                expression = f"{mean_y:.8f}"
                predictions = np.full_like(y, mean_y)
                
                return {
                    "expression": expression,
                    "predictions": predictions.tolist(),
                    "details": {"complexity": 0}
                }