import numpy as np

class Solution:
    def __init__(self, **kwargs):
        self.max_initial_features = kwargs.get("max_initial_features", 400)
        self.top_k_initial = kwargs.get("top_k_initial", 50)
        self.final_top_k = kwargs.get("final_top_k", 25)
        self.threshold_ratio = kwargs.get("threshold_ratio", 0.015)
        self.random_state = kwargs.get("random_state", 42)

    def _ptp_safe(self, a):
        v = float(np.max(a) - np.min(a))
        if not np.isfinite(v) or v == 0.0:
            return 1.0
        return v

    def _unique_sorted(self, vals, tol=1e-12):
        vals = sorted([float(v) for v in vals if np.isfinite(v) and v > 0])
        if not vals:
            return []
        uniq = [vals[0]]
        for v in vals[1:]:
            if abs(v - uniq[-1]) > tol:
                uniq.append(v)
        return uniq

    def _calc_omegas(self, rng, base_caps=(120.0,)):
        # Generate adaptive frequency grid based on range, with caps
        eps = 1e-12
        rng = max(rng, eps)
        cycles = [1, 2, 3, 5, 8, 13]
        w_data = [2.0 * np.pi * c / rng for c in cycles]
        w_raw = [1.0, 1.5, 2.0, 3.0, 5.0, 7.0, 10.0, 15.0]
        w_pi = [np.pi * k for k in [0.5, 1.0, 1.5, 2.0, 3.0]]
        w_all = w_data + w_raw + w_pi
        cap = base_caps[0] if base_caps else 120.0
        w_all = [w for w in w_all if 0 < w <= cap]
        return self._unique_sorted(w_all, tol=1e-12)

    def _calc_a_opts(self, r2):
        # Generate decay coefficients a for terms 1/(1 + a*r2)
        r2_max = float(np.max(r2))
        r2_rng = float(np.max(r2) - np.min(r2))
        eps = 1e-12
        scale1 = 1.0 / (r2_max + eps) if r2_max > 0 else 1.0
        scale2 = 1.0 / (r2_rng + eps) if r2_rng > 0 else scale1
        candidates = [scale1 * s for s in [0.5, 1.0, 2.0, 5.0, 10.0]] + [scale2 * s for s in [0.5, 1.0, 2.0, 5.0, 10.0]]
        candidates = [c for c in candidates if np.isfinite(c) and c > 0]
        # Deduplicate and limit to reasonable values
        c_sorted = self._unique_sorted(candidates, tol=1e-12)
        # Avoid extremely tiny or huge 'a'
        c_filtered = [c for c in c_sorted if 1e-8 <= c <= 1e8]
        # Limit number
        if len(c_filtered) > 6:
            # pick percentiles
            idxs = np.linspace(0, len(c_filtered) - 1, 6).astype(int)
            c_filtered = [c_filtered[i] for i in idxs]
        return c_filtered if c_filtered else [1.0]

    def _build_feature_library(self, X, max_features=400):
        n = X.shape[0]
        x1 = X[:, 0].astype(float)
        x2 = X[:, 1].astype(float)
        r2 = x1 * x1 + x2 * x2
        r = np.sqrt(r2 + 0.0)

        # Expressions strings for convenience
        r2_expr = "(x1**2 + x2**2)"
        r_expr = f"(({r2_expr})**0.5)"

        features = []
        exprs = []

        def add_feature(arr, expr):
            if len(features) >= max_features:
                return
            arr = np.asarray(arr).reshape(-1)
            if arr.shape[0] != n:
                return
            if not np.all(np.isfinite(arr)):
                return
            # Discard near-constant features (very low variance)
            v = float(np.var(arr))
            if not np.isfinite(v) or v < 1e-14:
                return
            features.append(arr)
            exprs.append(expr)

        # Baseline polynomial-like features (without constant)
        add_feature(x1, "x1")
        add_feature(x2, "x2")
        add_feature(r2, r2_expr)
        add_feature(r, r_expr)
        add_feature(x1 * x2, "(x1*x2)")

        # Frequency lists
        rng_x1 = self._ptp_safe(x1)
        rng_x2 = self._ptp_safe(x2)
        rng_sum = self._ptp_safe(x1 + x2)
        rng_diff = self._ptp_safe(x1 - x2)
        rng_r = self._ptp_safe(r)
        rng_r2 = self._ptp_safe(r2)

        w_x1 = self._calc_omegas(rng_x1, base_caps=(120.0,))
        w_x2 = self._calc_omegas(rng_x2, base_caps=(120.0,))
        w_sum = self._calc_omegas(rng_sum, base_caps=(120.0,))
        w_diff = self._calc_omegas(rng_diff, base_caps=(120.0,))
        w_r = self._calc_omegas(rng_r, base_caps=(120.0,))
        w_r2 = self._calc_omegas(rng_r2, base_caps=(120.0,))

        a_opts = self._calc_a_opts(r2)

        # Helper to add trig features
        def add_trig(var_arr, var_expr, w_list, with_decay=False, with_amp_growth=False):
            for w in w_list:
                if len(features) >= max_features:
                    break
                sin_arr = np.sin(w * var_arr)
                cos_arr = np.cos(w * var_arr)
                w_str = f"{w:.12g}"

                # Plain sin/cos
                add_feature(sin_arr, f"sin({w_str}*{var_expr})")
                add_feature(cos_arr, f"cos({w_str}*{var_expr})")

                if with_decay:
                    for a in a_opts:
                        if len(features) >= max_features:
                            break
                        a_str = f"{a:.12g}"
                        denom_expr = f"(1 + {a_str}*{r2_expr})"
                        denom_arr = 1.0 + a * r2
                        add_feature(sin_arr / denom_arr, f"(sin({w_str}*{var_expr})/{denom_expr})")
                        add_feature(cos_arr / denom_arr, f"(cos({w_str}*{var_expr})/{denom_expr})")

                if with_amp_growth:
                    # r2 * trig and r * trig
                    add_feature(r2 * sin_arr, f"({r2_expr}*sin({w_str}*{var_expr}))")
                    add_feature(r2 * cos_arr, f"({r2_expr}*cos({w_str}*{var_expr}))")
                    add_feature(r * sin_arr, f"({r_expr}*sin({w_str}*{var_expr}))")
                    add_feature(r * cos_arr, f"({r_expr}*cos({w_str}*{var_expr}))")

        # Build library
        # Trig in r with decay and some amplitude growth
        add_trig(r, r_expr, w_r, with_decay=True, with_amp_growth=True)

        # Trig in r2 with decay (captures sin of squared radius)
        add_trig(r2, r2_expr, w_r2, with_decay=True, with_amp_growth=False)

        # 1D trigs for x1, x2
        add_trig(x1, "x1", w_x1, with_decay=False, with_amp_growth=False)
        add_trig(x2, "x2", w_x2, with_decay=False, with_amp_growth=False)

        # Combined axes x1+x2 and x1-x2 (helps oriented ripples)
        add_trig(x1 + x2, "(x1 + x2)", w_sum, with_decay=False, with_amp_growth=False)
        add_trig(x1 - x2, "(x1 - x2)", w_diff, with_decay=False, with_amp_growth=False)

        # Also include a few nonlinear combinations
        # sin(w*x1)*cos(w*x2) style couplings for few selected w to limit count
        w_couple = [w for w in self._unique_sorted(list(set(w_x1 + w_x2))) if w <= 40.0][:6]
        for w in w_couple:
            if len(features) >= max_features:
                break
            w_str = f"{w:.12g}"
            sx1 = np.sin(w * x1)
            cx1 = np.cos(w * x1)
            sx2 = np.sin(w * x2)
            cx2 = np.cos(w * x2)
            add_feature(sx1 * cx2, f"(sin({w_str}*x1)*cos({w_str}*x2))")
            add_feature(cx1 * sx2, f"(cos({w_str}*x1)*sin({w_str}*x2))")
            add_feature(sx1 * sx2, f"(sin({w_str}*x1)*sin({w_str}*x2))")
            add_feature(cx1 * cx2, f"(cos({w_str}*x1)*cos({w_str}*x2))")

        Phi = np.column_stack(features) if features else np.zeros((n, 0))
        return Phi, exprs

    def _fit_ols(self, Phi, y):
        n = Phi.shape[0]
        ones = np.ones((n, 1), dtype=float)
        Xd = np.hstack([ones, Phi]) if Phi.size else ones
        try:
            w_full, _, _, _ = np.linalg.lstsq(Xd, y, rcond=None)
        except Exception:
            # Fallback to pinv
            w_full = np.linalg.pinv(Xd) @ y
        intercept = float(w_full[0])
        coeffs = w_full[1:] if w_full.shape[0] > 1 else np.zeros((0,), dtype=float)
        return intercept, coeffs

    def _select_top_features(self, Phi, coeffs, top_k):
        # score: |w_j| * std(phi_j)
        if Phi.size == 0 or coeffs.size == 0:
            return np.array([], dtype=int)
        stds = np.sqrt(np.mean(Phi**2, axis=0))
        scores = np.abs(coeffs) * stds
        order = np.argsort(-scores)
        k = min(top_k, Phi.shape[1])
        return order[:k]

    def _prune_by_threshold(self, Phi, coeffs, ratio):
        if Phi.size == 0 or coeffs.size == 0:
            return np.array([], dtype=int)
        stds = np.sqrt(np.mean(Phi**2, axis=0))
        contrib = np.abs(coeffs) * stds
        if contrib.size == 0:
            return np.array([], dtype=int)
        maxc = float(np.max(contrib))
        if maxc <= 0 or not np.isfinite(maxc):
            # keep all to avoid empty set
            return np.arange(Phi.shape[1])
        mask = contrib >= (ratio * maxc)
        idx = np.where(mask)[0]
        if idx.size == 0:
            # keep the single best if everything below threshold
            idx = np.array([int(np.argmax(contrib))])
        return idx

    def _build_expression(self, intercept, coeffs, selected_exprs):
        # Compose expression string
        terms = []
        # Intercept
        c0_str = f"{intercept:.12g}"
        expression = c0_str

        for c, e in zip(coeffs, selected_exprs):
            if not np.isfinite(c):
                continue
            if abs(c) < 1e-14:
                continue
            c_str = f"{c:.12g}"
            # If the expression starts with '-' and coefficient negative, could simplify, but keep general
            terms.append(f"({c_str})*({e})")

        if terms:
            expression = "(" + expression + ")"
            for t in terms:
                # Handle sign inside t via multiplication; always add with +
                expression += " + " + t
        return expression

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        X = np.asarray(X, dtype=float)
        y = np.asarray(y, dtype=float).reshape(-1)
        n, d = X.shape
        if d != 2:
            # Fallback simple linear fit if dimensions unexpected
            A = np.column_stack([X, np.ones(n)])
            coeffs, _, _, _ = np.linalg.lstsq(A, y, rcond=None)
            a, b, c = coeffs[0], coeffs[1], coeffs[2]
            expression = f"({a:.12g})*x1 + ({b:.12g})*x2 + ({c:.12g})"
            preds = A @ coeffs
            return {"expression": expression, "predictions": preds.tolist(), "details": {}}

        # Build library
        Phi, exprs = self._build_feature_library(X, max_features=self.max_initial_features)

        # If no features, fallback to linear baseline
        if Phi.size == 0:
            A = np.column_stack([X[:, 0], X[:, 1], np.ones(n)])
            coeffs, _, _, _ = np.linalg.lstsq(A, y, rcond=None)
            a, b, c = coeffs
            expression = f"({a:.12g})*x1 + ({b:.12g})*x2 + ({c:.12g})"
            preds = A @ coeffs
            return {"expression": expression, "predictions": preds.tolist(), "details": {}}

        # Initial OLS fit
        intercept, coeffs = self._fit_ols(Phi, y)

        # Select top-K by contribution
        idx_top = self._select_top_features(Phi, coeffs, self.top_k_initial)
        Phi_top = Phi[:, idx_top]
        exprs_top = [exprs[i] for i in idx_top]

        # Refit on top-K
        intercept2, coeffs2 = self._fit_ols(Phi_top, y)

        # Prune by threshold
        idx_prune_rel = self._prune_by_threshold(Phi_top, coeffs2, self.threshold_ratio)

        # Limit final number of terms
        if idx_prune_rel.size > self.final_top_k:
            # Select by highest contribution
            stds = np.sqrt(np.mean(Phi_top**2, axis=0))
            contrib = np.abs(coeffs2) * stds
            order = np.argsort(-contrib)
            idx_prune_rel = order[:self.final_top_k]

        Phi_final = Phi_top[:, idx_prune_rel]
        exprs_final = [exprs_top[i] for i in idx_prune_rel]

        # Final fit
        intercept_final, coeffs_final = self._fit_ols(Phi_final, y)

        # Predictions
        ones = np.ones((n, 1), dtype=float)
        if Phi_final.size:
            Xd_final = np.hstack([ones, Phi_final])
            w_final = np.concatenate([[intercept_final], coeffs_final])
            preds = Xd_final @ w_final
        else:
            preds = ones.flatten() * intercept_final

        # Build final expression
        expression = self._build_expression(intercept_final, coeffs_final, exprs_final)

        return {
            "expression": expression,
            "predictions": preds.tolist(),
            "details": {}
        }