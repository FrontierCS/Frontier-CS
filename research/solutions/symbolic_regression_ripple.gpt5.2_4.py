import numpy as np

class Solution:
    def __init__(self, **kwargs):
        self.random_state = int(kwargs.get("random_state", 42))
        self.max_w_grid = int(kwargs.get("max_w_grid", 120))
        self.refine_w_grid = int(kwargs.get("refine_w_grid", 80))
        self.degree_trig = int(kwargs.get("degree_trig", 2))
        self.degree_poly = int(kwargs.get("degree_poly", 3))

    @staticmethod
    def _fmt(c: float) -> str:
        if np.isnan(c) or np.isinf(c):
            return "0.0"
        if abs(c) < 1e-18:
            c = 0.0
        s = format(float(c), ".16g")
        if s == "-0":
            s = "0"
        return s

    @staticmethod
    def _poly_powers(t: np.ndarray, degree: int):
        polys = [np.ones_like(t)]
        if degree >= 1:
            polys.append(t)
        for k in range(2, degree + 1):
            polys.append(polys[-1] * t)
        return polys

    @staticmethod
    def _safe_lstsq(A: np.ndarray, y: np.ndarray):
        try:
            coef, _, _, _ = np.linalg.lstsq(A, y, rcond=None)
            return coef
        except Exception:
            try:
                ATA = A.T @ A
                ATy = A.T @ y
                coef = np.linalg.solve(ATA + 1e-12 * np.eye(ATA.shape[0]), ATy)
                return coef
            except Exception:
                return None

    @staticmethod
    def _mse(yhat: np.ndarray, y: np.ndarray) -> float:
        d = yhat - y
        return float(np.mean(d * d))

    def _w_candidates(self, t: np.ndarray, n: int):
        t_abs = np.abs(t)
        t_max = float(np.percentile(t_abs[np.isfinite(t_abs)], 99.5)) if np.any(np.isfinite(t_abs)) else 1.0
        if not np.isfinite(t_max) or t_max <= 1e-12:
            t_max = 1.0
        w_max = min(80.0, max(4.0, 120.0 / t_max))
        w_min = max(0.05, 0.5 / t_max)
        if w_max <= w_min:
            w_max = w_min + 1.0
        return np.linspace(w_min, w_max, n, dtype=float)

    def _fit_poly(self, t: np.ndarray, y: np.ndarray, degree: int):
        polys = self._poly_powers(t, degree)
        A = np.column_stack(polys)
        coef = self._safe_lstsq(A, y)
        if coef is None:
            return None
        yhat = A @ coef
        mse = self._mse(yhat, y)
        return {"kind": "poly", "degree": degree, "coef": coef, "mse": mse, "t": "t"}

    def _fit_trig(self, t: np.ndarray, y: np.ndarray, degree: int, variant: str, w_grid: np.ndarray):
        polys = self._poly_powers(t, degree)
        n = t.shape[0]
        p = degree + 1

        best = None
        for w in w_grid:
            if not np.isfinite(w) or w <= 0:
                continue
            arg = w * t
            s = np.sin(arg)
            c = np.cos(arg)

            if variant == "sincos":
                A = np.empty((n, 3 * p), dtype=float)
                col = 0
                for k in range(p):
                    A[:, col] = polys[k] * s
                    col += 1
                for k in range(p):
                    A[:, col] = polys[k] * c
                    col += 1
                for k in range(p):
                    A[:, col] = polys[k]
                    col += 1
            elif variant == "sin":
                A = np.empty((n, 2 * p), dtype=float)
                col = 0
                for k in range(p):
                    A[:, col] = polys[k] * s
                    col += 1
                for k in range(p):
                    A[:, col] = polys[k]
                    col += 1
            elif variant == "cos":
                A = np.empty((n, 2 * p), dtype=float)
                col = 0
                for k in range(p):
                    A[:, col] = polys[k] * c
                    col += 1
                for k in range(p):
                    A[:, col] = polys[k]
                    col += 1
            else:
                continue

            coef = self._safe_lstsq(A, y)
            if coef is None:
                continue
            yhat = A @ coef
            mse = self._mse(yhat, y)

            if (best is None) or (mse < best["mse"]):
                best = {"kind": "trig", "variant": variant, "degree": degree, "w": float(w), "coef": coef, "mse": mse}

        if best is None:
            return None

        w0 = best["w"]
        w_coarse = w_grid
        step = float(np.median(np.diff(w_coarse))) if w_coarse.size >= 2 else max(0.1, w0 * 0.05)
        span = max(5.0 * step, 0.1 * w0)
        w_min = max(1e-6, w0 - span)
        w_max = w0 + span
        w_ref = np.linspace(w_min, w_max, self.refine_w_grid, dtype=float)

        for w in w_ref:
            if not np.isfinite(w) or w <= 0:
                continue
            arg = w * t
            s = np.sin(arg)
            c = np.cos(arg)

            if variant == "sincos":
                A = np.empty((n, 3 * p), dtype=float)
                col = 0
                for k in range(p):
                    A[:, col] = polys[k] * s
                    col += 1
                for k in range(p):
                    A[:, col] = polys[k] * c
                    col += 1
                for k in range(p):
                    A[:, col] = polys[k]
                    col += 1
            elif variant == "sin":
                A = np.empty((n, 2 * p), dtype=float)
                col = 0
                for k in range(p):
                    A[:, col] = polys[k] * s
                    col += 1
                for k in range(p):
                    A[:, col] = polys[k]
                    col += 1
            elif variant == "cos":
                A = np.empty((n, 2 * p), dtype=float)
                col = 0
                for k in range(p):
                    A[:, col] = polys[k] * c
                    col += 1
                for k in range(p):
                    A[:, col] = polys[k]
                    col += 1
            else:
                break

            coef = self._safe_lstsq(A, y)
            if coef is None:
                continue
            yhat = A @ coef
            mse = self._mse(yhat, y)
            if mse < best["mse"]:
                best = {"kind": "trig", "variant": variant, "degree": degree, "w": float(w), "coef": coef, "mse": mse}

        return best

    @staticmethod
    def _prune_coef(coef: np.ndarray, scale: float):
        thr = 1e-10 * max(1.0, float(scale))
        c = coef.copy()
        c[np.abs(c) < thr] = 0.0
        return c

    def _poly_str(self, coefs: np.ndarray, t_expr: str):
        terms = []
        for k, c in enumerate(coefs):
            if c == 0.0:
                continue
            ac = abs(float(c))
            cs = self._fmt(ac)
            if k == 0:
                term = cs
            elif k == 1:
                term = f"{cs}*({t_expr})"
            else:
                term = f"{cs}*({t_expr})**{k}"
            terms.append((float(c) < 0.0, term))
        if not terms:
            return "0"
        expr = ""
        for i, (is_neg, term) in enumerate(terms):
            if i == 0:
                expr = f"-{term}" if is_neg else term
            else:
                expr += f" - {term}" if is_neg else f" + {term}"
        return expr

    def _build_expression(self, model: dict, t_expr: str, y_scale: float):
        kind = model["kind"]
        if kind == "poly":
            coef = self._prune_coef(np.asarray(model["coef"], dtype=float), y_scale)
            expr = self._poly_str(coef, t_expr)
            return expr, coef, None

        variant = model["variant"]
        degree = int(model["degree"])
        p = degree + 1
        w = float(model["w"])
        w_str = self._fmt(w)

        coef = self._prune_coef(np.asarray(model["coef"], dtype=float), y_scale)

        if variant == "sincos":
            a = coef[:p]
            b = coef[p:2 * p]
            d = coef[2 * p:3 * p]
            poly_s = self._poly_str(a, t_expr)
            poly_c = self._poly_str(b, t_expr)
            poly_p = self._poly_str(d, t_expr)

            parts = []
            if poly_s != "0":
                parts.append(f"({poly_s})*sin(({w_str})*({t_expr}))")
            if poly_c != "0":
                parts.append(f"({poly_c})*cos(({w_str})*({t_expr}))")
            if poly_p != "0":
                parts.append(f"({poly_p})")
            if not parts:
                expr = "0"
            else:
                expr = " + ".join(f"({p_})" for p_ in parts)
            return expr, coef, w

        if variant == "sin":
            a = coef[:p]
            d = coef[p:2 * p]
            poly_s = self._poly_str(a, t_expr)
            poly_p = self._poly_str(d, t_expr)
            parts = []
            if poly_s != "0":
                parts.append(f"({poly_s})*sin(({w_str})*({t_expr}))")
            if poly_p != "0":
                parts.append(f"({poly_p})")
            expr = "0" if not parts else " + ".join(f"({p_})" for p_ in parts)
            return expr, coef, w

        if variant == "cos":
            a = coef[:p]
            d = coef[p:2 * p]
            poly_c = self._poly_str(a, t_expr)
            poly_p = self._poly_str(d, t_expr)
            parts = []
            if poly_c != "0":
                parts.append(f"({poly_c})*cos(({w_str})*({t_expr}))")
            if poly_p != "0":
                parts.append(f"({poly_p})")
            expr = "0" if not parts else " + ".join(f"({p_})" for p_ in parts)
            return expr, coef, w

        return "0", coef, None

    def _predict_from_model(self, model: dict, t: np.ndarray):
        if model["kind"] == "poly":
            coef = np.asarray(model["coef"], dtype=float)
            degree = coef.shape[0] - 1
            polys = self._poly_powers(t, degree)
            A = np.column_stack(polys)
            return A @ coef

        variant = model["variant"]
        degree = int(model["degree"])
        w = float(model["w"])
        coef = np.asarray(model["coef"], dtype=float)
        p = degree + 1
        polys = self._poly_powers(t, degree)
        arg = w * t
        s = np.sin(arg)
        c = np.cos(arg)
        if variant == "sincos":
            a = coef[:p]
            b = coef[p:2 * p]
            d = coef[2 * p:3 * p]
            yhat = np.zeros_like(t, dtype=float)
            for k in range(p):
                yhat += a[k] * polys[k] * s
            for k in range(p):
                yhat += b[k] * polys[k] * c
            for k in range(p):
                yhat += d[k] * polys[k]
            return yhat
        if variant == "sin":
            a = coef[:p]
            d = coef[p:2 * p]
            yhat = np.zeros_like(t, dtype=float)
            for k in range(p):
                yhat += a[k] * polys[k] * s
            for k in range(p):
                yhat += d[k] * polys[k]
            return yhat
        if variant == "cos":
            a = coef[:p]
            d = coef[p:2 * p]
            yhat = np.zeros_like(t, dtype=float)
            for k in range(p):
                yhat += a[k] * polys[k] * c
            for k in range(p):
                yhat += d[k] * polys[k]
            return yhat
        return np.zeros_like(t, dtype=float)

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        X = np.asarray(X)
        y = np.asarray(y).reshape(-1)
        n = X.shape[0]
        if n == 0:
            return {"expression": "0", "predictions": [], "details": {}}

        x1 = X[:, 0].astype(float, copy=False)
        x2 = X[:, 1].astype(float, copy=False)

        r2 = x1 * x1 + x2 * x2
        r = np.sqrt(np.maximum(r2, 0.0))

        mask = np.isfinite(x1) & np.isfinite(x2) & np.isfinite(y) & np.isfinite(r2) & np.isfinite(r)
        if not np.all(mask):
            x1m = x1[mask]
            x2m = x2[mask]
            ym = y[mask]
            r2m = r2[mask]
            rm = r[mask]
        else:
            ym = y
            r2m = r2
            rm = r

        y_scale = float(np.std(ym)) if ym.size else 1.0
        if not np.isfinite(y_scale) or y_scale <= 1e-12:
            y_scale = float(np.max(np.abs(ym))) if ym.size else 1.0
        if not np.isfinite(y_scale) or y_scale <= 1e-12:
            y_scale = 1.0

        candidates = []

        cand_poly_r2 = self._fit_poly(r2m, ym, self.degree_poly)
        if cand_poly_r2 is not None:
            cand_poly_r2["t_expr"] = "(x1**2 + x2**2)"
            cand_poly_r2["t_kind"] = "r2"
            candidates.append(cand_poly_r2)

        cand_poly_r = self._fit_poly(rm, ym, self.degree_poly)
        if cand_poly_r is not None:
            cand_poly_r["t_expr"] = "((x1**2 + x2**2)**0.5)"
            cand_poly_r["t_kind"] = "r"
            candidates.append(cand_poly_r)

        w_grid_r2 = self._w_candidates(r2m, self.max_w_grid)
        w_grid_r = self._w_candidates(rm, self.max_w_grid)

        for variant in ("sincos", "sin", "cos"):
            cand = self._fit_trig(r2m, ym, self.degree_trig, variant, w_grid_r2)
            if cand is not None:
                cand["t_expr"] = "(x1**2 + x2**2)"
                cand["t_kind"] = "r2"
                candidates.append(cand)

            cand = self._fit_trig(rm, ym, self.degree_trig, variant, w_grid_r)
            if cand is not None:
                cand["t_expr"] = "((x1**2 + x2**2)**0.5)"
                cand["t_kind"] = "r"
                candidates.append(cand)

        if not candidates:
            expr = "0"
            preds = np.zeros(n, dtype=float)
            return {"expression": expr, "predictions": preds.tolist(), "details": {"mse": float(np.mean((y - preds) ** 2))}}

        def proxy_complexity(m):
            if m["kind"] == "poly":
                return 1 + int(m.get("degree", 0))
            variant = m.get("variant", "")
            trig_count = 2 if variant == "sincos" else 1
            return 10 * trig_count + 1 + int(m.get("degree", 0))

        best = None
        for m in candidates:
            if best is None:
                best = m
            else:
                if m["mse"] < best["mse"]:
                    best = m
                else:
                    rel = (m["mse"] - best["mse"]) / (abs(best["mse"]) + 1e-12)
                    if rel <= 1e-3 and proxy_complexity(m) < proxy_complexity(best):
                        best = m

        t_expr = best["t_expr"]
        expr, pruned_coef, w_used = self._build_expression(best, t_expr, y_scale)

        if best.get("t_kind") == "r":
            t_all = r
        else:
            t_all = r2

        best2 = dict(best)
        best2["coef"] = pruned_coef
        yhat_all = self._predict_from_model(best2, t_all)

        if not np.all(mask):
            preds = np.full(n, np.nan, dtype=float)
            preds[mask] = yhat_all
            preds[~mask] = np.nan
        else:
            preds = yhat_all

        details = {
            "mse_fit": float(best["mse"]),
            "model_kind": best["kind"],
            "t_kind": best.get("t_kind", ""),
        }
        if best["kind"] == "trig":
            details["variant"] = best.get("variant", "")
            details["w"] = float(best.get("w", 0.0))

        return {
            "expression": expr,
            "predictions": preds.tolist(),
            "details": details,
        }