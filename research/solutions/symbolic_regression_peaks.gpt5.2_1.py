import numpy as np

class Solution:
    def __init__(self, **kwargs):
        self.random_state = kwargs.get("random_state", 42)

    @staticmethod
    def _fmt(c: float) -> str:
        if not np.isfinite(c):
            return "0.0"
        if abs(c) < 1e-15:
            return "0.0"
        s = f"{c:.12g}"
        if s == "-0":
            s = "0"
        return s

    @staticmethod
    def _shift_expr(var: str, c: float) -> str:
        if abs(c) < 1e-15:
            return var
        if c < 0:
            return f"({var} + {Solution._fmt(-c)})"
        return f"({var} - {Solution._fmt(c)})"

    @staticmethod
    def _build_expression(intercept: float, coefs: np.ndarray, exprs: list, coef_thresh: float = 1e-12) -> str:
        parts = []
        if np.isfinite(intercept) and abs(intercept) > coef_thresh:
            parts.append(Solution._fmt(intercept))

        for a, e in zip(coefs, exprs):
            if not np.isfinite(a) or abs(a) <= coef_thresh:
                continue
            a_str = Solution._fmt(abs(a))
            if a > 0:
                if not parts:
                    parts.append(f"{a_str}*({e})")
                else:
                    parts.append(f"+ {a_str}*({e})")
            else:
                if not parts:
                    parts.append(f"- {a_str}*({e})")
                else:
                    parts.append(f"- {a_str}*({e})")

        if not parts:
            return "0.0"
        return " ".join(parts)

    @staticmethod
    def _lstsq_fit(y: np.ndarray, cols: list):
        n = y.shape[0]
        if not cols:
            intercept = float(np.mean(y))
            pred = np.full(n, intercept, dtype=np.float64)
            return intercept, np.zeros(0, dtype=np.float64), pred
        A = np.column_stack([np.ones(n, dtype=np.float64)] + cols)
        coef, _, _, _ = np.linalg.lstsq(A, y, rcond=None)
        intercept = float(coef[0])
        coefs = coef[1:].astype(np.float64, copy=False)
        pred = A @ coef
        return intercept, coefs, pred

    @staticmethod
    def _omp(y: np.ndarray, Phi: np.ndarray, max_terms: int = 8, tol_corr: float = 1e-12, min_improve: float = 1e-10):
        n, p = Phi.shape
        if p == 0:
            intercept = float(np.mean(y))
            pred = np.full(n, intercept, dtype=np.float64)
            return intercept, np.zeros(0, dtype=np.float64), [], pred

        y = y.astype(np.float64, copy=False)
        Phi = Phi.astype(np.float64, copy=False)

        norms = np.sqrt(np.sum(Phi * Phi, axis=0))
        good = norms > 1e-14
        if not np.any(good):
            intercept = float(np.mean(y))
            pred = np.full(n, intercept, dtype=np.float64)
            return intercept, np.zeros(0, dtype=np.float64), [], pred

        Phi = Phi[:, good]
        norms = norms[good]
        p = Phi.shape[1]
        PhiN = Phi / norms

        intercept = float(np.mean(y))
        residual = y - intercept
        active = []
        best_mse = float(np.mean(residual * residual))

        for _ in range(min(max_terms, p)):
            corr = np.abs(PhiN.T @ residual)
            if active:
                corr[np.array(active, dtype=int)] = -np.inf
            j = int(np.argmax(corr))
            if not np.isfinite(corr[j]) or corr[j] < tol_corr:
                break
            active.append(j)

            cols = [Phi[:, idx] for idx in active]
            intercept_i, coefs_i, pred_i = Solution._lstsq_fit(y, cols)
            mse_i = float(np.mean((y - pred_i) ** 2))
            if best_mse - mse_i < min_improve * max(1.0, best_mse):
                active.pop()
                break
            best_mse = mse_i
            intercept = intercept_i
            residual = y - pred_i

        if not active:
            intercept = float(np.mean(y))
            pred = np.full(n, intercept, dtype=np.float64)
            return intercept, np.zeros(0, dtype=np.float64), [], pred

        cols = [Phi[:, idx] for idx in active]
        intercept, coefs, pred = Solution._lstsq_fit(y, cols)
        return intercept, coefs, active, pred

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        X = np.asarray(X, dtype=np.float64)
        y = np.asarray(y, dtype=np.float64).reshape(-1)
        n = X.shape[0]
        if n == 0:
            return {"expression": "0.0", "predictions": [], "details": {}}
        if X.shape[1] != 2:
            raise ValueError("Expected X shape (n, 2)")

        x1 = X[:, 0]
        x2 = X[:, 1]

        def expv(z):
            z = np.clip(z, -700.0, 700.0)
            return np.exp(z)

        # Canonical peaks-like components
        t1 = (1.0 - x1) ** 2 * expv(-(x1 ** 2) - (x2 + 1.0) ** 2)
        t2 = (x1 / 5.0 - x1 ** 3 - x2 ** 5) * expv(-(x1 ** 2) - (x2 ** 2))
        t3 = expv(-(x1 + 1.0) ** 2 - (x2 ** 2))

        # Fit peaks basis model
        intercept_p, coefs_p, pred_p = self._lstsq_fit(y, [t1, t2, t3])
        mse_p = float(np.mean((y - pred_p) ** 2))
        exprs_p = [
            "(1 - x1)**2*exp(-x1**2 - (x2 + 1)**2)",
            "(x1/5 - x1**3 - x2**5)*exp(-x1**2 - x2**2)",
            "exp(-(x1 + 1)**2 - x2**2)",
        ]
        expr_p = self._build_expression(intercept_p, coefs_p, exprs_p)

        # Build a broader candidate library for sparse linear combination
        cand_exprs = []
        cand_cols = []

        def add(expr: str, col: np.ndarray):
            if col is None:
                return
            col = np.asarray(col, dtype=np.float64)
            if col.shape[0] != n:
                return
            if not np.all(np.isfinite(col)):
                return
            v = float(np.var(col))
            if v < 1e-20:
                return
            cand_exprs.append(expr)
            cand_cols.append(col)

        # Polynomials
        add("x1", x1)
        add("x2", x2)
        add("x1**2", x1 ** 2)
        add("x2**2", x2 ** 2)
        add("x1*x2", x1 * x2)
        add("x1**3", x1 ** 3)
        add("x2**3", x2 ** 3)
        add("x1**4", x1 ** 4)
        add("x2**4", x2 ** 4)

        # Exponential bumps at fixed offsets
        add("exp(-x1**2 - x2**2)", expv(-(x1 ** 2) - (x2 ** 2)))
        add("exp(-(x1 + 1)**2 - x2**2)", expv(-((x1 + 1.0) ** 2) - (x2 ** 2)))
        add("exp(-(x1 - 1)**2 - x2**2)", expv(-((x1 - 1.0) ** 2) - (x2 ** 2)))
        add("exp(-x1**2 - (x2 + 1)**2)", expv(-(x1 ** 2) - ((x2 + 1.0) ** 2)))
        add("exp(-x1**2 - (x2 - 1)**2)", expv(-(x1 ** 2) - ((x2 - 1.0) ** 2)))
        add("exp(-(x1 + 1)**2 - (x2 + 1)**2)", expv(-((x1 + 1.0) ** 2) - ((x2 + 1.0) ** 2)))
        add("exp(-(x1 - 1)**2 - (x2 - 1)**2)", expv(-((x1 - 1.0) ** 2) - ((x2 - 1.0) ** 2)))

        # Peaks-style nonlinear terms
        add("(1 - x1)**2*exp(-x1**2 - (x2 + 1)**2)", t1)
        add("(x1/5 - x1**3 - x2**5)*exp(-x1**2 - x2**2)", t2)
        add("exp(-(x1 + 1)**2 - x2**2)", t3)
        t1b = (1.0 - x1) ** 2 * expv(-(x1 ** 2) - (x2 - 1.0) ** 2)
        add("(1 - x1)**2*exp(-x1**2 - (x2 - 1)**2)", t1b)
        t2s = (x2 / 5.0 - x2 ** 3 - x1 ** 5) * expv(-(x1 ** 2) - (x2 ** 2))
        add("(x2/5 - x2**3 - x1**5)*exp(-x1**2 - x2**2)", t2s)
        t3b = expv(-(x1 - 1.0) ** 2 - (x2 ** 2))
        add("exp(-(x1 - 1)**2 - x2**2)", t3b)

        # Data-adaptive Gaussian bumps
        rx = float(np.max(x1) - np.min(x1))
        ry = float(np.max(x2) - np.min(x2))
        r = 0.5 * (rx + ry)
        r = max(r, 1e-6)
        k = 1.0 / (0.55 * r) ** 2
        if not np.isfinite(k) or k <= 0:
            k = 1.0

        qs = [0.2, 0.5, 0.8]
        c1s = [float(np.quantile(x1, q)) for q in qs]
        c2s = [float(np.quantile(x2, q)) for q in qs]
        used = set()
        for c1 in c1s:
            for c2 in c2s:
                key = (round(c1, 6), round(c2, 6))
                if key in used:
                    continue
                used.add(key)
                dx = x1 - c1
                dy = x2 - c2
                g = expv(-k * (dx * dx + dy * dy))
                dx_e = self._shift_expr("x1", c1)
                dy_e = self._shift_expr("x2", c2)
                k_str = self._fmt(k)
                if abs(k - 1.0) < 1e-12:
                    expr_g = f"exp(-({dx_e})**2 - ({dy_e})**2)"
                else:
                    expr_g = f"exp(-{k_str}*(({dx_e})**2 + ({dy_e})**2))"
                add(expr_g, g)

        # OMP sparse fit on full candidate set
        if cand_cols:
            Phi = np.column_stack(cand_cols)
            intercept_o, coefs_o, active, pred_o = self._omp(y, Phi, max_terms=8)
            mse_o = float(np.mean((y - pred_o) ** 2))
            exprs_o = [cand_exprs[i] for i in active]
            expr_o = self._build_expression(intercept_o, coefs_o, exprs_o)
        else:
            intercept_o = float(np.mean(y))
            pred_o = np.full(n, intercept_o, dtype=np.float64)
            mse_o = float(np.mean((y - pred_o) ** 2))
            expr_o = self._fmt(intercept_o)
            exprs_o = []

        # Prefer simpler peaks model if close in error
        terms_p = int(np.sum(np.abs(coefs_p) > 1e-12)) + (1 if abs(intercept_p) > 1e-12 else 0)
        terms_o = len(exprs_o) + (1 if abs(intercept_o) > 1e-12 else 0)
        use_peaks = False
        if np.isfinite(mse_p) and np.isfinite(mse_o):
            if mse_p <= mse_o * 1.02 and terms_p <= max(1, terms_o - 1):
                use_peaks = True
        else:
            use_peaks = np.isfinite(mse_p)

        if use_peaks:
            expression = expr_p
            predictions = pred_p
            details = {"model": "peaks_linear", "terms": terms_p, "mse": mse_p}
        else:
            expression = expr_o
            predictions = pred_o
            details = {"model": "sparse_library", "terms": terms_o, "mse": mse_o}

        return {
            "expression": expression,
            "predictions": predictions.tolist(),
            "details": details,
        }