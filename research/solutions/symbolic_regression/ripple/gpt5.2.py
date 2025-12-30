import numpy as np
from typing import List, Tuple, Dict, Any, Optional


class Solution:
    def __init__(self, **kwargs):
        self.kwargs = kwargs

    @staticmethod
    def _safe_lstsq(A: np.ndarray, y: np.ndarray) -> np.ndarray:
        try:
            coef, _, _, _ = np.linalg.lstsq(A, y, rcond=None)
            return coef
        except np.linalg.LinAlgError:
            # Ridge fallback
            alpha = 1e-10
            AtA = A.T @ A
            Aty = A.T @ y
            AtA.flat[:: AtA.shape[0] + 1] += alpha
            try:
                return np.linalg.solve(AtA, Aty)
            except np.linalg.LinAlgError:
                return np.linalg.pinv(AtA) @ Aty

    @staticmethod
    def _fit_scaled(features: List[np.ndarray], y: np.ndarray) -> Tuple[np.ndarray, np.ndarray, float]:
        A = np.column_stack(features)
        n, m = A.shape
        scale = np.ones(m, dtype=np.float64)
        for j in range(m):
            if j == 0:
                scale[j] = 1.0
            else:
                s = np.std(A[:, j])
                if not np.isfinite(s) or s < 1e-14:
                    s = 1.0
                scale[j] = s

        As = A / scale
        coef_s = Solution._safe_lstsq(As, y)
        coef = coef_s / scale
        pred = A @ coef
        resid = pred - y
        mse = float(np.mean(resid * resid))
        return coef, pred, mse

    @staticmethod
    def _fmt_float(x: float) -> str:
        if not np.isfinite(x):
            return "0.0"
        if abs(x) < 1e-14:
            x = 0.0
        s = f"{float(x):.12g}"
        if s == "-0":
            s = "0"
        return s

    @staticmethod
    def _build_expression(terms: List[str], coef: np.ndarray) -> str:
        parts: List[str] = []
        for c, t in zip(coef.tolist(), terms):
            if not np.isfinite(c) or abs(c) < 1e-12:
                continue
            if t == "1":
                parts.append(Solution._fmt_float(c))
                continue
            if abs(c - 1.0) < 1e-12:
                parts.append(f"({t})")
                continue
            if abs(c + 1.0) < 1e-12:
                parts.append(f"-({t})")
                continue
            parts.append(f"({Solution._fmt_float(c)})*({t})")

        if not parts:
            return "0"
        expr = " + ".join(parts)
        expr = expr.replace("+ -", "- ")
        expr = expr.replace("+-", "-")
        return expr

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        X = np.asarray(X, dtype=np.float64)
        y = np.asarray(y, dtype=np.float64).reshape(-1)
        n = X.shape[0]
        x1 = X[:, 0]
        x2 = X[:, 1]

        # Baseline linear model
        A_lin = np.column_stack([x1, x2, np.ones(n, dtype=np.float64)])
        coef_lin = self._safe_lstsq(A_lin, y)
        pred_lin = A_lin @ coef_lin
        mse_lin = float(np.mean((pred_lin - y) ** 2))
        expr_lin = (
            f"({self._fmt_float(coef_lin[0])})*x1 + ({self._fmt_float(coef_lin[1])})*x2 + ({self._fmt_float(coef_lin[2])})"
        )

        r2 = x1 * x1 + x2 * x2
        r = np.sqrt(r2)

        R2 = "(x1**2 + x2**2)"
        R = f"({R2}**0.5)"

        # Polynomial-only candidates
        best = {
            "criterion": float("inf"),
            "mse": float("inf"),
            "terms": ["1"],
            "coef": np.array([float(np.mean(y))], dtype=np.float64),
            "pred": np.full(n, float(np.mean(y)), dtype=np.float64),
        }

        for deg in (1, 2, 3, 4):
            feats = [np.ones(n, dtype=np.float64)]
            terms = ["1"]
            p = r2.copy()
            for d in range(1, deg + 1):
                if d == 1:
                    terms.append(f"({R2})")
                    feats.append(r2)
                else:
                    terms.append(f"({R2}**{d})")
                    feats.append(p * r2 if d > 1 else r2)
                if d >= 1:
                    p = feats[-1]
            coef, pred, mse = self._fit_scaled(feats, y)
            # small complexity penalty
            crit = mse * (1.0 + 0.0008 * (len(terms) ** 2))
            if crit < best["criterion"]:
                best.update(criterion=crit, mse=mse, terms=terms, coef=coef, pred=pred)

        # Stage 1: select promising (argtype, k) via simple trig model
        kmax = 80
        k_list = list(range(1, kmax + 1))
        combos: List[Tuple[float, str]] = []

        def simple_trig_scores(u: np.ndarray) -> List[Tuple[float, int]]:
            scores = []
            ones = np.ones(n, dtype=np.float64)
            for k in k_list:
                su = np.sin(k * u)
                cu = np.cos(k * u)
                coef, pred, mse = self._fit_scaled([ones, su, cu], y)
                scores.append((mse, k))
            scores.sort(key=lambda t: t[0])
            return scores

        top_u_r2 = simple_trig_scores(r2)[:6]
        top_u_r = simple_trig_scores(r)[:6]

        combos.extend([(float(k), "r2") for _, k in top_u_r2])
        combos.extend([(float(k), "r") for _, k in top_u_r])

        # Deduplicate combos
        combos_unique = []
        seen = set()
        for k, a in combos:
            key = (a, int(round(k)))
            if key in seen:
                continue
            seen.add(key)
            combos_unique.append((float(int(round(k))), a))

        # Stage 2: fit richer models for each combo
        configs = [
            (1, 1, False),
            (2, 1, False),
            (3, 1, False),
            (2, 2, False),
            (3, 2, False),
            (2, 1, True),
            (3, 1, True),
        ]

        ones = np.ones(n, dtype=np.float64)
        denom = 1.0 + r2

        for k, argtype in combos_unique:
            k_int = int(round(k))
            if argtype == "r2":
                u = r2
                Uexpr = f"({R2})"
            else:
                u = r
                Uexpr = f"({R})"

            su = np.sin(k_int * u)
            cu = np.cos(k_int * u)

            for deg_poly, deg_trig, include_damped in configs:
                feats: List[np.ndarray] = [ones]
                terms: List[str] = ["1"]

                # Polynomial in r2 (amplitude modulation)
                if deg_poly >= 1:
                    feats.append(r2)
                    terms.append(f"({R2})")
                if deg_poly >= 2:
                    feats.append(r2 * r2)
                    terms.append(f"({R2}**2)")
                if deg_poly >= 3:
                    feats.append(r2 * r2 * r2)
                    terms.append(f"({R2}**3)")

                # Trig terms: r2^d * sin(k*u), r2^d * cos(k*u)
                sin_expr = f"sin({k_int}*{Uexpr})"
                cos_expr = f"cos({k_int}*{Uexpr})"

                for d in range(0, deg_trig + 1):
                    if d == 0:
                        feats.append(su)
                        terms.append(sin_expr)
                        feats.append(cu)
                        terms.append(cos_expr)
                    elif d == 1:
                        feats.append(r2 * su)
                        terms.append(f"({R2})*({sin_expr})")
                        feats.append(r2 * cu)
                        terms.append(f"({R2})*({cos_expr})")
                    elif d == 2:
                        r2_2 = r2 * r2
                        feats.append(r2_2 * su)
                        terms.append(f"({R2}**2)*({sin_expr})")
                        feats.append(r2_2 * cu)
                        terms.append(f"({R2}**2)*({cos_expr})")

                if include_damped:
                    denom_expr = f"(1+{R2})"
                    feats.append(su / denom)
                    terms.append(f"({sin_expr})/({denom_expr})")
                    feats.append(cu / denom)
                    terms.append(f"({cos_expr})/({denom_expr})")
                    feats.append((r2 * su) / denom)
                    terms.append(f"(({R2})*({sin_expr}))/({denom_expr})")

                coef, pred, mse = self._fit_scaled(feats, y)

                # Prune tiny coefficients and refit
                abscoef = np.abs(coef)
                maxc = float(abscoef.max()) if abscoef.size else 0.0
                keep = abscoef > max(1e-10, 1e-6 * maxc)
                if keep.size:
                    keep[0] = True  # keep intercept
                if keep.sum() < len(keep):
                    feats2 = [f for f, kf in zip(feats, keep.tolist()) if kf]
                    terms2 = [t for t, kf in zip(terms, keep.tolist()) if kf]
                    coef2, pred2, mse2 = self._fit_scaled(feats2, y)
                    coef, pred, mse = coef2, pred2, mse2
                    feats, terms = feats2, terms2

                crit = mse * (1.0 + 0.0008 * (len(terms) ** 2))
                if crit < best["criterion"]:
                    best.update(criterion=crit, mse=mse, terms=terms, coef=coef, pred=pred)

        # If nothing beats linear baseline, return baseline
        if not np.isfinite(best["mse"]) or best["mse"] > mse_lin * 0.999:
            return {
                "expression": expr_lin,
                "predictions": pred_lin.tolist(),
                "details": {"mse": mse_lin, "n_terms": 3},
            }

        expression = self._build_expression(best["terms"], best["coef"])
        return {
            "expression": expression,
            "predictions": best["pred"].tolist(),
            "details": {"mse": best["mse"], "n_terms": int(len(best["terms"]))},
        }