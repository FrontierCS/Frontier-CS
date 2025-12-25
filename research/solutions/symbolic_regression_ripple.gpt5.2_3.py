import numpy as np
import sympy as sp


class Solution:
    def __init__(self, **kwargs):
        self.random_state = kwargs.get("random_state", 42)

    @staticmethod
    def _safe_quantile_scale(r: np.ndarray) -> float:
        r = np.asarray(r, dtype=np.float64)
        if r.size == 0:
            return 1.0
        q = float(np.quantile(r, 0.95))
        mx = float(np.max(r))
        scale = q if np.isfinite(q) and q > 0 else (mx if np.isfinite(mx) and mx > 0 else 1.0)
        if not np.isfinite(scale) or scale <= 0:
            scale = 1.0
        return scale

    @staticmethod
    def _fit_lstsq(A: np.ndarray, y: np.ndarray):
        try:
            coef, _, _, _ = np.linalg.lstsq(A, y, rcond=None)
            pred = A @ coef
            resid = y - pred
            mse = float(np.mean(resid * resid))
            if not np.isfinite(mse):
                return None
            return coef, pred, mse
        except Exception:
            return None

    @staticmethod
    def _build_design(rs: np.ndarray, t: np.ndarray, k: float, deg_dc: int, deg_sin: int, deg_cos: int):
        n = rs.shape[0]
        cols = []
        meta = []
        if deg_dc >= 0:
            for p in range(deg_dc + 1):
                if p == 0:
                    v = np.ones(n, dtype=np.float64)
                elif p == 1:
                    v = rs
                else:
                    v = rs ** p
                cols.append(v)
                meta.append(("dc", p))
        if deg_sin >= 0 or deg_cos >= 0:
            arg = k * t
            sinv = np.sin(arg) if deg_sin >= 0 else None
            cosv = np.cos(arg) if deg_cos >= 0 else None
            if deg_sin >= 0:
                for p in range(deg_sin + 1):
                    if p == 0:
                        v = sinv
                    elif p == 1:
                        v = rs * sinv
                    else:
                        v = (rs ** p) * sinv
                    cols.append(v)
                    meta.append(("sin", p))
            if deg_cos >= 0:
                for p in range(deg_cos + 1):
                    if p == 0:
                        v = cosv
                    elif p == 1:
                        v = rs * cosv
                    else:
                        v = (rs ** p) * cosv
                    cols.append(v)
                    meta.append(("cos", p))
        if not cols:
            A = np.zeros((n, 1), dtype=np.float64)
            meta = [("dc", 0)]
        else:
            A = np.column_stack(cols).astype(np.float64, copy=False)
        return A, meta

    @staticmethod
    def _group_coeffs(coef: np.ndarray, meta):
        groups = {"dc": {}, "sin": {}, "cos": {}}
        for c, (g, p) in zip(coef, meta):
            groups[g][p] = float(c)
        def to_list(dct):
            if not dct:
                return []
            mxp = max(dct.keys())
            out = [0.0] * (mxp + 1)
            for p, v in dct.items():
                out[p] = float(v)
            return out
        return {
            "dc": to_list(groups["dc"]),
            "sin": to_list(groups["sin"]),
            "cos": to_list(groups["cos"]),
        }

    @staticmethod
    def _trim_coeffs(coeffs, thr_abs):
        c = [float(v) for v in coeffs]
        if not c:
            return []
        c = [0.0 if abs(v) < thr_abs else float(v) for v in c]
        while len(c) > 0 and abs(c[-1]) < thr_abs:
            c.pop()
        if len(c) == 0:
            return []
        return c

    @staticmethod
    def _poly_eval(coeffs, x):
        if not coeffs:
            return 0.0
        coeffs = np.asarray(coeffs, dtype=np.float64)
        y = np.zeros_like(x, dtype=np.float64)
        xp = np.ones_like(x, dtype=np.float64)
        for a in coeffs:
            y += a * xp
            xp *= x
        return y

    @staticmethod
    def _format_float(v: float) -> str:
        if not np.isfinite(v):
            return "0.0"
        if v == 0.0:
            return "0.0"
        s = f"{v:.16g}"
        return s

    @classmethod
    def _poly_to_str(cls, coeffs, var_expr: str) -> str:
        if not coeffs:
            return "0.0"
        terms = []
        for p, c in enumerate(coeffs):
            if c == 0.0:
                continue
            cs = cls._format_float(c)
            if p == 0:
                terms.append(f"({cs})")
            elif p == 1:
                terms.append(f"({cs})*({var_expr})")
            else:
                terms.append(f"({cs})*(({var_expr})**{p})")
        if not terms:
            return "0.0"
        return " + ".join(terms)

    @staticmethod
    def _complexity(expr_str: str) -> int:
        sin, cos, exp, log = sp.sin, sp.cos, sp.exp, sp.log
        try:
            e = sp.sympify(expr_str, locals={"sin": sin, "cos": cos, "exp": exp, "log": log})
        except Exception:
            return 10**9

        unary = 0
        binary = 0

        def rec(node):
            nonlocal unary, binary
            if isinstance(node, sp.Function):
                if node.func in (sp.sin, sp.cos, sp.exp, sp.log):
                    unary += 1
            if isinstance(node, sp.Add) or isinstance(node, sp.Mul):
                n = len(node.args)
                if n > 1:
                    binary += (n - 1)
            elif isinstance(node, sp.Pow):
                binary += 1
            for a in getattr(node, "args", ()):
                rec(a)

        rec(e)
        return int(2 * binary + unary)

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        X = np.asarray(X, dtype=np.float64)
        y = np.asarray(y, dtype=np.float64).reshape(-1)
        n = X.shape[0]
        if n == 0:
            return {"expression": "0.0", "predictions": [], "details": {"complexity": 0}}

        x1 = X[:, 0]
        x2 = X[:, 1]
        r = x1 * x1 + x2 * x2
        scale = self._safe_quantile_scale(r)
        rs = r / scale

        t_options = [
            ("r", rs),
            ("sqrt_r", np.sqrt(np.maximum(rs, 0.0))),
        ]

        # Initial coarse search for k using full model
        k_grid = np.unique(
            np.concatenate(
                [
                    np.linspace(1.0, 50.0, 50),
                    np.linspace(52.0, 150.0, 50),
                ]
            )
        )

        best = None  # (mse, tkind, k, deg_dc, deg_sin, deg_cos, coef, meta)
        for tkind, t in t_options:
            for k in k_grid:
                A, meta = self._build_design(rs, t, float(k), 2, 2, 2)
                fit = self._fit_lstsq(A, y)
                if fit is None:
                    continue
                coef, pred, mse = fit
                if best is None or mse < best[0]:
                    best = (mse, tkind, float(k), 2, 2, 2, coef, meta)

        if best is None:
            # Fallback to linear regression on x1, x2, 1
            A = np.column_stack([x1, x2, np.ones_like(x1)])
            fit = self._fit_lstsq(A, y)
            if fit is None:
                expr = "0.0"
                preds = np.zeros_like(y)
            else:
                coef, preds, _ = fit
                a, b, c = [float(v) for v in coef]
                expr = f"({self._format_float(a)})*x1 + ({self._format_float(b)})*x2 + ({self._format_float(c)})"
            return {"expression": expr, "predictions": preds.tolist(), "details": {"complexity": self._complexity(expr)}}

        # Refine k near best
        _, best_tkind, best_k, _, _, _, _, _ = best
        best_t = rs if best_tkind == "r" else np.sqrt(np.maximum(rs, 0.0))
        dk = 5.0
        k_ref = np.linspace(max(0.2, best_k - dk), best_k + dk, 81)
        for k in k_ref:
            A, meta = self._build_design(rs, best_t, float(k), 2, 2, 2)
            fit = self._fit_lstsq(A, y)
            if fit is None:
                continue
            coef, pred, mse = fit
            if mse < best[0]:
                best = (mse, best_tkind, float(k), 2, 2, 2, coef, meta)

        # Explore simpler variants around refined k
        configs = [
            (2, 2, 2),
            (2, 2, -1),
            (2, -1, 2),
            (2, 1, 1),
            (1, 1, 1),
            (0, 1, 1),
            (2, 2, 0),
            (2, 0, 2),
            (2, -1, -1),
        ]

        local_k = np.linspace(max(0.2, best[2] - 2.0), best[2] + 2.0, 31)
        for deg_dc, deg_sin, deg_cos in configs:
            for k in local_k:
                A, meta = self._build_design(rs, best_t, float(k), deg_dc, deg_sin, deg_cos)
                fit = self._fit_lstsq(A, y)
                if fit is None:
                    continue
                coef, pred, mse = fit
                if mse < best[0]:
                    best = (mse, best_tkind, float(k), deg_dc, deg_sin, deg_cos, coef, meta)

        # Build final model groups
        mse, tkind, k_scaled, deg_dc, deg_sin, deg_cos, coef, meta = best
        groups_scaled = self._group_coeffs(coef, meta)

        # Convert to unscaled r-variable model for output (reduces repeated scaling ops)
        # poly(rs) where rs = r/scale  => coeff_r[i] = coeff_rs[i] / scale**i
        def unscale_coeffs(coeffs_rs):
            return [float(a) / (scale ** i) for i, a in enumerate(coeffs_rs)] if coeffs_rs else []

        dc_r = unscale_coeffs(groups_scaled["dc"])
        sin_r = unscale_coeffs(groups_scaled["sin"])
        cos_r = unscale_coeffs(groups_scaled["cos"])

        if tkind == "r":
            k_out = k_scaled / scale
            t_out = r
            t_expr = "(x1**2 + x2**2)"
        else:
            k_out = k_scaled / (scale ** 0.5)
            t_out = np.sqrt(np.maximum(r, 0.0))
            t_expr = "((x1**2 + x2**2))**0.5"

        # Candidate pruning/degree reduction by thresholding and refitting
        thresholds = [0.0, 1e-12, 1e-10, 1e-8, 1e-7, 1e-6, 1e-5, 1e-4]
        best_expr = None  # (objective, mse, expr_str, preds, complexity, cfg, k_scaled, tkind)
        y_scale = float(np.std(y)) if np.isfinite(np.std(y)) and np.std(y) > 0 else float(np.max(np.abs(y)) + 1.0)
        if not np.isfinite(y_scale) or y_scale <= 0:
            y_scale = 1.0

        for thr in thresholds:
            thr_abs = thr * y_scale
            dc_t = self._trim_coeffs(dc_r, thr_abs)
            sin_t = self._trim_coeffs(sin_r, thr_abs)
            cos_t = self._trim_coeffs(cos_r, thr_abs)

            # Determine degrees for refit on scaled variable with trimmed degrees
            deg_dc2 = len(dc_t) - 1 if dc_t else -1
            deg_sin2 = len(sin_t) - 1 if sin_t else -1
            deg_cos2 = len(cos_t) - 1 if cos_t else -1
            if deg_dc2 < 0 and deg_sin2 < 0 and deg_cos2 < 0:
                deg_dc2 = 0

            t_for_fit = rs if tkind == "r" else np.sqrt(np.maximum(rs, 0.0))
            A, meta2 = self._build_design(rs, t_for_fit, float(k_scaled), deg_dc2, deg_sin2, deg_cos2)
            fit2 = self._fit_lstsq(A, y)
            if fit2 is None:
                continue
            coef2, pred2, mse2 = fit2
            groups2_scaled = self._group_coeffs(coef2, meta2)

            dc2_r = unscale_coeffs(groups2_scaled["dc"])
            sin2_r = unscale_coeffs(groups2_scaled["sin"])
            cos2_r = unscale_coeffs(groups2_scaled["cos"])

            # Build expression string
            r_expr = "(x1**2 + x2**2)"
            dc_str = self._poly_to_str(dc2_r, r_expr)
            sin_str = self._poly_to_str(sin2_r, r_expr)
            cos_str = self._poly_to_str(cos2_r, r_expr)

            arg_str = f"({self._format_float(float(k_out))})*({t_expr})"
            parts = []
            if dc_str != "0.0":
                parts.append(f"({dc_str})")
            if sin_str != "0.0":
                parts.append(f"({sin_str})*sin({arg_str})")
            if cos_str != "0.0":
                parts.append(f"({cos_str})*cos({arg_str})")
            expr = " + ".join(parts) if parts else "0.0"

            # Numeric predictions consistent with expression
            pred_expr = self._poly_eval(dc2_r, r) if dc2_r else np.zeros_like(y)
            if sin2_r:
                pred_expr = pred_expr + self._poly_eval(sin2_r, r) * np.sin(k_out * t_out)
            if cos2_r:
                pred_expr = pred_expr + self._poly_eval(cos2_r, r) * np.cos(k_out * t_out)
            resid = y - pred_expr
            mse_expr = float(np.mean(resid * resid))
            comp = self._complexity(expr)
            if not np.isfinite(mse_expr) or comp >= 10**8:
                continue
            obj = mse_expr * (1.0 + 0.001 * comp)

            if best_expr is None or obj < best_expr[0]:
                best_expr = (obj, mse_expr, expr, pred_expr, comp, (deg_dc2, deg_sin2, deg_cos2), float(k_scaled), tkind)

        if best_expr is None:
            # Very unlikely fallback
            expr = "0.0"
            preds = np.zeros_like(y)
            return {"expression": expr, "predictions": preds.tolist(), "details": {"complexity": 0}}

        _, final_mse, expression, final_preds, complexity, cfg, k_scaled_final, tkind_final = best_expr

        details = {
            "complexity": int(complexity),
            "mse": float(final_mse),
            "config": {"deg_dc": int(cfg[0]), "deg_sin": int(cfg[1]), "deg_cos": int(cfg[2])},
            "tkind": str(tkind_final),
            "k_scaled": float(k_scaled_final),
        }

        return {
            "expression": expression,
            "predictions": final_preds.tolist(),
            "details": details,
        }