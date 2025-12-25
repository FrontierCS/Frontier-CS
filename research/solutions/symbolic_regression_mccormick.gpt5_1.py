import numpy as np

class Solution:
    def __init__(self, **kwargs):
        self.r2_threshold = kwargs.get("r2_threshold", 0.98)
        self.zero_tol = kwargs.get("zero_tol", 1e-12)
        self.max_fallback_terms = kwargs.get("max_fallback_terms", 8)

    def _fit_ols(self, A, y):
        coefs, _, _, _ = np.linalg.lstsq(A, y, rcond=None)
        preds = A @ coefs
        return coefs, preds

    def _r2(self, y, y_pred):
        resid = y - y_pred
        sse = np.sum(resid ** 2)
        sst = np.sum((y - np.mean(y)) ** 2)
        if sst <= 0:
            return 1.0 if sse <= 0 else 0.0
        return 1.0 - sse / sst

    def _build_expression(self, coefs, names):
        expr = None
        for c, n in zip(coefs, names):
            if abs(c) < self.zero_tol:
                continue
            if n == "1":
                term = f"{abs(c):.12g}"
            else:
                term = f"{abs(c):.12g}*{n}"
            if expr is None:
                if n == "1":
                    expr = f"{c:.12g}"
                else:
                    expr = f"{c:.12g}*{n}"
            else:
                sign = "-" if c < 0 else "+"
                expr += f" {sign} {term}"
        if expr is None:
            expr = "0"
        return expr

    def _fallback_model(self, x1, x2, y):
        # Extended feature set for robustness
        feats = [
            ("1", lambda a, b: np.ones_like(a)),
            ("x1", lambda a, b: a),
            ("x2", lambda a, b: b),
            ("x1**2", lambda a, b: a**2),
            ("x2**2", lambda a, b: b**2),
            ("x1*x2", lambda a, b: a*b),
            ("sin(x1 + x2)", lambda a, b: np.sin(a + b)),
            ("sin(x1)", lambda a, b: np.sin(a)),
            ("sin(x2)", lambda a, b: np.sin(b)),
            ("cos(x1)", lambda a, b: np.cos(a)),
            ("cos(x2)", lambda a, b: np.cos(b)),
            ("cos(x1 + x2)", lambda a, b: np.cos(a + b)),
            ("sin(x1 - x2)", lambda a, b: np.sin(a - b)),
            ("cos(x1 - x2)", lambda a, b: np.cos(a - b)),
        ]
        names = [n for n, _ in feats]
        A = np.column_stack([f(x1, x2) for _, f in feats]).astype(float)
        # Ridge-like small regularization to stabilize
        AtA = A.T @ A
        alpha = 1e-8
        AtA[np.diag_indices_from(AtA)] += alpha
        Aty = A.T @ y
        coefs = np.linalg.solve(AtA, Aty)
        preds = A @ coefs

        # Feature selection by contribution magnitude
        effects = []
        pred_rms = np.sqrt(np.mean(preds**2)) + 1e-20
        for j in range(A.shape[1]):
            eff_rms = np.sqrt(np.mean((coefs[j] * A[:, j])**2))
            effects.append(eff_rms)
        idx_sorted = np.argsort(effects)[::-1]

        keep = []
        for idx in idx_sorted:
            if len(keep) >= self.max_fallback_terms:
                break
            if effects[idx] < 1e-12 * pred_rms:
                continue
            keep.append(idx)

        # Ensure constant is included if helpful
        const_idx = names.index("1")
        if const_idx not in keep and abs(coefs[const_idx]) > 1e-10:
            if len(keep) >= self.max_fallback_terms:
                keep[-1] = const_idx
            else:
                keep.append(const_idx)

        keep = sorted(set(keep))
        A_sel = A[:, keep]
        coefs_sel, preds_sel = self._fit_ols(A_sel, y)
        names_sel = [names[i] for i in keep]

        # Build expression
        expr = self._build_expression(coefs_sel, names_sel)
        return expr, preds_sel

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        X = np.asarray(X, dtype=float)
        y = np.asarray(y, dtype=float).ravel()
        x1 = X[:, 0]
        x2 = X[:, 1]

        # Primary: McCormick-structured model
        names5 = ["sin(x1 + x2)", "(x1 - x2)**2", "x1", "x2", "1"]
        A5 = np.column_stack([
            np.sin(x1 + x2),
            (x1 - x2) ** 2,
            x1,
            x2,
            np.ones_like(x1),
        ])
        coefs5, preds5 = self._fit_ols(A5, y)
        r2_5 = self._r2(y, preds5)

        if r2_5 >= self.r2_threshold:
            expr = self._build_expression(coefs5, names5)
            return {
                "expression": expr,
                "predictions": preds5.tolist(),
                "details": {}
            }

        # Fallback to broader basis
        expr_fb, preds_fb = self._fallback_model(x1, x2, y)
        return {
            "expression": expr_fb,
            "predictions": preds_fb.tolist(),
            "details": {}
        }
