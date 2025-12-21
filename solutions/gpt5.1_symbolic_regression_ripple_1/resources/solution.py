import numpy as np

class Solution:
    def __init__(self, **kwargs):
        self.use_pysr = kwargs.get("use_pysr", True)

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        X = np.asarray(X, dtype=float)
        y = np.asarray(y, dtype=float).ravel()

        expression = None
        predictions = None
        details = {}

        if self.use_pysr:
            expr_pysr, preds_pysr = self._run_pysr(X, y)
            if expr_pysr is not None:
                expression = expr_pysr
                predictions = preds_pysr

        if expression is None:
            expression, predictions = self._fallback_symbolic(X, y)

        return {
            "expression": expression,
            "predictions": predictions.tolist() if predictions is not None else None,
            "details": details,
        }

    def _run_pysr(self, X: np.ndarray, y: np.ndarray):
        try:
            from pysr import PySRRegressor
        except Exception:
            return None, None

        n_samples = X.shape[0]
        if n_samples <= 2000:
            niterations = 80
            population_size = 50
        elif n_samples <= 8000:
            niterations = 60
            population_size = 40
        else:
            niterations = 40
            population_size = 30

        try:
            model = PySRRegressor(
                niterations=niterations,
                binary_operators=["+", "-", "*", "/", "^"],
                unary_operators=["sin", "cos", "exp", "log"],
                populations=10,
                population_size=population_size,
                maxsize=25,
                verbosity=0,
                progress=False,
                random_state=42,
            )
            model.fit(X, y, variable_names=["x1", "x2"])
            best_expr = model.sympy()
            expression = str(best_expr)
            expression = expression.replace("^", "**")
            preds = model.predict(X)
            preds = np.asarray(preds, dtype=float).ravel()
            return expression, preds
        except Exception:
            return None, None

    def _fallback_symbolic(self, X: np.ndarray, y: np.ndarray):
        x1 = X[:, 0]
        x2 = X[:, 1]

        r2 = x1 ** 2 + x2 ** 2
        r = np.sqrt(r2 + 1e-12)

        feats = []
        exprs = []

        def add_feat(values, expr_str):
            feats.append(values)
            exprs.append(expr_str)

        # Basic polynomial terms
        add_feat(np.ones_like(x1), "1.0")
        add_feat(x1, "x1")
        add_feat(x2, "x2")
        add_feat(x1 * x2, "x1*x2")
        add_feat(x1 ** 2, "x1**2")
        add_feat(x2 ** 2, "x2**2")
        add_feat(r2, "x1**2 + x2**2")
        add_feat(r, "(x1**2 + x2**2)**0.5")

        # Rational-like radial terms
        denom = 1.0 + r2
        add_feat(1.0 / denom, "1.0/(1.0 + (x1**2 + x2**2))")
        add_feat(r2 / denom, "(x1**2 + x2**2)/(1.0 + (x1**2 + x2**2))")

        # Trigonometric terms in x1 and x2
        freqs_x = [1.0, 2.0, 3.0, 5.0]
        for k in freqs_x:
            add_feat(np.sin(k * x1), f"sin({k}*x1)")
            add_feat(np.cos(k * x1), f"cos({k}*x1)")
            add_feat(np.sin(k * x2), f"sin({k}*x2)")
            add_feat(np.cos(k * x2), f"cos({k}*x2)")

        # Radial trigonometric terms (in radius)
        freqs_r = [1.0, 2.0, 3.0, 5.0]
        for k in freqs_r:
            add_feat(np.sin(k * r), f"sin({k}*(x1**2 + x2**2)**0.5)")
            add_feat(np.cos(k * r), f"cos({k}*(x1**2 + x2**2)**0.5)")

        # Trigonometric terms in r^2
        freqs_r2 = [0.5, 1.0, 2.0, 3.0]
        for k in freqs_r2:
            add_feat(np.sin(k * r2), f"sin({k}*(x1**2 + x2**2))")
            add_feat(np.cos(k * r2), f"cos({k}*(x1**2 + x2**2))")

        A = np.column_stack(feats).astype(float)

        # Normalize columns to improve conditioning
        col_norms = np.linalg.norm(A, axis=0)
        col_norms[col_norms == 0] = 1.0
        A_scaled = A / col_norms

        # Ridge regression
        lambda_reg = 1e-4
        AtA = A_scaled.T @ A_scaled
        n_features = AtA.shape[0]
        AtA[np.arange(n_features), np.arange(n_features)] += lambda_reg
        Aty = A_scaled.T @ y

        try:
            coeffs_scaled = np.linalg.solve(AtA, Aty)
        except np.linalg.LinAlgError:
            coeffs_scaled, _, _, _ = np.linalg.lstsq(A_scaled, y, rcond=None)

        coeffs = coeffs_scaled / col_norms

        if coeffs.size == 0:
            expression = "0.0"
            predictions = np.zeros_like(y, dtype=float)
            return expression, predictions

        max_abs = float(np.max(np.abs(coeffs)))
        if not np.isfinite(max_abs) or max_abs == 0.0:
            expression = "0.0"
            predictions = np.zeros_like(y, dtype=float)
            return expression, predictions

        threshold = max_abs * 1e-3
        mask = np.abs(coeffs) > threshold

        if not np.any(mask):
            idx_max = int(np.argmax(np.abs(coeffs)))
            mask = np.zeros_like(coeffs, dtype=bool)
            mask[idx_max] = True

        coeffs_used = coeffs[mask]
        exprs_used = [exprs[i] for i in range(len(exprs)) if mask[i]]

        terms = []
        for c, e in zip(coeffs_used, exprs_used):
            if e == "1.0":
                term = f"({c:.15g})"
            else:
                term = f"({c:.15g})*({e})"
            terms.append(term)

        if not terms:
            expression = "0.0"
            predictions = np.zeros_like(y, dtype=float)
        else:
            expression = " + ".join(terms)
            A_reduced = A[:, mask]
            predictions = A_reduced @ coeffs_used

        predictions = np.asarray(predictions, dtype=float).ravel()
        return expression, predictions
