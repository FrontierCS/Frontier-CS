import numpy as np

class Solution:
    def __init__(self, **kwargs):
        self.random_state = int(kwargs.get("random_state", 42))

    @staticmethod
    def _mse(y_true, y_pred):
        y_true = np.asarray(y_true, dtype=np.float64)
        y_pred = np.asarray(y_pred, dtype=np.float64)
        diff = y_true - y_pred
        return float(np.mean(diff * diff))

    @staticmethod
    def _fmt(c):
        if not np.isfinite(c):
            c = 0.0
        if abs(c) < 1e-15:
            return "0.0"
        s = f"{float(c):.12g}"
        if s == "-0":
            s = "0"
        return s

    @classmethod
    def _build_expression(cls, bias, coefs, exprs, drop_tol=1e-12, one_tol=1e-6):
        parts = []
        if np.isfinite(bias) and abs(bias) > drop_tol:
            parts.append(cls._fmt(bias))
        for coef, ex in zip(coefs, exprs):
            if not np.isfinite(coef) or abs(coef) <= drop_tol:
                continue
            if abs(coef - 1.0) <= one_tol:
                parts.append(f"({ex})")
            elif abs(coef + 1.0) <= one_tol:
                parts.append(f"-({ex})")
            else:
                parts.append(f"{cls._fmt(coef)}*({ex})")
        if not parts:
            return "0.0"
        expr = parts[0]
        for p in parts[1:]:
            if p.startswith("-"):
                expr = f"({expr}) {p}"
            else:
                expr = f"({expr}) + {p}"
        return expr

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        X = np.asarray(X, dtype=np.float64)
        y = np.asarray(y, dtype=np.float64).reshape(-1)
        n = X.shape[0]
        x1 = X[:, 0]
        x2 = X[:, 1]

        with np.errstate(over="ignore", under="ignore", invalid="ignore", divide="ignore"):
            # Baseline linear model
            A_lin = np.column_stack([x1, x2, np.ones_like(x1)])
            coef_lin, _, _, _ = np.linalg.lstsq(A_lin, y, rcond=None)
            yhat_lin = A_lin @ coef_lin
            mse_lin = self._mse(y, yhat_lin)

            # Precompute common terms
            x1_2 = x1 * x1
            x2_2 = x2 * x2
            x1_3 = x1_2 * x1
            x2_3 = x2_2 * x2
            x1_4 = x1_2 * x1_2
            x2_4 = x2_2 * x2_2
            x2_5 = x2_4 * x2

            x1p1 = x1 + 1.0
            x2p1 = x2 + 1.0
            x1m1 = x1 - 1.0
            x2m1 = x2 - 1.0

            g00 = np.exp(-(x1_2 + x2_2))
            g0p1 = np.exp(-(x1_2 + x2p1 * x2p1))
            gp10 = np.exp(-(x1p1 * x1p1 + x2_2))

            # Classic peaks formula candidates
            f1 = (1.0 - x1) * (1.0 - x1) * g0p1
            f2 = (x1 / 5.0 - x1_3 - x2_5) * g00
            f3 = gp10

            yhat_peaks_fixed = 3.0 * f1 - 10.0 * f2 - (1.0 / 3.0) * f3
            mse_peaks_fixed = self._mse(y, yhat_peaks_fixed)
            expr_peaks_fixed = "3*(1 - x1)**2*exp(-(x1**2 + (x2 + 1)**2)) - 10*(x1/5 - x1**3 - x2**5)*exp(-(x1**2 + x2**2)) - (1/3)*exp(-((x1 + 1)**2 + x2**2))"

            # Fit coefficients for peaks structure (robust constants)
            A_peaks = np.column_stack([f1, f2, f3, np.ones_like(x1)])
            coef_peaks, _, _, _ = np.linalg.lstsq(A_peaks, y, rcond=None)
            yhat_peaks_fit = A_peaks @ coef_peaks
            mse_peaks_fit = self._mse(y, yhat_peaks_fit)
            expr_peaks_fit = self._build_expression(
                bias=coef_peaks[3],
                coefs=coef_peaks[:3],
                exprs=[
                    "(1 - x1)**2*exp(-(x1**2 + (x2 + 1)**2))",
                    "(x1/5 - x1**3 - x2**5)*exp(-(x1**2 + x2**2))",
                    "exp(-((x1 + 1)**2 + x2**2))",
                ],
            )

            # OMP on a compact feature library
            # Build candidate features (exclude bias; bias will be included in regression)
            g0m1 = np.exp(-(x1_2 + x2m1 * x2m1))
            gm10 = np.exp(-(x1m1 * x1m1 + x2_2))
            gpp = np.exp(-(x1p1 * x1p1 + x2p1 * x2p1))
            gmm = np.exp(-(x1m1 * x1m1 + x2m1 * x2m1))
            gpm = np.exp(-(x1p1 * x1p1 + x2m1 * x2m1))
            gmp = np.exp(-(x1m1 * x1m1 + x2p1 * x2p1))

            feats = []
            exprs = []

            def add_feat(arr, expr):
                arr = np.asarray(arr, dtype=np.float64)
                arr = np.where(np.isfinite(arr), arr, 0.0)
                feats.append(arr)
                exprs.append(expr)

            # polynomial features (low degree)
            add_feat(x1, "x1")
            add_feat(x2, "x2")
            add_feat(x1_2, "x1**2")
            add_feat(x2_2, "x2**2")
            add_feat(x1 * x2, "x1*x2")
            add_feat(x1_3, "x1**3")
            add_feat(x2_3, "x2**3")
            add_feat(x1_2 * x2, "x1**2*x2")
            add_feat(x1 * x2_2, "x1*x2**2")

            # gaussian bumps
            add_feat(g00, "exp(-(x1**2 + x2**2))")
            add_feat(g0p1, "exp(-(x1**2 + (x2 + 1)**2))")
            add_feat(g0m1, "exp(-(x1**2 + (x2 - 1)**2))")
            add_feat(gp10, "exp(-((x1 + 1)**2 + x2**2))")
            add_feat(gm10, "exp(-((x1 - 1)**2 + x2**2))")
            add_feat(gpp, "exp(-((x1 + 1)**2 + (x2 + 1)**2))")
            add_feat(gmm, "exp(-((x1 - 1)**2 + (x2 - 1)**2))")
            add_feat(gpm, "exp(-((x1 + 1)**2 + (x2 - 1)**2))")
            add_feat(gmp, "exp(-((x1 - 1)**2 + (x2 + 1)**2))")

            # gaussian * polynomial interactions (including peaks structure)
            add_feat(f1, "(1 - x1)**2*exp(-(x1**2 + (x2 + 1)**2))")
            add_feat(f2, "(x1/5 - x1**3 - x2**5)*exp(-(x1**2 + x2**2))")
            add_feat(f3, "exp(-((x1 + 1)**2 + x2**2))")
            add_feat(x1 * g00, "x1*exp(-(x1**2 + x2**2))")
            add_feat(x2 * g00, "x2*exp(-(x1**2 + x2**2))")
            add_feat(x1_2 * g00, "x1**2*exp(-(x1**2 + x2**2))")
            add_feat(x2_2 * g00, "x2**2*exp(-(x1**2 + x2**2))")
            add_feat((1.0 - x1) * g0p1, "(1 - x1)*exp(-(x1**2 + (x2 + 1)**2))")
            add_feat((x2 + 1.0) * g0p1, "(x2 + 1)*exp(-(x1**2 + (x2 + 1)**2))")
            add_feat((x1 + 1.0) * gp10, "(x1 + 1)*exp(-((x1 + 1)**2 + x2**2))")
            add_feat(x2 * gp10, "x2*exp(-((x1 + 1)**2 + x2**2))")

            Phi = np.column_stack(feats) if feats else np.empty((n, 0), dtype=np.float64)
            k = Phi.shape[1]

            # OMP settings
            max_terms = 8
            min_improve = 1e-10

            # Normalize columns for selection
            col_norm = np.linalg.norm(Phi, axis=0)
            col_norm = np.where(col_norm > 0, col_norm, 1.0)
            Phi_norm = Phi / col_norm

            # Start with bias-only
            bias0 = float(np.mean(y)) if n > 0 else 0.0
            res = y - bias0
            selected = []
            best_mse = self._mse(y, np.full_like(y, bias0))
            best_coef = np.array([bias0], dtype=np.float64)
            best_sel = []

            for _ in range(max_terms):
                if k == 0:
                    break
                # Correlation with residual
                corr = np.abs(Phi_norm.T @ res)
                if selected:
                    corr[np.array(selected, dtype=int)] = -1.0
                j = int(np.argmax(corr))
                if corr[j] <= 0:
                    break
                selected.append(j)

                A = np.column_stack([np.ones_like(y), Phi[:, selected]])
                coef, _, _, _ = np.linalg.lstsq(A, y, rcond=None)
                yhat = A @ coef
                mse = self._mse(y, yhat)

                if best_mse - mse > min_improve:
                    best_mse = mse
                    best_coef = coef
                    best_sel = list(selected)
                    res = y - yhat
                else:
                    selected.pop()
                    break

            if best_sel:
                expr_omp = self._build_expression(
                    bias=float(best_coef[0]),
                    coefs=best_coef[1:],
                    exprs=[exprs[j] for j in best_sel],
                )
                A_best = np.column_stack([np.ones_like(y), Phi[:, best_sel]])
                yhat_omp = A_best @ best_coef
                mse_omp = self._mse(y, yhat_omp)
            else:
                expr_omp = self._fmt(bias0)
                yhat_omp = np.full_like(y, bias0)
                mse_omp = best_mse

            # Quadratic baseline (for fallback)
            A_quad = np.column_stack([x1, x2, x1_2, x2_2, x1 * x2, np.ones_like(x1)])
            coef_quad, _, _, _ = np.linalg.lstsq(A_quad, y, rcond=None)
            yhat_quad = A_quad @ coef_quad
            mse_quad = self._mse(y, yhat_quad)
            expr_quad = self._build_expression(
                bias=coef_quad[-1],
                coefs=coef_quad[:-1],
                exprs=["x1", "x2", "x1**2", "x2**2", "x1*x2"],
            )

            candidates = [
                (mse_peaks_fixed, expr_peaks_fixed, yhat_peaks_fixed),
                (mse_peaks_fit, expr_peaks_fit, yhat_peaks_fit),
                (mse_omp, expr_omp, yhat_omp),
                (mse_quad, expr_quad, yhat_quad),
                (mse_lin, self._build_expression(coef_lin[2], coef_lin[:2], ["x1", "x2"]), yhat_lin),
            ]

            # Choose best by MSE, then shorter expression
            candidates.sort(key=lambda t: (t[0], len(t[1])))
            best_mse, best_expr, best_pred = candidates[0]

            best_pred = np.where(np.isfinite(best_pred), best_pred, 0.0)

        return {
            "expression": best_expr,
            "predictions": best_pred.tolist(),
            "details": {"mse": float(best_mse)},
        }