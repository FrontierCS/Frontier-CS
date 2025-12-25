import numpy as np


class Solution:
    def __init__(self, **kwargs):
        self.kwargs = kwargs

    def _fit_linear_baseline(self, X: np.ndarray, y: np.ndarray):
        x1, x2, x3, x4 = X[:, 0], X[:, 1], X[:, 2], X[:, 3]
        A = np.column_stack([x1, x2, x3, x4, np.ones_like(x1)])
        coeffs, _, _, _ = np.linalg.lstsq(A, y, rcond=None)
        a, b, c, d, e = coeffs
        expression = (
            f"{a:.12g}*x1 + {b:.12g}*x2 + {c:.12g}*x3 + {d:.12g}*x4 + {e:.12g}"
        )
        predictions = A @ coeffs
        return expression, predictions

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        try:
            from pysr import PySRRegressor

            n_samples = X.shape[0]

            # Moderate settings for 4D problem and CPU-only environment
            if n_samples < 300:
                niterations = 70
                populations = 14
                population_size = 30
                maxsize = 30
            elif n_samples < 2000:
                niterations = 50
                populations = 16
                population_size = 35
                maxsize = 32
            else:
                niterations = 40
                populations = 18
                population_size = 40
                maxsize = 32

            model = PySRRegressor(
                niterations=niterations,
                binary_operators=["+", "-", "*", "/"],
                unary_operators=["sin", "cos", "exp", "log"],
                populations=populations,
                population_size=population_size,
                maxsize=maxsize,
                verbosity=0,
                progress=False,
                random_state=42,
            )

            model.fit(X, y, variable_names=["x1", "x2", "x3", "x4"])

            expression = None
            try:
                eqs = model.equations_
                if eqs is not None and len(eqs) > 0:
                    losses = np.asarray(eqs["loss"], dtype=float)
                    best_loss = np.nanmin(losses)
                    if not np.isfinite(best_loss):
                        raise ValueError("Non-finite best_loss")

                    tol = max(1e-6, 0.01 * abs(best_loss))
                    mask = losses <= best_loss + tol
                    if not np.any(mask):
                        mask = np.isfinite(losses)

                    sub = eqs[mask]
                    if len(sub) == 0:
                        sub = eqs

                    complexities = np.asarray(sub["complexity"], dtype=float)
                    idx_in_sub = int(np.argmin(complexities))
                    idx = int(sub.index[idx_in_sub])

                    if "sympy_format" in eqs.columns:
                        expr_obj = eqs.loc[idx, "sympy_format"]
                    else:
                        expr_obj = eqs.loc[idx, "equation"]
                    expression = str(expr_obj)
                else:
                    expression = str(model.sympy())
            except Exception:
                expression = str(model.sympy())

            return {
                "expression": expression,
                "predictions": None,
                "details": {},
            }

        except Exception:
            expression, predictions = self._fit_linear_baseline(X, y)
            return {
                "expression": expression,
                "predictions": predictions.tolist(),
                "details": {},
            }
