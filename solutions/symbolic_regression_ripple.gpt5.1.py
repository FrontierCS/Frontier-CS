import numpy as np

try:
    from pysr import PySRRegressor
    _HAVE_PYSR = True
except Exception:
    PySRRegressor = None
    _HAVE_PYSR = False


class Solution:
    def __init__(self, **kwargs):
        self.params = kwargs

    def _fit_pysr(self, X: np.ndarray, y: np.ndarray):
        if not _HAVE_PYSR:
            raise RuntimeError("PySR is not available.")

        n_samples = X.shape[0]

        # Adapt iterations based on dataset size to balance speed and accuracy
        if n_samples <= 500:
            niterations = 120
        elif n_samples <= 2000:
            niterations = 80
        elif n_samples <= 8000:
            niterations = 60
        else:
            niterations = 40

        model = PySRRegressor(
            niterations=niterations,
            binary_operators=["+", "-", "*", "/"],
            unary_operators=["sin", "cos", "exp", "log"],
            populations=15,
            population_size=33,
            maxsize=25,
            verbosity=0,
            progress=False,
            random_state=42,
        )

        model.fit(X, y, variable_names=["x1", "x2"])

        expression = None
        best_complexity = None

        equations = getattr(model, "equations_", None)
        if equations is not None:
            try:
                # Drop rows without loss/complexity
                eq = equations.dropna(subset=["loss", "complexity"])
                if len(eq) > 0:
                    min_loss = eq["loss"].min()
                    tol = max(1e-6, 0.01 * abs(min_loss))
                    # Candidate equations: within small tolerance of best loss
                    candidates = eq[eq["loss"] <= min_loss + tol]
                    candidates = candidates.sort_values(
                        ["complexity", "loss"], ascending=[True, True]
                    )
                    best_idx = candidates.index[0]
                    best_complexity = int(candidates.loc[best_idx, "complexity"])
                    if "sympy_format" in candidates.columns:
                        expr_obj = candidates.loc[best_idx, "sympy_format"]
                        expression = str(expr_obj)
                    else:
                        # Fall back to PySR's sympy exporter for this index
                        expr_obj = model.sympy(best_idx)
                        expression = str(expr_obj)
            except Exception:
                expression = None
                best_complexity = None

        if expression is None:
            # Fallback: take PySR's default best equation
            expr_obj = model.sympy()
            expression = str(expr_obj)

        try:
            predictions = model.predict(X)
        except Exception:
            predictions = None

        details = {"used_pysr": True}
        if best_complexity is not None:
            details["complexity"] = best_complexity

        return expression, predictions, details

    def _fit_fallback(self, X: np.ndarray, y: np.ndarray):
        x1 = X[:, 0]
        x2 = X[:, 1]

        ones = np.ones_like(x1)
        x1_sq = x1 ** 2
        x2_sq = x2 ** 2
        x1x2 = x1 * x2
        sin_x1 = np.sin(x1)
        sin_x2 = np.sin(x2)
        cos_x1 = np.cos(x1)
        cos_x2 = np.cos(x2)
        sin_x1x2 = np.sin(x1x2)
        cos_x1x2 = np.cos(x1x2)

        A = np.column_stack(
            [
                ones,
                x1,
                x2,
                x1_sq,
                x2_sq,
                x1x2,
                sin_x1,
                sin_x2,
                cos_x1,
                cos_x2,
                sin_x1x2,
                cos_x1x2,
            ]
        )

        coeffs, _, _, _ = np.linalg.lstsq(A, y, rcond=None)

        basis_exprs = [
            "1",
            "x1",
            "x2",
            "x1**2",
            "x2**2",
            "x1*x2",
            "sin(x1)",
            "sin(x2)",
            "cos(x1)",
            "cos(x2)",
            "sin(x1*x2)",
            "cos(x1*x2)",
        ]

        terms = []
        for c, be in zip(coeffs, basis_exprs):
            if abs(c) < 1e-8:
                continue
            if be == "1":
                terms.append(f"({c:.12g})")
            else:
                terms.append(f"({c:.12g})*{be}")

        if not terms:
            expression = "0.0"
        else:
            expression = " + ".join(terms)

        predictions = A @ coeffs
        details = {"used_pysr": False, "complexity": len(terms)}

        return expression, predictions, details

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        X = np.asarray(X, dtype=float)
        y = np.asarray(y, dtype=float)

        if X.ndim != 2 or X.shape[1] != 2:
            raise ValueError("X must be of shape (n_samples, 2).")

        try:
            expression, predictions, details = self._fit_pysr(X, y)
        except Exception:
            expression, predictions, details = self._fit_fallback(X, y)

        preds_list = None
        if predictions is not None:
            try:
                preds_list = np.asarray(predictions, dtype=float).ravel().tolist()
            except Exception:
                preds_list = None

        return {
            "expression": expression,
            "predictions": preds_list,
            "details": details,
        }
