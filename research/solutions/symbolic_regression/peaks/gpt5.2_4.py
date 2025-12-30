import numpy as np

class Solution:
    def __init__(self, **kwargs):
        self.kwargs = kwargs

    @staticmethod
    def _safe_lstsq(A, y):
        try:
            coef, _, _, _ = np.linalg.lstsq(A, y, rcond=None)
            return coef
        except Exception:
            try:
                coef = np.linalg.pinv(A) @ y
                return coef
            except Exception:
                return None

    @staticmethod
    def _mse(y, yhat):
        r = y - yhat
        return float(np.mean(r * r))

    @staticmethod
    def _build_terms(x1, x2):
        # MATLAB "peaks" inspired terms
        t1 = (1.0 - x1) ** 2 * np.exp(-(x1 * x1) - (x2 + 1.0) ** 2)
        t2 = (x1 / 5.0 - x1 ** 3 - x2 ** 5) * np.exp(-(x1 * x1) - (x2 * x2))
        t3 = np.exp(-(x1 + 1.0) ** 2 - (x2 * x2))
        return t1, t2, t3

    @staticmethod
    def _fit_best_subset(t1, t2, t3, y):
        terms = [t1, t2, t3]
        n = y.shape[0]
        best = None

        for include_const in (0, 1):
            for mask in range(1, 8):  # at least one term
                cols = []
                idxs = []
                for i in range(3):
                    if (mask >> i) & 1:
                        cols.append(terms[i])
                        idxs.append(i)
                if include_const:
                    cols.append(np.ones(n, dtype=float))
                A = np.column_stack(cols).astype(float, copy=False)
                coef = Solution._safe_lstsq(A, y)
                if coef is None:
                    continue
                yhat = A @ coef
                mse = Solution._mse(y, yhat)
                k = len(coef)
                # Tie-break: fewer parameters preferred
                cand = (mse, k, include_const, mask, coef, yhat)
                if best is None or cand[:2] < best[:2]:
                    best = cand

        # Also allow constant-only model if all terms fail (unlikely)
        if best is None:
            c = float(np.mean(y))
            yhat = np.full_like(y, c, dtype=float)
            best = (Solution._mse(y, yhat), 1, 1, 0, np.array([c], dtype=float), yhat)

        return best  # (mse, k, include_const, mask, coef, yhat)

    @staticmethod
    def _expr_from_fit(include_const, mask, coef):
        coef = np.asarray(coef, dtype=float)
        parts = []
        ci = 0

        def fmt(v):
            if not np.isfinite(v):
                v = 0.0
            s = format(float(v), ".12g")
            if s == "-0":
                s = "0"
            return s

        # Order: t1, t2, t3 then const
        if mask & 1:
            a = fmt(coef[ci]); ci += 1
            parts.append(f"({a})*(1 - x1)**2*exp(-x1**2 - (x2 + 1)**2)")
        if mask & 2:
            b = fmt(coef[ci]); ci += 1
            parts.append(f"({b})*(x1/5 - x1**3 - x2**5)*exp(-x1**2 - x2**2)")
        if mask & 4:
            c = fmt(coef[ci]); ci += 1
            parts.append(f"({c})*exp(-(x1 + 1)**2 - x2**2)")
        if include_const:
            d = fmt(coef[ci]); ci += 1
            parts.append(f"({d})")

        if not parts:
            return "0"
        return " + ".join(parts)

    @staticmethod
    def _linear_baseline(x1, x2, y):
        A = np.column_stack([x1, x2, np.ones_like(x1, dtype=float)])
        coef = Solution._safe_lstsq(A, y)
        if coef is None:
            c = float(np.mean(y))
            yhat = np.full_like(y, c, dtype=float)
            expr = format(c, ".12g")
            return expr, yhat
        a, b, c = coef
        yhat = A @ coef
        expr = f"({format(float(a), '.12g')})*x1 + ({format(float(b), '.12g')})*x2 + ({format(float(c), '.12g')})"
        return expr, yhat

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        X = np.asarray(X)
        y = np.asarray(y).astype(float, copy=False).reshape(-1)

        n = X.shape[0]
        if X.ndim != 2 or X.shape[1] != 2 or y.shape[0] != n or n == 0:
            return {"expression": "0", "predictions": [0.0] * int(n), "details": {}}

        x1 = X[:, 0].astype(float, copy=False)
        x2 = X[:, 1].astype(float, copy=False)

        # Baseline
        lin_expr, lin_pred = self._linear_baseline(x1, x2, y)
        lin_mse = self._mse(y, lin_pred)

        # Peaks-like fit, both variable orders
        t1, t2, t3 = self._build_terms(x1, x2)
        best1 = self._fit_best_subset(t1, t2, t3, y)

        ts1, ts2, ts3 = self._build_terms(x2, x1)
        best2 = self._fit_best_subset(ts1, ts2, ts3, y)

        # Choose best
        # best tuple: (mse, k, include_const, mask, coef, yhat)
        best = best1
        swapped = False
        if best2[0] < best1[0]:
            best = best2
            swapped = True

        mse_best = best[0]
        include_const, mask, coef, yhat = best[2], best[3], best[4], best[5]

        # Decide if peaks model is good; else fallback to linear
        # Accept if it improves over linear by at least 5% or if linear is poor.
        use_peaks = np.isfinite(mse_best) and (mse_best <= lin_mse * 0.95 or mse_best <= 1e-12)

        if not use_peaks:
            return {
                "expression": lin_expr,
                "predictions": lin_pred.tolist(),
                "details": {"model": "linear", "mse": lin_mse},
            }

        expr = self._expr_from_fit(include_const, mask, coef)
        if swapped:
            # Swap variable names in expression safely via placeholders
            expr = expr.replace("x1", "__tmp_x1__").replace("x2", "x1").replace("__tmp_x1__", "x2")
            # predictions already computed with swapped build_terms; keep as yhat
        return {
            "expression": expr,
            "predictions": yhat.tolist(),
            "details": {"model": "peaks_basis", "mse": mse_best, "swapped": swapped},
        }