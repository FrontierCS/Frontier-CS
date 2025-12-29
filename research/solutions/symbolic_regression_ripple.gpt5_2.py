import numpy as np

class Solution:
    def __init__(self, max_terms: int = 18, random_state: int = 42, **kwargs):
        self.max_terms = int(max_terms)
        self.random_state = int(random_state)

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        X = np.asarray(X, dtype=float)
        y = np.asarray(y, dtype=float).ravel()
        n, d = X.shape
        if d != 2:
            raise ValueError("X must have exactly 2 columns: x1, x2")
        # Build candidate features
        feats = self._build_features(X)
        if len(feats["cols"]) == 0:
            # Fallback: simple linear regression with x1, x2
            x1, x2 = X[:, 0], X[:, 1]
            A = np.column_stack([np.ones_like(x1), x1, x2])
            coeffs, _, _, _ = np.linalg.lstsq(A, y, rcond=None)
            c, a, b = coeffs
            expression = f"{c:.12g} + ({a:.12g})*x1 + ({b:.12g})*x2"
            preds = A @ coeffs
            return {
                "expression": expression,
                "predictions": preds.tolist(),
                "details": {}
            }
        F = feats["matrix"]
        exprs = feats["exprs"]

        # Run Orthogonal Matching Pursuit with an intercept
        coef, selected = self._omp_with_intercept(F, y, max_terms=self.max_terms)

        # Build final expression
        expression = self._build_expression(coef, selected, exprs)

        # Predictions using the selected features and intercept
        intercept = coef[0]
        if len(selected) > 0:
            preds = intercept + F[:, selected] @ coef[1:]
        else:
            preds = np.full_like(y, intercept, dtype=float)

        return {
            "expression": expression,
            "predictions": preds.tolist(),
            "details": {}
        }

    def _build_features(self, X: np.ndarray) -> dict:
        x1 = X[:, 0]
        x2 = X[:, 1]
        n = X.shape[0]

        def add_feature(arr, expr):
            # Validate column
            col = np.asarray(arr, dtype=float).ravel()
            if not np.all(np.isfinite(col)):
                return
            norm = np.linalg.norm(col)
            if norm < 1e-12:
                return
            cols.append(col)
            exprs.append(expr)

        # Precompute radial terms
        r2 = x1**2 + x2**2
        r = np.sqrt(r2)

        str_x1 = "x1"
        str_x2 = "x2"
        str_r2 = "(x1**2 + x2**2)"
        str_r = f"({str_r2})**0.5"

        cols = []
        exprs = []

        # Polynomial base features (without the intercept since we'll include it separately)
        add_feature(x1, str_x1)
        add_feature(x2, str_x2)
        add_feature(r, str_r)
        add_feature(r2, str_r2)
        add_feature(x1 * x2, f"{str_x1}*{str_x2}")
        add_feature(x1**2, f"{str_x1}**2")
        add_feature(x2**2, f"{str_x2}**2")

        # Amplitude multipliers
        amp_list = [
            (np.ones_like(r), "1"),
            (1.0 / (1.0 + r), f"1/(1 + ({str_r}))"),
            (1.0 / (1.0 + r2), f"1/(1 + ({str_r2}))"),
            (r / (1.0 + r2), f"(({str_r})/(1 + ({str_r2})))"),
            (1.0 / np.sqrt(1.0 + r2), f"1/((1 + ({str_r2}))**0.5)"),
        ]
        amp_axis = [
            (np.ones_like(r), "1"),
            (1.0 / (1.0 + r2), f"1/(1 + ({str_r2}))"),
        ]

        # Frequencies
        F_r = list(range(1, 13))  # 1..12 for radial
        F_r2 = [0.5, 1.0, 2.0, 3.0]
        F_axis = [1.0, 2.0, 3.0, 4.0, 5.0]
        F_sumdiff = [1.0, 2.0, 3.0, 4.0]

        # Radial sin/cos with amplitudes
        for w in F_r:
            sin_arr = np.sin(w * r)
            cos_arr = np.cos(w * r)
            sin_expr = f"sin({w}*({str_r}))"
            cos_expr = f"cos({w}*({str_r}))"
            for amp_arr, amp_expr in amp_list:
                add_feature(amp_arr * sin_arr, self._mul_exprs(amp_expr, sin_expr))
                add_feature(amp_arr * cos_arr, self._mul_exprs(amp_expr, cos_expr))

        # r^2 sin/cos with amplitudes
        for w in F_r2:
            sin_arr = np.sin(w * r2)
            cos_arr = np.cos(w * r2)
            sin_expr = f"sin({self._format_float(w)}*({str_r2}))"
            cos_expr = f"cos({self._format_float(w)}*({str_r2}))"
            for amp_arr, amp_expr in amp_list:
                add_feature(amp_arr * sin_arr, self._mul_exprs(amp_expr, sin_expr))
                add_feature(amp_arr * cos_arr, self._mul_exprs(amp_expr, cos_expr))

        # Axis-aligned sin/cos
        for w in F_axis:
            sin1 = np.sin(w * x1)
            cos1 = np.cos(w * x1)
            sin2 = np.sin(w * x2)
            cos2 = np.cos(w * x2)
            sin1_expr = f"sin({self._format_float(w)}*{str_x1})"
            cos1_expr = f"cos({self._format_float(w)}*{str_x1})"
            sin2_expr = f"sin({self._format_float(w)}*{str_x2})"
            cos2_expr = f"cos({self._format_float(w)}*{str_x2})"
            for amp_arr, amp_expr in amp_axis:
                add_feature(amp_arr * sin1, self._mul_exprs(amp_expr, sin1_expr))
                add_feature(amp_arr * cos1, self._mul_exprs(amp_expr, cos1_expr))
                add_feature(amp_arr * sin2, self._mul_exprs(amp_expr, sin2_expr))
                add_feature(amp_arr * cos2, self._mul_exprs(amp_expr, cos2_expr))

        # Sum/diff sin/cos
        s = x1 + x2
        d = x1 - x2
        str_s = f"({str_x1} + {str_x2})"
        str_d = f"({str_x1} - {str_x2})"
        for w in F_sumdiff:
            sin_s = np.sin(w * s)
            cos_s = np.cos(w * s)
            sin_d = np.sin(w * d)
            cos_d = np.cos(w * d)
            sin_s_expr = f"sin({self._format_float(w)}*{str_s})"
            cos_s_expr = f"cos({self._format_float(w)}*{str_s})"
            sin_d_expr = f"sin({self._format_float(w)}*{str_d})"
            cos_d_expr = f"cos({self._format_float(w)}*{str_d})"
            for amp_arr, amp_expr in amp_axis:
                add_feature(amp_arr * sin_s, self._mul_exprs(amp_expr, sin_s_expr))
                add_feature(amp_arr * cos_s, self._mul_exprs(amp_expr, cos_s_expr))
                add_feature(amp_arr * sin_d, self._mul_exprs(amp_expr, sin_d_expr))
                add_feature(amp_arr * cos_d, self._mul_exprs(amp_expr, cos_d_expr))

        if len(cols) == 0:
            return {"matrix": np.zeros((X.shape[0], 0), dtype=float), "exprs": [], "cols": []}

        F = np.column_stack(cols)
        return {"matrix": F, "exprs": exprs, "cols": cols}

    def _mul_exprs(self, a_expr: str, b_expr: str) -> str:
        if a_expr == "1":
            return f"{b_expr}"
        return f"({a_expr})*({b_expr})"

    def _format_float(self, v: float) -> str:
        return f"{float(v):.12g}"

    def _omp_with_intercept(self, F: np.ndarray, y: np.ndarray, max_terms: int = 18):
        n, p = F.shape
        # Precompute column norms for correlation normalization
        col_norms = np.linalg.norm(F, axis=0)
        col_norms[col_norms < 1e-15] = 1e-15

        selected = []
        # Solve with only intercept initially
        ones = np.ones(n, dtype=float)
        A = ones.reshape(-1, 1)
        beta, _, _, _ = np.linalg.lstsq(A, y, rcond=None)
        intercept = float(beta[0])
        y_pred = A @ beta
        resid = y - y_pred
        prev_rss = float(np.dot(resid, resid))
        y_var = float(np.var(y)) if n > 1 else prev_rss
        tol_abs = max(1e-8, 1e-6 * y_var * n)

        max_terms = int(max_terms)
        for t in range(max_terms):
            # Compute correlations
            corr = F.T @ resid
            corr = corr / col_norms
            # Mask already selected indices
            if selected:
                corr[selected] = 0.0
            # Pick best
            j = int(np.argmax(np.abs(corr)))
            best_corr = float(np.abs(corr[j]))
            if best_corr <= 0:
                break
            # Add feature j
            selected.append(j)
            # Solve least squares with intercept + selected features
            A = np.column_stack([np.ones(n, dtype=float), F[:, selected]])
            beta, _, _, _ = np.linalg.lstsq(A, y, rcond=None)
            y_pred = A @ beta
            resid = y - y_pred
            rss = float(np.dot(resid, resid))
            improvement = prev_rss - rss
            if improvement < tol_abs:
                # Revert last selection and stop
                selected.pop()
                # Recompute final with earlier set
                if selected:
                    A = np.column_stack([np.ones(n, dtype=float), F[:, selected]])
                    beta, _, _, _ = np.linalg.lstsq(A, y, rcond=None)
                else:
                    A = np.ones((n, 1), dtype=float)
                    beta, _, _, _ = np.linalg.lstsq(A, y, rcond=None)
                break
            prev_rss = rss

        # Final coefficients
        if selected:
            A = np.column_stack([np.ones(n, dtype=float), F[:, selected]])
            beta, _, _, _ = np.linalg.lstsq(A, y, rcond=None)
        else:
            A = np.ones((n, 1), dtype=float)
            beta, _, _, _ = np.linalg.lstsq(A, y, rcond=None)
        return beta.ravel(), selected

    def _build_expression(self, coef: np.ndarray, selected: list, exprs: list) -> str:
        # Remove near-zero coefficients to simplify expression
        intercept = float(coef[0])
        terms = []
        for k, j in enumerate(selected):
            c = float(coef[k + 1])
            if not np.isfinite(c) or abs(c) < 1e-12:
                continue
            expr = exprs[j]
            terms.append(f"({self._format_float(c)})*({expr})")

        # Recompute intercept if we dropped terms
        # But to keep consistency, we won't adjust; instead, if no terms remain, output intercept only
        base = self._format_float(intercept)
        if len(terms) == 0:
            return f"{base}"
        # Combine
        expression = base
        for t in terms:
            expression += f" + {t}"
        return expression