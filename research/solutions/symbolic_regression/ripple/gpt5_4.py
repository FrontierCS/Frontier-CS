import numpy as np

class Solution:
    def __init__(self, max_terms=14, rel_tol=1e-5, random_state=42):
        self.max_terms = int(max_terms)
        self.rel_tol = float(rel_tol)
        self.random_state = int(random_state)

    def _fmt(self, x):
        if not np.isfinite(x):
            return "0"
        if abs(x) < 1e-14:
            return "0"
        return f"{x:.12g}"

    def _generate_features(self, X):
        n = X.shape[0]
        x1 = X[:, 0].astype(float)
        x2 = X[:, 1].astype(float)

        # Precompute basic terms
        s = x1 * x1 + x2 * x2
        r = np.sqrt(np.maximum(s, 0.0))

        # Ranges for adaptive frequencies
        def safe_range(v):
            vmax = float(np.max(v))
            vmin = float(np.min(v))
            rng = vmax - vmin
            if not np.isfinite(rng) or rng <= 1e-12:
                return 1.0
            return rng

        rng_x1 = safe_range(x1)
        rng_x2 = safe_range(x2)
        rng_r = safe_range(r)
        rng_s = safe_range(s)

        pi2 = 2.0 * np.pi

        # Cycles across range -> convert to angular freq
        cycles_r = [1, 2, 3, 4, 5, 6, 8, 10, 12]
        cycles_s = [1, 2, 3, 4, 5, 6]
        cycles_x = [1, 2, 3, 4, 5, 7, 10]
        cycles_sumdiff = [1, 2, 3, 4, 5]

        wr_list = [pi2 * c / max(rng_r, 1e-9) for c in cycles_r]
        ws_list = [pi2 * c / max(rng_s, 1e-12) for c in cycles_s]
        wx1_list = [pi2 * c / max(rng_x1, 1e-9) for c in cycles_x]
        wx2_list = [pi2 * c / max(rng_x2, 1e-9) for c in cycles_x]
        wsumdiff_list = [pi2 * c / max(rng_r + rng_x1 + rng_x2, 1e-9) for c in cycles_sumdiff]

        # Strings for expressions
        str_x1 = "x1"
        str_x2 = "x2"
        str_s = "(x1**2 + x2**2)"
        str_r = f"({str_s}**0.5)"

        # Feature storage
        vectors = []
        meta = []
        expr_set = set()

        def add_feature(expr, vec, group_key=None, amp_expr=None, tag=None):
            if expr in expr_set:
                return
            if not np.all(np.isfinite(vec)):
                return
            var = float(np.var(vec))
            if not np.isfinite(var) or var < 1e-18:
                return
            expr_set.add(expr)
            vectors.append(vec.astype(float))
            meta.append({
                "expr": expr,
                "group_key": group_key,
                "amp_expr": amp_expr,
                "tag": tag
            })

        # Polynomial/base features
        add_feature(str_s, s, group_key=None, amp_expr=None, tag="poly")
        add_feature(str_x1, x1, group_key=None, amp_expr=None, tag="poly")
        add_feature(str_x2, x2, group_key=None, amp_expr=None, tag="poly")
        add_feature(f"{str_x1}**2", x1 * x1, group_key=None, amp_expr=None, tag="poly")
        add_feature(f"{str_x2}**2", x2 * x2, group_key=None, amp_expr=None, tag="poly")
        add_feature(f"{str_x1}*{str_x2}", x1 * x2, group_key=None, amp_expr=None, tag="poly")

        # Amplitude terms for radial trig
        amp_map = {
            "1": np.ones(n),
            "r": r,
            "s": s,
        }
        amp_str_map = {
            "1": "1",
            "r": str_r,
            "s": str_s,
        }
        amp_list_r = ["1", "r", "s"]
        amp_list_s = ["1", "s"]

        # Radial trig with r
        for w in wr_list:
            sin_vec = np.sin(w * r)
            cos_vec = np.cos(w * r)
            w_str = self._fmt(w)
            base_sin_str = f"sin({w_str}*{str_r})"
            base_cos_str = f"cos({w_str}*{str_r})"
            for amp_key in amp_list_r:
                amp_vec = amp_map[amp_key]
                amp_str = amp_str_map[amp_key]
                # sin
                if amp_key == "1":
                    expr = base_sin_str
                else:
                    expr = f"{amp_str}*{base_sin_str}"
                add_feature(expr, amp_vec * sin_vec, group_key=base_sin_str, amp_expr=amp_key, tag="radial_r_sin")
                # cos
                if amp_key == "1":
                    expr = base_cos_str
                else:
                    expr = f"{amp_str}*{base_cos_str}"
                add_feature(expr, amp_vec * cos_vec, group_key=base_cos_str, amp_expr=amp_key, tag="radial_r_cos")

        # Radial trig with s
        for w in ws_list:
            sin_vec = np.sin(w * s)
            cos_vec = np.cos(w * s)
            w_str = self._fmt(w)
            base_sin_str = f"sin({w_str}*{str_s})"
            base_cos_str = f"cos({w_str}*{str_s})"
            for amp_key in amp_list_s:
                amp_vec = amp_map[amp_key]
                amp_str = amp_str_map[amp_key]
                if amp_key == "1":
                    expr = base_sin_str
                else:
                    expr = f"{amp_str}*{base_sin_str}"
                add_feature(expr, amp_vec * sin_vec, group_key=base_sin_str, amp_expr=amp_key, tag="radial_s_sin")
                if amp_key == "1":
                    expr = base_cos_str
                else:
                    expr = f"{amp_str}*{base_cos_str}"
                add_feature(expr, amp_vec * cos_vec, group_key=base_cos_str, amp_expr=amp_key, tag="radial_s_cos")

        # 1D trig on x1
        for w in wx1_list:
            w_str = self._fmt(w)
            expr = f"sin({w_str}*{str_x1})"
            add_feature(expr, np.sin(w * x1), group_key=None, amp_expr=None, tag="x1_sin")
            expr = f"cos({w_str}*{str_x1})"
            add_feature(expr, np.cos(w * x1), group_key=None, amp_expr=None, tag="x1_cos")

        # 1D trig on x2
        for w in wx2_list:
            w_str = self._fmt(w)
            expr = f"sin({w_str}*{str_x2})"
            add_feature(expr, np.sin(w * x2), group_key=None, amp_expr=None, tag="x2_sin")
            expr = f"cos({w_str}*{str_x2})"
            add_feature(expr, np.cos(w * x2), group_key=None, amp_expr=None, tag="x2_cos")

        # Sum/diff combinations
        u_plus = x1 + x2
        u_minus = x1 - x2
        str_u_plus = f"({str_x1}+{str_x2})"
        str_u_minus = f"({str_x1}-{str_x2})"
        rng_u = safe_range(u_plus) + safe_range(u_minus)
        for c in cycles_sumdiff:
            w = pi2 * c / max(rng_u, 1e-9)
            w_str = self._fmt(w)
            expr = f"sin({w_str}*{str_u_plus})"
            add_feature(expr, np.sin(w * u_plus), group_key=None, amp_expr=None, tag="sum_sin")
            expr = f"cos({w_str}*{str_u_plus})"
            add_feature(expr, np.cos(w * u_plus), group_key=None, amp_expr=None, tag="sum_cos")
            expr = f"sin({w_str}*{str_u_minus})"
            add_feature(expr, np.sin(w * u_minus), group_key=None, amp_expr=None, tag="diff_sin")
            expr = f"cos({w_str}*{str_u_minus})"
            add_feature(expr, np.cos(w * u_minus), group_key=None, amp_expr=None, tag="diff_cos")

        F = np.column_stack(vectors) if vectors else np.zeros((n, 0), dtype=float)
        return F, meta

    def _omp_select(self, F, y, max_terms, rel_tol):
        n = y.shape[0]
        if F.size == 0:
            intercept = float(np.mean(y))
            return [], np.array([], dtype=float), intercept

        ones = np.ones(n, dtype=float)
        intercept = float(np.mean(y))
        y_hat = np.full(n, intercept, dtype=float)
        resid = y - y_hat

        norms2 = np.sum(F * F, axis=0)
        selected = []
        remaining = np.arange(F.shape[1])

        for _ in range(max_terms):
            if remaining.size == 0:
                break
            # Compute improvement for each remaining feature
            dots = F[:, remaining].T @ resid  # shape (m_remaining,)
            denom = norms2[remaining] + 1e-18
            improvements = (dots * dots) / denom
            best_idx_local = int(np.argmax(improvements))
            best_improve = float(improvements[best_idx_local])
            sse = float(np.dot(resid, resid))
            # Stopping criterion
            if best_improve <= self.rel_tol * max(sse, 1e-12):
                break

            feat_global_idx = int(remaining[best_idx_local])
            selected.append(feat_global_idx)
            # Fit OLS with intercept and selected features
            A = np.column_stack([ones, F[:, selected]])
            # Solve using least squares
            coef, _, _, _ = np.linalg.lstsq(A, y, rcond=None)
            intercept = float(coef[0])
            betas = coef[1:].astype(float)
            y_hat = A @ coef
            resid = y - y_hat

            # Update remaining pool
            remaining = np.array([j for j in remaining if j != feat_global_idx], dtype=int)

        # Final fit
        if selected:
            A = np.column_stack([ones, F[:, selected]])
            coef, _, _, _ = np.linalg.lstsq(A, y, rcond=None)
            intercept = float(coef[0])
            betas = coef[1:].astype(float)
        else:
            betas = np.array([], dtype=float)

        return selected, betas, intercept

    def _build_expression(self, meta, selected, betas, intercept):
        # Group factorization: group_key is base trig (e.g., sin(w*r)), amp_expr in {"1","r","s"}
        # Collect contributions
        grouped = {}
        others = []  # list of (coef, expr)
        for idx, coef in zip(selected, betas):
            if abs(coef) < 1e-14:
                continue
            m = meta[idx]
            gk = m.get("group_key", None)
            amp = m.get("amp_expr", None)
            expr = m["expr"]
            if gk is not None and amp in ("1", "r", "s"):
                if gk not in grouped:
                    grouped[gk] = {"1": 0.0, "r": 0.0, "s": 0.0, "base": gk}
                grouped[gk][amp] += float(coef)
            else:
                others.append((float(coef), expr))

        # Build expression parts
        parts = []

        # Intercept
        if abs(intercept) > 1e-14:
            parts.append(self._fmt(intercept))

        # Factorized groups
        def amp_str_builder(a0, a_r, a_s):
            subparts = []
            if abs(a0) > 1e-14:
                subparts.append(self._fmt(a0))
            if abs(a_r) > 1e-14:
                coef_str = self._fmt(a_r)
                r_str = "((x1**2 + x2**2)**0.5)"
                subparts.append(f"{coef_str}*{r_str}")
            if abs(a_s) > 1e-14:
                coef_str = self._fmt(a_s)
                s_str = "(x1**2 + x2**2)"
                subparts.append(f"{coef_str}*{s_str}")
            if not subparts:
                return None
            return "(" + " + ".join(subparts) + ")"

        for gk, d in grouped.items():
            a0 = d.get("1", 0.0)
            ar = d.get("r", 0.0)
            aS = d.get("s", 0.0)
            amp_str = amp_str_builder(a0, ar, aS)
            if amp_str is None:
                continue
            parts.append(f"{amp_str}*{gk}")

        # Other terms (not factorized)
        for coef, expr in others:
            coef_str = self._fmt(coef)
            parts.append(f"{coef_str}*{expr}")

        if not parts:
            return "0"

        # Build final expression as sum
        expression = " + ".join(parts)
        # Clean potential "+ -" patterns by converting "+ -a" to "- a"
        # Basic cleanup without regex
        expression = expression.replace("+ -", "- ")
        return expression

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        X = np.asarray(X, dtype=float)
        y = np.asarray(y, dtype=float).ravel()
        if X.ndim != 2 or X.shape[1] != 2:
            # Fallback simple linear
            x1, x2 = X[:, 0], X[:, 1]
            A = np.column_stack([x1, x2, np.ones_like(x1)])
            coeffs, _, _, _ = np.linalg.lstsq(A, y, rcond=None)
            a, b, c = coeffs
            expression = f"{self._fmt(a)}*x1 + {self._fmt(b)}*x2 + {self._fmt(c)}"
            predictions = (a * x1 + b * x2 + c)
            return {
                "expression": expression,
                "predictions": predictions.tolist(),
                "details": {}
            }

        # Generate candidate features
        F, meta = self._generate_features(X)

        # Feature selection
        selected, betas, intercept = self._omp_select(F, y, self.max_terms, self.rel_tol)

        # Predictions
        if selected:
            y_pred = intercept + F[:, selected] @ betas
        else:
            y_pred = np.full_like(y, intercept)

        # Build expression string
        expression = self._build_expression(meta, selected, betas, intercept)

        return {
            "expression": expression,
            "predictions": y_pred.tolist(),
            "details": {}
        }