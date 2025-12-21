import numpy as np

class Solution:
    def __init__(self, **kwargs):
        self.random_state = kwargs.get("random_state", 42)

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        X = np.asarray(X, dtype=float)
        y = np.asarray(y, dtype=float).ravel()
        n, d = X.shape
        if d != 2:
            raise ValueError("X must have exactly 2 columns: x1, x2")
        x1 = X[:, 0]
        x2 = X[:, 1]
        y_scale = max(1.0, np.std(y))
        best = {"mse": np.inf, "expression": None, "pred": None}

        # Baseline linear model
        base_expr, base_pred, base_mse = self._fit_linear_baseline(x1, x2, y)
        best = self._consider_candidate(best, base_expr, base_pred, y)

        # Prepare radial variables
        r2 = x1 * x1 + x2 * x2
        r = np.sqrt(r2)

        # Frequency grids
        wgrid_r = self._make_frequency_grid(np.ptp(r), cycles=[1, 2, 3, 4, 5, 6, 8, 10, 12, 15, 18, 22])
        wgrid_r2 = self._make_frequency_grid(np.ptp(r2), cycles=[0.5, 1, 2, 3, 4, 6, 8, 10, 12], clamp_min=0.05, clamp_max=120.0)
        wgrid_x1 = self._make_frequency_grid(np.ptp(x1), cycles=[1, 2, 3, 4, 5, 6, 8, 10, 12])
        wgrid_x2 = self._make_frequency_grid(np.ptp(x2), cycles=[1, 2, 3, 4, 5, 6, 8, 10, 12])

        # Radial: A(r) * sin(w*r) + B(r) * cos(w*r), degree 0..2
        for deg in [0, 1, 2]:
            for w in wgrid_r:
                expr, pred, mse = self._fit_radial_trig(r, r2, y, w, deg, denom=None, dval=None)
                best = self._consider_candidate(best, expr, pred, y)

        # Radial with denominator (1 + d*(r2))
        d_scale_r2 = 1.0 / (np.mean(r2) + 1e-8)
        for deg in [0, 1, 2]:
            for w in wgrid_r:
                for dval in [0.5 * d_scale_r2, 1.0 * d_scale_r2, 2.0 * d_scale_r2]:
                    expr, pred, mse = self._fit_radial_trig(r, r2, y, w, deg, denom="r2", dval=dval)
                    best = self._consider_candidate(best, expr, pred, y)

        # Trig of r2: A(r2) * sin(w*r2) + B(r2) * cos(w*r2), degree 0..1
        for deg in [0, 1]:
            for w in wgrid_r2:
                expr, pred, mse = self._fit_r2_trig(r2, y, w, deg)
                best = self._consider_candidate(best, expr, pred, y)

        # Separable product sin/cos with optional denominator on r2
        d_scale_r2 = 1.0 / (np.mean(r2) + 1e-8)
        for w1 in wgrid_x1:
            s1, c1 = np.sin(w1 * x1), np.cos(w1 * x1)
            for w2 in wgrid_x2:
                s2, c2 = np.sin(w2 * x2), np.cos(w2 * x2)
                # Product only, no denominator
                expr, pred, mse = self._fit_separable(x1, x2, r2, y, w1, w2, use_product=True, use_sum=False, dval=None)
                best = self._consider_candidate(best, expr, pred, y)
                # Product with denominator
                for dval in [0.5 * d_scale_r2, 1.0 * d_scale_r2]:
                    expr, pred, mse = self._fit_separable(x1, x2, r2, y, w1, w2, use_product=True, use_sum=False, dval=dval)
                    best = self._consider_candidate(best, expr, pred, y)

        # Additive sin/cos with optional denominator on r2
        for w1 in wgrid_x1:
            for w2 in wgrid_x2:
                expr, pred, mse = self._fit_separable(x1, x2, r2, y, w1, w2, use_product=False, use_sum=True, dval=None)
                best = self._consider_candidate(best, expr, pred, y)
                for dval in [0.5 * d_scale_r2, 1.0 * d_scale_r2]:
                    expr, pred, mse = self._fit_separable(x1, x2, r2, y, w1, w2, use_product=False, use_sum=True, dval=dval)
                    best = self._consider_candidate(best, expr, pred, y)

        # If nothing better than baseline, keep baseline
        expression = best["expression"] if best["expression"] is not None else base_expr
        predictions = best["pred"] if best["pred"] is not None else base_pred

        return {
            "expression": expression,
            "predictions": predictions.tolist(),
            "details": {}
        }

    # Helper: baseline linear fit
    def _fit_linear_baseline(self, x1, x2, y):
        A = np.column_stack([x1, x2, np.ones_like(x1)])
        coeffs, _, _, _ = np.linalg.lstsq(A, y, rcond=None)
        a, b, c = coeffs
        expr = f"{self._fmt(a)}*x1 + {self._fmt(b)}*x2 + {self._fmt(c)}"
        y_pred = a * x1 + b * x2 + c
        mse = self._mse(y, y_pred)
        return expr, y_pred, mse

    # Helper: frequency grid based on range and desired cycle counts
    def _make_frequency_grid(self, rng, cycles, clamp_min=0.1, clamp_max=200.0):
        rng = float(rng)
        if not np.isfinite(rng) or rng <= 1e-12:
            rng = 1.0
        ws = []
        for c in cycles:
            w = 2.0 * np.pi * float(c) / rng
            if np.isfinite(w):
                w = float(np.clip(w, clamp_min, clamp_max))
                if w not in ws:
                    ws.append(w)
        # Ensure uniqueness and sorted
        ws = sorted(set(ws))
        if len(ws) == 0:
            ws = [1.0]
        return ws

    # Radial trig: sum_i [a_i r^i sin(w*r)/den + b_i r^i cos(w*r)/den] + intercept (+ optionally 1/den)
    def _fit_radial_trig(self, r, r2, y, w, deg, denom=None, dval=None):
        n = r.shape[0]
        # Build denominator if requested
        den_arr = None
        den_expr = None
        if denom is None:
            pass
        elif denom == "r2":
            den_arr = 1.0 + dval * r2
            if np.any(np.abs(den_arr) < 1e-8) or not np.all(np.isfinite(den_arr)):
                return None, None, np.inf
            den_expr = f"(1 + {self._fmt(dval)}*(x1**2 + x2**2))"
        elif denom == "r":
            den_arr = 1.0 + dval * r
            if np.any(np.abs(den_arr) < 1e-8) or not np.all(np.isfinite(den_arr)):
                return None, None, np.inf
            den_expr = f"(1 + {self._fmt(dval)}*((x1**2 + x2**2)**0.5))"
        else:
            return None, None, np.inf

        s = np.sin(w * r)
        c = np.cos(w * r)
        if den_arr is not None:
            s = s / den_arr
            c = c / den_arr

        features = []
        feature_exprs = []
        # amplitude powers r**i
        for i in range(deg + 1):
            if i == 0:
                amp_arr = np.ones_like(r)
                amp_expr = "1"
            else:
                amp_arr = r ** i
                amp_expr = f"((x1**2 + x2**2)**0.5)**{i}"

            features.append(amp_arr * s)
            sin_expr = f"sin({self._fmt(w)}*((x1**2 + x2**2)**0.5))"
            if den_expr is not None:
                feature_exprs.append(f"({amp_expr}*{sin_expr})/{den_expr}")
            else:
                feature_exprs.append(f"{amp_expr}*{sin_expr}")

            features.append(amp_arr * c)
            cos_expr = f"cos({self._fmt(w)}*((x1**2 + x2**2)**0.5))"
            if den_expr is not None:
                feature_exprs.append(f"({amp_expr}*{cos_expr})/{den_expr}")
            else:
                feature_exprs.append(f"{amp_expr}*{cos_expr}")

        # Optionally include 1/denominator as a feature
        extra_features = []
        extra_exprs = []
        if den_arr is not None:
            inv_den = 1.0 / den_arr
            extra_features.append(inv_den)
            extra_exprs.append(f"1/{den_expr}")

        # Add intercept as final column of ones in the regression
        A = np.column_stack(features + extra_features + [np.ones(n)])
        if not np.all(np.isfinite(A)):
            return None, None, np.inf

        try:
            coeffs, _, _, _ = np.linalg.lstsq(A, y, rcond=None)
        except Exception:
            return None, None, np.inf

        # Extract coefficients
        m = len(features)
        m_extra = len(extra_features)
        coef_main = coeffs[:m]
        coef_extra = coeffs[m:m + m_extra] if m_extra > 0 else np.array([])
        intercept = coeffs[-1]

        y_pred = A @ coeffs
        mse = self._mse(y, y_pred)

        # Build expression string
        expr_terms = []
        # keep only significant coefficients
        thresh = 1e-8 * max(1.0, np.std(y))
        for coef, expr in zip(coef_main, feature_exprs):
            if not np.isfinite(coef) or abs(coef) < thresh:
                continue
            expr_terms.append(f"{self._fmt(coef)}*{expr}")
        for coef, expr in zip(coef_extra, extra_exprs):
            if not np.isfinite(coef) or abs(coef) < thresh:
                continue
            expr_terms.append(f"{self._fmt(coef)}*{expr}")

        expression = self._combine_expression(intercept, expr_terms)
        return expression, y_pred, mse

    # r2 trig: sum_i [a_i r2^i sin(w*r2) + b_i r2^i cos(w*r2)] + intercept
    def _fit_r2_trig(self, r2, y, w, deg):
        n = r2.shape[0]
        s = np.sin(w * r2)
        c = np.cos(w * r2)
        features = []
        feature_exprs = []
        for i in range(deg + 1):
            if i == 0:
                amp_arr = np.ones_like(r2)
                amp_expr = "1"
            else:
                amp_arr = r2 ** i
                amp_expr = f"(x1**2 + x2**2)**{i}"

            features.append(amp_arr * s)
            feature_exprs.append(f"{amp_expr}*sin({self._fmt(w)}*(x1**2 + x2**2))")
            features.append(amp_arr * c)
            feature_exprs.append(f"{amp_expr}*cos({self._fmt(w)}*(x1**2 + x2**2))")

        A = np.column_stack(features + [np.ones(n)])
        if not np.all(np.isfinite(A)):
            return None, None, np.inf

        try:
            coeffs, _, _, _ = np.linalg.lstsq(A, y, rcond=None)
        except Exception:
            return None, None, np.inf

        m = len(features)
        coef_main = coeffs[:m]
        intercept = coeffs[-1]
        y_pred = A @ coeffs
        mse = self._mse(y, y_pred)

        expr_terms = []
        thresh = 1e-8 * max(1.0, np.std(y))
        for coef, expr in zip(coef_main, feature_exprs):
            if not np.isfinite(coef) or abs(coef) < thresh:
                continue
            expr_terms.append(f"{self._fmt(coef)}*{expr}")

        expression = self._combine_expression(intercept, expr_terms)
        return expression, y_pred, mse

    # Separable sin/cos (product or sum), optional denominator on r2
    def _fit_separable(self, x1, x2, r2, y, w1, w2, use_product=True, use_sum=False, dval=None):
        n = x1.shape[0]
        s1, c1 = np.sin(w1 * x1), np.cos(w1 * x1)
        s2, c2 = np.sin(w2 * x2), np.cos(w2 * x2)

        denom_arr = None
        denom_expr = None
        if dval is not None:
            denom_arr = 1.0 + dval * r2
            if np.any(np.abs(denom_arr) < 1e-8) or not np.all(np.isfinite(denom_arr)):
                return None, None, np.inf
            denom_expr = f"(1 + {self._fmt(dval)}*(x1**2 + x2**2))"

        features = []
        feature_exprs = []

        if use_product:
            terms = [
                (s1 * s2, f"sin({self._fmt(w1)}*x1)*sin({self._fmt(w2)}*x2)"),
                (s1 * c2, f"sin({self._fmt(w1)}*x1)*cos({self._fmt(w2)}*x2)"),
                (c1 * s2, f"cos({self._fmt(w1)}*x1)*sin({self._fmt(w2)}*x2)"),
                (c1 * c2, f"cos({self._fmt(w1)}*x1)*cos({self._fmt(w2)}*x2)"),
            ]
            for arr, expr in terms:
                if denom_arr is not None:
                    features.append(arr / denom_arr)
                    feature_exprs.append(f"({expr})/{denom_expr}")
                else:
                    features.append(arr)
                    feature_exprs.append(expr)

        if use_sum:
            terms = [
                (s1, f"sin({self._fmt(w1)}*x1)"),
                (c1, f"cos({self._fmt(w1)}*x1)"),
                (s2, f"sin({self._fmt(w2)}*x2)"),
                (c2, f"cos({self._fmt(w2)}*x2)"),
            ]
            for arr, expr in terms:
                if denom_arr is not None:
                    features.append(arr / denom_arr)
                    feature_exprs.append(f"({expr})/{denom_expr}")
                else:
                    features.append(arr)
                    feature_exprs.append(expr)

        # Optionally add 1/denominator feature
        extra_features = []
        extra_exprs = []
        if denom_arr is not None:
            inv_den = 1.0 / denom_arr
            extra_features.append(inv_den)
            extra_exprs.append(f"1/{denom_expr}")

        if len(features) == 0:
            return None, None, np.inf

        A = np.column_stack(features + extra_features + [np.ones(n)])
        if not np.all(np.isfinite(A)):
            return None, None, np.inf

        try:
            coeffs, _, _, _ = np.linalg.lstsq(A, y, rcond=None)
        except Exception:
            return None, None, np.inf

        m = len(features)
        m_extra = len(extra_features)
        coef_main = coeffs[:m]
        coef_extra = coeffs[m:m + m_extra] if m_extra > 0 else np.array([])
        intercept = coeffs[-1]

        y_pred = A @ coeffs
        mse = self._mse(y, y_pred)

        thresh = 1e-8 * max(1.0, np.std(y))
        expr_terms = []
        for coef, expr in zip(coef_main, feature_exprs):
            if not np.isfinite(coef) or abs(coef) < thresh:
                continue
            expr_terms.append(f"{self._fmt(coef)}*{expr}")
        for coef, expr in zip(coef_extra, extra_exprs):
            if not np.isfinite(coef) or abs(coef) < thresh:
                continue
            expr_terms.append(f"{self._fmt(coef)}*{expr}")

        expression = self._combine_expression(intercept, expr_terms)
        return expression, y_pred, mse

    # Utilities
    def _consider_candidate(self, best, expr, pred, y):
        if expr is None or pred is None:
            return best
        mse = self._mse(y, pred)
        if mse < best["mse"]:
            best = {"mse": mse, "expression": expr, "pred": pred}
        return best

    def _mse(self, y_true, y_pred):
        diff = y_true - y_pred
        return float(np.mean(diff * diff))

    def _fmt(self, v):
        if not np.isfinite(v):
            v = 0.0
        # Trim tiny values to zero for readability
        if abs(v) < 1e-12:
            v = 0.0
        return f"{v:.12g}"

    def _combine_expression(self, intercept, terms):
        terms = [t for t in terms if t is not None and len(t) > 0]
        expr = self._fmt(intercept)
        if len(terms) > 0:
            expr = " + ".join([expr] + terms)
        return expr.strip()
