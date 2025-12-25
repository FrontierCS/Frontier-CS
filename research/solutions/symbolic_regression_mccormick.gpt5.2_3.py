import numpy as np

class Solution:
    def __init__(self, **kwargs):
        self.kwargs = kwargs

    @staticmethod
    def _snap_float(v: float, tol: float = 1e-8) -> float:
        if not np.isfinite(v):
            return float(v)
        snap = [
            -5.0, -4.0, -3.0, -2.5, -2.0, -1.5, -1.0, -0.5,
            0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 4.0, 5.0
        ]
        for s in snap:
            if abs(v - s) <= tol * max(1.0, abs(s)):
                return float(s)
        if abs(v) <= tol:
            return 0.0
        return float(v)

    @staticmethod
    def _fmt_float(v: float) -> str:
        if not np.isfinite(v):
            if np.isnan(v):
                return "0.0"
            return "1e308" if v > 0 else "-1e308"
        v = float(v)
        if v == 0.0:
            return "0"
        s = format(v, ".12g")
        if "e" in s or "E" in s:
            s = format(v, ".16g")
        return s

    @staticmethod
    def _build_expression(coeffs, term_strs, coef_tol=1e-10) -> str:
        parts = []
        for c, t in zip(coeffs, term_strs):
            c = float(c)
            if t is None:
                continue
            if abs(c) <= coef_tol:
                continue
            c = Solution._snap_float(c, tol=1e-8)
            if abs(c - 1.0) <= 1e-12:
                parts.append(f"{t}")
            elif abs(c + 1.0) <= 1e-12:
                parts.append(f"-({t})")
            else:
                parts.append(f"{Solution._fmt_float(c)}*({t})")

        c0 = float(coeffs[-1])
        if abs(c0) > coef_tol:
            c0 = Solution._snap_float(c0, tol=1e-8)
            parts.append(Solution._fmt_float(c0))

        if not parts:
            return "0"

        expr = " + ".join(parts)
        expr = expr.replace("+ -", "- ")
        return expr

    @staticmethod
    def _lstsq_fit(F: np.ndarray, y: np.ndarray):
        coeffs, _, _, _ = np.linalg.lstsq(F, y, rcond=None)
        pred = F @ coeffs
        mse = float(np.mean((y - pred) ** 2))
        return coeffs, pred, mse

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        X = np.asarray(X, dtype=np.float64)
        y = np.asarray(y, dtype=np.float64).reshape(-1)
        n = X.shape[0]
        if n == 0:
            return {"expression": "0", "predictions": [], "details": {}}

        x1 = X[:, 0]
        x2 = X[:, 1]
        ones = np.ones_like(x1)

        # Primary hypothesis: McCormick function form
        t1 = np.sin(x1 + x2)
        t2 = (x1 - x2) ** 2
        F = np.column_stack([t1, t2, x1, x2, ones])
        coeffs, pred, mse = self._lstsq_fit(F, y)

        yvar = float(np.var(y)) if n > 1 else float(np.mean(y * y))
        tol_mse = 1e-12 + 1e-10 * max(1.0, yvar)

        if not np.isfinite(mse) or mse > tol_mse:
            # Fallback: small sparse greedy selection over a modest library (no PySR dependency)
            # Always include constant term; select up to max_terms additional terms.
            lib = [
                (np.sin(x1 + x2), "sin(x1 + x2)"),
                (np.cos(x1 + x2), "cos(x1 + x2)"),
                (np.sin(x1), "sin(x1)"),
                (np.cos(x1), "cos(x1)"),
                (np.sin(x2), "sin(x2)"),
                (np.cos(x2), "cos(x2)"),
                (x1, "x1"),
                (x2, "x2"),
                (x1 + x2, "(x1 + x2)"),
                (x1 - x2, "(x1 - x2)"),
                (x1 * x2, "(x1*x2)"),
                (x1 ** 2, "(x1**2)"),
                (x2 ** 2, "(x2**2)"),
                ((x1 - x2) ** 2, "(x1 - x2)**2"),
                ((x1 + x2) ** 2, "(x1 + x2)**2"),
            ]

            # Normalize features for selection
            Z = []
            Zstr = []
            for v, s in lib:
                v = np.asarray(v, dtype=np.float64)
                m = float(np.mean(v))
                vc = v - m
                sd = float(np.std(vc))
                if sd < 1e-12:
                    continue
                Z.append(vc / sd)
                Zstr.append(s)
            if not Z:
                expression = Solution._fmt_float(float(np.mean(y)))
                return {"expression": expression, "predictions": [float(np.mean(y))] * n, "details": {}}

            Z = np.column_stack(Z)

            selected = []
            selected_str = []
            r = y - np.mean(y)

            max_terms = 6
            best = None  # (mse, coeffs, pred, term_strs)
            for _ in range(max_terms):
                # Choose best correlated with residual
                corr = Z.T @ r
                idx = int(np.argmax(np.abs(corr)))
                if idx in selected:
                    break
                selected.append(idx)
                selected_str.append(Zstr[idx])

                # Fit with selected raw (un-normalized) features + constant
                feats = []
                feat_strs = []
                for j in selected:
                    feats.append(lib[[k for k, s in enumerate([ss for _, ss in lib])].index(Zstr[j])][0] if False else None)  # placeholder

                # Recover raw feature vectors by recomputing from strings list mapping
                raw_map = {s: v for (v, s) in lib}
                raw_feats = [raw_map[s] for s in selected_str]

                Fsel = np.column_stack(raw_feats + [ones])
                csel, psel, msel = self._lstsq_fit(Fsel, y)

                # BIC-like criterion to avoid excessive terms
                p = len(raw_feats) + 1
                msel_clip = max(msel, 1e-18)
                bic = n * np.log(msel_clip) + p * np.log(max(n, 2))

                if best is None:
                    best = (bic, msel, csel, psel, selected_str)
                else:
                    if bic < best[0]:
                        best = (bic, msel, csel, psel, selected_str)

                # Update residual
                r = y - psel
                if msel <= tol_mse:
                    break

            if best is not None:
                _, mse, csel, psel, tstrs = best
                # Build expression from selected features + constant
                term_strs = list(tstrs) + [None]
                coeffs = np.concatenate([csel[:-1], [csel[-1]]])
                pred = psel

                # Snap and simplify multiplications by 1/-1 etc
                coeffs = np.array([self._snap_float(float(v), tol=1e-8) for v in coeffs], dtype=np.float64)
                expression = self._build_expression(coeffs, term_strs, coef_tol=1e-10)

                return {
                    "expression": expression,
                    "predictions": pred.tolist(),
                    "details": {}
                }

        # Base McCormick form expression
        term_strs = ["sin(x1 + x2)", "(x1 - x2)**2", "x1", "x2", None]
        coeffs = np.array([self._snap_float(float(v), tol=1e-8) for v in coeffs], dtype=np.float64)
        expression = self._build_expression(coeffs, term_strs, coef_tol=1e-10)

        return {
            "expression": expression,
            "predictions": pred.tolist(),
            "details": {}
        }