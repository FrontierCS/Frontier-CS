import numpy as np

class Solution:
    def __init__(self, **kwargs):
        self.random_state = int(kwargs.get("random_state", 42))
        self.max_pysr_samples = int(kwargs.get("max_pysr_samples", 3000))
        self.use_pysr = bool(kwargs.get("use_pysr", True))

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        X = np.asarray(X, dtype=float)
        y = np.asarray(y, dtype=float).ravel()

        if X.ndim != 2 or X.shape[1] != 2:
            expression, _ = self._fit_linear(X, y)
            return {
                "expression": expression,
                "predictions": None,
                "details": {}
            }

        expr_peaks, mse_peaks = self._fit_param_peaks(X, y)
        best_expr = expr_peaks
        best_mse = mse_peaks

        if self.use_pysr:
            expr_pysr, mse_pysr = self._try_pysr(
                X,
                y,
                n_samples_limit=self.max_pysr_samples,
                random_state=self.random_state,
            )
            if expr_pysr is not None and np.isfinite(mse_pysr) and mse_pysr < best_mse:
                best_expr = expr_pysr
                best_mse = mse_pysr

        return {
            "expression": best_expr,
            "predictions": None,
            "details": {}
        }

    def _fit_param_peaks(self, X: np.ndarray, y: np.ndarray):
        x1 = X[:, 0]
        x2 = X[:, 1]

        f1 = (1.0 - x1) ** 2 * np.exp(-x1 ** 2 - (x2 + 1.0) ** 2)
        f2 = (x1 / 5.0 - x1 ** 3 - x2 ** 5) * np.exp(-x1 ** 2 - x2 ** 2)
        f3 = np.exp(-(x1 + 1.0) ** 2 - x2 ** 2)
        ones = np.ones_like(x1)

        A = np.column_stack([f1, f2, f3, ones])
        coeffs, _, _, _ = np.linalg.lstsq(A, y, rcond=None)
        a1, a2, a3, c = [float(v) for v in coeffs]

        preds = A @ coeffs
        mse = float(np.mean((preds - y) ** 2))

        a1s = repr(a1)
        a2s = repr(a2)
        a3s = repr(a3)
        cs = repr(c)

        expression = (
            f"{a1s}*(1 - x1)**2*exp(-x1**2 - (x2 + 1)**2)"
            f" + {a2s}*(x1/5 - x1**3 - x2**5)*exp(-x1**2 - x2**2)"
            f" + {a3s}*exp(-(x1 + 1)**2 - x2**2)"
            f" + {cs}"
        )

        return expression, mse

    def _fit_linear(self, X: np.ndarray, y: np.ndarray):
        n_samples = X.shape[0]
        if X.shape[1] >= 2:
            x1 = X[:, 0]
            x2 = X[:, 1]
            A = np.column_stack([x1, x2, np.ones(n_samples)])
            coeffs, _, _, _ = np.linalg.lstsq(A, y, rcond=None)
            a, b, c = [float(v) for v in coeffs]
            expr = f"{repr(a)}*x1 + {repr(b)}*x2 + {repr(c)}"
            preds = A @ coeffs
        elif X.shape[1] == 1:
            x1 = X[:, 0]
            A = np.column_stack([x1, np.ones(n_samples)])
            coeffs, _, _, _ = np.linalg.lstsq(A, y, rcond=None)
            a, c = [float(v) for v in coeffs]
            expr = f"{repr(a)}*x1 + {repr(c)}"
            preds = A @ coeffs
        else:
            A = np.ones((n_samples, 1))
            coeffs, _, _, _ = np.linalg.lstsq(A, y, rcond=None)
            c = float(coeffs[0])
            expr = repr(c)
            preds = A @ coeffs

        mse = float(np.mean((preds - y) ** 2))
        return expr, mse

    def _try_pysr(
        self,
        X: np.ndarray,
        y: np.ndarray,
        n_samples_limit: int = 3000,
        random_state: int = 42,
    ):
        try:
            from pysr import PySRRegressor
        except Exception:
            return None, np.inf

        n = X.shape[0]
        if n > n_samples_limit:
            rng = np.random.default_rng(random_state)
            idx = rng.choice(n, size=n_samples_limit, replace=False)
            X_train = X[idx]
            y_train = y[idx]
        else:
            X_train = X
            y_train = y

        try:
            model = PySRRegressor(
                niterations=40,
                binary_operators=["+", "-", "*", "/"],
                unary_operators=["sin", "cos", "exp", "log"],
                populations=15,
                population_size=33,
                maxsize=25,
                verbosity=0,
                progress=False,
                random_state=random_state,
            )

            model.fit(X_train, y_train, variable_names=["x1", "x2"])

            best_expr = model.sympy()
            try:
                import sympy
                if not isinstance(best_expr, sympy.Basic):
                    if isinstance(best_expr, (list, tuple)) and len(best_expr) > 0:
                        best_expr = best_expr[0]
            except Exception:
                if isinstance(best_expr, (list, tuple)) and len(best_expr) > 0:
                    best_expr = best_expr[0]

            expr_str = str(best_expr)

            preds = model.predict(X)
            mse = float(np.mean((preds - y) ** 2))

            return expr_str, mse
        except Exception:
            return None, np.inf