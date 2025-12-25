import numpy as np

class Solution:
    def __init__(self, **kwargs):
        self.kwargs = kwargs

    @staticmethod
    def _format_float(x: float) -> str:
        if not np.isfinite(x):
            return "0.0"
        if abs(x) < 5e-15:
            x = 0.0
        s = f"{x:.12g}"
        if s == "-0":
            s = "0"
        return s

    @staticmethod
    def _poly_expr(coeffs, var_expr: str, tol: float) -> str:
        terms = []
        var1 = f"({var_expr})"
        for j, c in enumerate(coeffs):
            if not np.isfinite(c) or abs(c) < tol:
                continue
            cs = Solution._format_float(float(c))
            if j == 0:
                term = f"{cs}"
            elif j == 1:
                term = f"{cs}*{var1}"
            else:
                term = f"{cs}*({var1}**{j})"
            terms.append((float(c), term))

        if not terms:
            return "0"

        expr = terms[0][1]
        for c, term in terms[1:]:
            if c >= 0:
                expr += " + " + term
            else:
                expr += " - " + term.replace("-", "", 1) if term.startswith("-") else " + " + term
        return f"({expr})"

    @staticmethod
    def _solve_ridge(A: np.ndarray, y: np.ndarray, lam: float = 1e-12):
        G = A.T @ A
        b = A.T @ y
        p = G.shape[0]
        tr = float(np.trace(G))
        reg = lam * (tr / p + 1.0)
        G.flat[:: p + 1] += reg
        try:
            beta = np.linalg.solve(G, b)
        except np.linalg.LinAlgError:
            beta = np.linalg.lstsq(A, y, rcond=None)[0]
        return beta

    def _fit_linear(self, x1, x2, y):
        n = y.shape[0]
        A = np.empty((n, 3), dtype=np.float64)
        A[:, 0] = x1
        A[:, 1] = x2
        A[:, 2] = 1.0
        beta = self._solve_ridge(A, y, lam=1e-14)
        pred = A @ beta
        mse = float(np.mean((y - pred) ** 2))
        a, b, c = beta.tolist()
        expr = f"{self._format_float(a)}*x1 + {self._format_float(b)}*x2 + {self._format_float(c)}"
        return mse, expr, pred

    def _fit_ripple_model(self, r2, y, w, deg_amp, deg_off, A_work=None):
        n = y.shape[0]
        max_deg = max(deg_amp, deg_off)
        r2_pows = [np.ones_like(r2)]
        for k in range(1, max_deg + 1):
            r2_pows.append(r2_pows[-1] * r2)

        t = w * r2
        s = np.sin(t)
        c = np.cos(t)

        p = 2 * (deg_amp + 1) + (deg_off + 1)
        if A_work is None or A_work.shape != (n, p):
            A = np.empty((n, p), dtype=np.float64)
        else:
            A = A_work

        col = 0
        for j in range(deg_amp + 1):
            A[:, col] = r2_pows[j] * s
            col += 1
        for j in range(deg_amp + 1):
            A[:, col] = r2_pows[j] * c
            col += 1
        for j in range(deg_off + 1):
            A[:, col] = r2_pows[j]
            col += 1

        beta = self._solve_ridge(A, y, lam=1e-12)
        pred = A @ beta
        mse = float(np.mean((y - pred) ** 2))
        return mse, beta, pred, A

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        X = np.asarray(X)
        y = np.asarray(y).astype(np.float64)
        x1 = X[:, 0].astype(np.float64)
        x2 = X[:, 1].astype(np.float64)

        n = y.shape[0]
        if n == 0:
            return {"expression": "0", "predictions": [], "details": {}}

        mse_lin, expr_lin, pred_lin = self._fit_linear(x1, x2, y)

        r2 = x1 * x1 + x2 * x2
        r2min = float(np.min(r2))
        r2max = float(np.max(r2))
        span = max(r2max - r2min, 1e-9)

        y_scale = float(np.std(y) + abs(np.mean(y)) + 1e-12)
        tol_coeff = 1e-10 * y_scale

        base = 2.0 * np.pi / span
        cycles = np.linspace(0.75, 80.0, 220)
        w_grid = base * cycles

        model_specs = [
            (2, 2),
            (3, 2),
            (2, 1),
            (3, 1),
        ]

        best = {
            "mse": mse_lin,
            "expr": expr_lin,
            "pred": pred_lin,
            "details": {"model": "linear"},
        }

        for deg_amp, deg_off in model_specs:
            A_work = None
            best_w = None
            best_mse = np.inf
            best_beta = None
            best_pred = None

            for w in w_grid:
                mse, beta, pred, A_work = self._fit_ripple_model(r2, y, float(w), deg_amp, deg_off, A_work=A_work)
                if mse < best_mse:
                    best_mse = mse
                    best_w = float(w)
                    best_beta = beta
                    best_pred = pred

            if best_w is None or not np.isfinite(best_mse):
                continue

            step = float(np.median(np.diff(w_grid)))
            w_curr = best_w
            beta_curr = best_beta
            pred_curr = best_pred
            mse_curr = best_mse

            for _ in range(25):
                improved = False
                for w_try in (w_curr - step, w_curr + step):
                    if w_try <= 0 or not np.isfinite(w_try):
                        continue
                    mse_try, beta_try, pred_try, A_work = self._fit_ripple_model(
                        r2, y, float(w_try), deg_amp, deg_off, A_work=A_work
                    )
                    if mse_try + 1e-15 < mse_curr:
                        w_curr = float(w_try)
                        beta_curr = beta_try
                        pred_curr = pred_try
                        mse_curr = mse_try
                        improved = True
                if not improved:
                    step *= 0.5
                    if step < 1e-12 * max(1.0, w_curr):
                        break

            if mse_curr >= best["mse"]:
                continue

            a = beta_curr[: (deg_amp + 1)]
            b = beta_curr[(deg_amp + 1) : 2 * (deg_amp + 1)]
            c = beta_curr[2 * (deg_amp + 1) :]

            r2expr = "(x1**2 + x2**2)"
            wstr = self._format_float(w_curr)
            arg = f"({wstr}*({r2expr}))"

            poly_sin = self._poly_expr(a, r2expr, tol_coeff)
            poly_cos = self._poly_expr(b, r2expr, tol_coeff)
            poly_off = self._poly_expr(c, r2expr, tol_coeff)

            expr_parts = []
            if poly_sin != "0":
                expr_parts.append(f"{poly_sin}*sin({arg})")
            if poly_cos != "0":
                expr_parts.append(f"{poly_cos}*cos({arg})")
            if poly_off != "0":
                expr_parts.append(f"{poly_off}")

            expr = " + ".join(expr_parts) if expr_parts else "0"

            best = {
                "mse": mse_curr,
                "expr": expr,
                "pred": pred_curr,
                "details": {"model": "ripple", "w": w_curr, "deg_amp": deg_amp, "deg_off": deg_off},
            }

        return {
            "expression": best["expr"],
            "predictions": best["pred"].astype(float).tolist() if best.get("pred") is not None else None,
            "details": best.get("details", {}),
        }