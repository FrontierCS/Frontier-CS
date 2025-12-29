import numpy as np

class Solution:
    def __init__(self, **kwargs):
        self.nmse_threshold = kwargs.get("nmse_threshold", 0.02)
        self.max_additional_features = kwargs.get("max_additional_features", 4)
        self.stepwise_improve_tol = kwargs.get("stepwise_improve_tol", 5e-3)
        self.random_state = kwargs.get("random_state", 42)

    def _format_number(self, x):
        if not np.isfinite(x):
            x = 0.0
        if abs(x) < 1e-12:
            return "0"
        s = f"{x:.12g}"
        if s in ("-0", "-0.0", "0.0"):
            s = "0"
        return s

    def _fit_ols(self, A, y):
        w, _, _, _ = np.linalg.lstsq(A, y, rcond=None)
        return w

    def _evaluate_base_peaks(self, x1, x2):
        t1 = (1.0 - x1) ** 2 * np.exp(-(x1 ** 2) - (x2 + 1.0) ** 2)
        t2 = (x1 / 5.0 - x1 ** 3 - x2 ** 5) * np.exp(-(x1 ** 2) - (x2 ** 2))
        t3 = np.exp(-(x1 + 1.0) ** 2 - (x2 ** 2))
        return t1, t2, t3

    def _base_peaks_expressions(self):
        f1 = "((1 - x1)**2)*exp(-(x1**2) - (x2 + 1)**2)"
        f2 = "(x1/5 - x1**3 - x2**5)*exp(-(x1**2) - (x2**2))"
        f3 = "exp(-(x1 + 1)**2 - x2**2)"
        return f1, f2, f3

    def _build_candidate_features(self, x1, x2):
        # Centers inspired by the peaks function
        centers = [(0.0, -1.0), (0.0, 0.0), (-1.0, 0.0)]
        # Polynomial basis terms
        poly_terms = [
            ("1", np.ones_like(x1)),
            ("x1", x1),
            ("x2", x2),
            ("x1**2", x1 ** 2),
            ("x2**2", x2 ** 2),
            ("x1*x2", x1 * x2),
            ("x1**3", x1 ** 3),
            ("x2**3", x2 ** 3),
            ("x1**2*x2", (x1 ** 2) * x2),
            ("x1*x2**2", x1 * (x2 ** 2)),
            ("x2**5", x2 ** 5),
        ]

        features = []
        for (cx, cy) in centers:
            g = np.exp(-((x1 - cx) ** 2) - ((x2 - cy) ** 2))
            # Composite peaks-like basis terms (include exact forms used in classic peaks)
            if (cx, cy) == (0.0, -1.0):
                # ((1 - x1)**2) * exp(-(x1**2) - (x2 + 1)**2)
                arr = ((1.0 - x1) ** 2) * np.exp(-(x1 ** 2) - (x2 + 1.0) ** 2)
                expr = "((1 - x1)**2)*exp(-(x1**2) - (x2 + 1)**2)"
                features.append((expr, arr))
            if (cx, cy) == (0.0, 0.0):
                # (x1/5 - x1**3 - x2**5)*exp(-(x1**2) - (x2**2))
                arr = (x1 / 5.0 - x1 ** 3 - x2 ** 5) * np.exp(-(x1 ** 2) - (x2 ** 2))
                expr = "(x1/5 - x1**3 - x2**5)*exp(-(x1**2) - (x2**2))"
                features.append((expr, arr))
            if (cx, cy) == (-1.0, 0.0):
                # exp(-(x1 + 1)**2 - x2**2)
                arr = np.exp(-(x1 + 1.0) ** 2 - (x2 ** 2))
                expr = "exp(-(x1 + 1)**2 - x2**2)"
                features.append((expr, arr))

            for pexpr, parr in poly_terms:
                expr = f"({pexpr})*exp(-((x1 - {self._format_number(cx)})**2) - ((x2 - {self._format_number(cy)})**2))"
                arr = parr * g
                features.append((expr, arr))

        # Deduplicate by expression string
        seen = set()
        unique_features = []
        for expr, arr in features:
            if expr not in seen:
                seen.add(expr)
                unique_features.append((expr, arr))
        return unique_features

    def _build_expression(self, coeffs, feature_exprs, intercept):
        terms = []
        for c, expr in zip(coeffs, feature_exprs):
            if not np.isfinite(c) or abs(c) < 1e-12:
                continue
            c_abs_str = self._format_number(abs(float(c)))
            if c >= 0:
                terms.append(f"+ {c_abs_str}*({expr})")
            else:
                terms.append(f"- {c_abs_str}*({expr})")
        if np.isfinite(intercept) and abs(intercept) >= 1e-12:
            i_abs_str = self._format_number(abs(float(intercept)))
            if intercept >= 0:
                terms.append(f"+ {i_abs_str}")
            else:
                terms.append(f"- {i_abs_str}")
        if not terms:
            return "0"
        expr_str = " ".join(terms)
        if expr_str.startswith("+ "):
            expr_str = expr_str[2:]
        return expr_str

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        X = np.asarray(X, dtype=float)
        y = np.asarray(y, dtype=float).ravel()
        n = X.shape[0]
        if n == 0:
            return {"expression": "0", "predictions": [], "details": {}}

        x1 = X[:, 0]
        x2 = X[:, 1]

        # Handle near-constant y
        y_mean = float(np.mean(y))
        y_var = float(np.var(y))
        if not np.isfinite(y_var) or y_var < 1e-14:
            expression = self._format_number(y_mean)
            predictions = np.full(n, y_mean, dtype=float)
            return {"expression": expression, "predictions": predictions.tolist(), "details": {}}

        # Base Peaks-like features (3 terms) + intercept
        t1, t2, t3 = self._evaluate_base_peaks(x1, x2)
        A_base = np.column_stack([t1, t2, t3, np.ones(n)])
        coeffs_base = self._fit_ols(A_base, y)
        yhat_base = A_base @ coeffs_base
        mse_base = float(np.mean((y - yhat_base) ** 2))
        nmse_base = mse_base / (y_var + 1e-18)

        f1_expr, f2_expr, f3_expr = self._base_peaks_expressions()
        base_exprs = [f1_expr, f2_expr, f3_expr]
        base_coeffs = coeffs_base[:3]
        base_intercept = coeffs_base[3]

        # If base is good enough, finalize
        if nmse_base <= self.nmse_threshold:
            expression = self._build_expression(base_coeffs, base_exprs, base_intercept)
            return {"expression": expression, "predictions": yhat_base.tolist(), "details": {}}

        # Otherwise, perform a small forward stepwise selection over candidate features
        rng = np.random.default_rng(self.random_state)

        # Build candidate features
        candidates = self._build_candidate_features(x1, x2)
        # Remove base features from candidates to avoid duplicates
        base_set = set(base_exprs)
        candidate_list = [(e, a) for (e, a) in candidates if e not in base_set]

        # Initialize selection with base features
        selected_exprs = base_exprs.copy()
        selected_arrays = [t1, t2, t3]
        intercept_col = np.ones(n)

        # Current fit with base features
        A_sel = np.column_stack(selected_arrays + [intercept_col])
        w_sel = self._fit_ols(A_sel, y)
        yhat_sel = A_sel @ w_sel
        sse_sel = float(np.sum((y - yhat_sel) ** 2))

        max_add = max(0, int(self.max_additional_features))
        for _ in range(max_add):
            best_improve = 0.0
            best_idx = -1
            best_w = None
            best_sse = sse_sel
            # Try adding each candidate
            for idx, (expr_i, arr_i) in enumerate(candidate_list):
                if expr_i in selected_exprs:
                    continue
                A_try = np.column_stack(selected_arrays + [arr_i, intercept_col])
                w_try = self._fit_ols(A_try, y)
                yhat_try = A_try @ w_try
                sse_try = float(np.sum((y - yhat_try) ** 2))
                improve = sse_sel - sse_try
                if improve > best_improve + 1e-12:
                    best_improve = improve
                    best_idx = idx
                    best_w = w_try
                    best_sse = sse_try

            # Check if improvement is significant
            if best_idx == -1:
                break
            rel_improve = best_improve / (sse_sel + 1e-18)
            if rel_improve < self.stepwise_improve_tol:
                break

            # Accept best candidate
            expr_b, arr_b = candidate_list[best_idx]
            selected_exprs.append(expr_b)
            selected_arrays.append(arr_b)
            sse_sel = best_sse
            # Update current fit coefficients using best_w
            # best_w corresponds to selected_arrays + [new] + intercept
            w_sel = best_w

        # Final refit with selected features
        A_final = np.column_stack(selected_arrays + [intercept_col])
        w_final = self._fit_ols(A_final, y)
        yhat_final = A_final @ w_final
        coeffs_final = w_final[:-1]
        intercept_final = w_final[-1]

        expression = self._build_expression(coeffs_final, selected_exprs, intercept_final)
        return {"expression": expression, "predictions": yhat_final.tolist(), "details": {}}