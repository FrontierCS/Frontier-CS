import numpy as np

class Solution:
    def __init__(self, **kwargs):
        self.random_state = kwargs.get("random_state", 42)

    @staticmethod
    def _fmt_num(a: float) -> str:
        if not np.isfinite(a):
            return "0.0"
        if abs(a) < 1e-15:
            return "0.0"
        ar = float(a)
        ir = int(round(ar))
        if abs(ar - ir) < 1e-12 and abs(ir) < 10**12:
            return str(ir)
        s = f"{ar:.12g}"
        if s == "-0":
            s = "0"
        return s

    @staticmethod
    def _poly_horner_str(coeffs, var_str: str) -> str:
        # coeffs: [c0, c1, c2] for c0 + c1*var + c2*var**2
        c0, c1, c2 = coeffs
        def is_zero(v):
            return (not np.isfinite(v)) or abs(v) < 1e-15

        expr = None
        if not is_zero(c2):
            expr = Solution._fmt_num(c2)
        if expr is not None:
            expr = f"({expr})*({var_str})"
            if not is_zero(c1):
                expr = f"({expr} + {Solution._fmt_num(c1)})"
        else:
            if not is_zero(c1):
                expr = Solution._fmt_num(c1)

        if expr is not None:
            expr = f"({expr})*({var_str})"
            if not is_zero(c0):
                expr = f"({expr} + {Solution._fmt_num(c0)})"
        else:
            if not is_zero(c0):
                expr = Solution._fmt_num(c0)
            else:
                expr = "0.0"

        return expr

    @staticmethod
    def _eval_poly(coeffs, r2):
        c0, c1, c2 = coeffs
        return (c2 * r2 + c1) * r2 + c0

    @staticmethod
    def _fit_normal_eq(columns, y, yTy, reg_scale=1e-12):
        # columns: list of 1D arrays length n
        n = y.shape[0]
        m = len(columns)
        A = np.column_stack(columns).astype(np.float64, copy=False)
        ATA = A.T @ A
        ATy = A.T @ y
        tr = float(np.trace(ATA))
        lam = reg_scale * (tr / m + 1.0)
        if lam > 0:
            ATA = ATA + lam * np.eye(m, dtype=np.float64)
        try:
            coef = np.linalg.solve(ATA, ATy)
        except np.linalg.LinAlgError:
            coef, _, _, _ = np.linalg.lstsq(A, y, rcond=None)
        sse = float(yTy - 2.0 * float(np.dot(coef, ATy)) + float(coef @ (ATA @ coef)))
        mse = sse / n
        return coef, mse

    def _build_columns(self, r2, arg, k):
        ones = np.ones_like(r2)
        r2_1 = r2
        r2_2 = r2 * r2
        ka = k * arg
        s = np.sin(ka)
        c = np.cos(ka)
        cols = [
            ones, r2_1, r2_2,
            ones * s, r2_1 * s, r2_2 * s,
            ones * c, r2_1 * c, r2_2 * c,
        ]
        return cols

    def _search_best_k(self, r2, arg, y):
        y = y.astype(np.float64, copy=False)
        yTy = float(np.dot(y, y))
        n = y.shape[0]

        # Determine sensible k ranges
        arg_min = float(np.min(arg))
        arg_max = float(np.max(arg))
        arg_range = max(arg_max - arg_min, 1e-12)

        # Heuristic: allow up to ~25 oscillations across range
        # If arg is r2 (0..~2), k might need to be larger; clamp.
        kmax = int(min(250, max(40, round(50.0 * np.pi / arg_range))))
        kmin = 1

        best = None  # (mse, k, coef)
        for k in range(kmin, kmax + 1):
            cols = self._build_columns(r2, arg, float(k))
            coef, mse = self._fit_normal_eq(cols, y, yTy, reg_scale=1e-12)
            if not np.isfinite(mse):
                continue
            if best is None or mse < best[0]:
                best = (mse, float(k), coef)

        if best is None:
            return None

        def refine(center_k, step, half_width_steps):
            nonlocal best
            ks = center_k + step * (np.arange(-half_width_steps, half_width_steps + 1, dtype=np.float64))
            for k in ks:
                if k <= 0:
                    continue
                cols = self._build_columns(r2, arg, float(k))
                coef, mse = self._fit_normal_eq(cols, y, yTy, reg_scale=1e-12)
                if np.isfinite(mse) and mse < best[0]:
                    best = (mse, float(k), coef)

        # Refinement stages
        refine(best[1], 0.1, 15)   # +/-1.5
        refine(best[1], 0.01, 20)  # +/-0.2

        return best  # mse, k, coef

    def _prune_terms(self, cols, y, yTy, coef_full, mse_full, rel_tol=1e-4):
        # Greedy backward elimination
        idx = list(range(len(cols)))
        best_mse = float(mse_full)
        best_idx = idx
        best_coef = coef_full

        def fit_subset(sub_idx):
            sub_cols = [cols[i] for i in sub_idx]
            coef, mse = self._fit_normal_eq(sub_cols, y, yTy, reg_scale=1e-12)
            return coef, mse

        changed = True
        while changed and len(best_idx) > 1:
            changed = False
            # Sort candidates by smallest absolute coefficient magnitude first
            abscoefs = [(abs(best_coef[j]), j) for j in range(len(best_idx))]
            abscoefs.sort(key=lambda t: t[0])
            for _, local_j in abscoefs:
                trial_idx = best_idx[:local_j] + best_idx[local_j + 1:]
                if len(trial_idx) == 0:
                    continue
                tcoef, tmse = fit_subset(trial_idx)
                if np.isfinite(tmse) and tmse <= best_mse * (1.0 + rel_tol):
                    best_mse = float(tmse)
                    best_idx = trial_idx
                    best_coef = tcoef
                    changed = True
                    break

        # Map back to full 9 coefficients
        coef9 = np.zeros(9, dtype=np.float64)
        for j, col_i in enumerate(best_idx):
            coef9[col_i] = best_coef[j]
        return coef9, best_mse

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        X = np.asarray(X, dtype=np.float64)
        y = np.asarray(y, dtype=np.float64).reshape(-1)
        n = y.shape[0]
        if n == 0:
            return {"expression": "0.0", "predictions": [], "details": {}}

        x1 = X[:, 0]
        x2 = X[:, 1]
        r2 = x1 * x1 + x2 * x2
        r = np.sqrt(r2)

        # Handle near-constant targets
        y_mean = float(np.mean(y))
        y_var = float(np.var(y))
        if not np.isfinite(y_var) or y_var < 1e-24:
            expr = self._fmt_num(y_mean)
            preds = np.full(n, y_mean, dtype=np.float64)
            return {"expression": expr, "predictions": preds.tolist(), "details": {"complexity": 0}}

        # Try two radial arguments: r2 and r
        candidates = []
        for arg_name, arg in (("r2", r2), ("r", r)):
            best = self._search_best_k(r2, arg, y)
            if best is None:
                continue
            mse, k, coef = best
            candidates.append((mse, k, coef, arg_name))

        if not candidates:
            # Fallback: quadratic in r2
            A = np.column_stack([np.ones_like(r2), r2, r2 * r2])
            coef, _, _, _ = np.linalg.lstsq(A, y, rcond=None)
            c0, c1, c2 = coef.tolist()
            r2s = "(x1**2 + x2**2)"
            expr = self._poly_horner_str([c0, c1, c2], r2s)
            preds = (c2 * r2 + c1) * r2 + c0
            return {"expression": expr, "predictions": preds.tolist(), "details": {}}

        # Choose best by MSE
        candidates.sort(key=lambda t: t[0])
        best_mse, best_k, best_coef, best_arg_name = candidates[0]

        # Prune terms
        yTy = float(np.dot(y, y))
        best_arg = r2 if best_arg_name == "r2" else r
        cols_full = self._build_columns(r2, best_arg, best_k)
        coef9, pruned_mse = self._prune_terms(cols_full, y, yTy, best_coef, best_mse, rel_tol=1e-4)

        c_off = [float(coef9[0]), float(coef9[1]), float(coef9[2])]
        c_sin = [float(coef9[3]), float(coef9[4]), float(coef9[5])]
        c_cos = [float(coef9[6]), float(coef9[7]), float(coef9[8])]

        # Predictions
        arg_np = best_arg
        ka = best_k * arg_np
        off_np = self._eval_poly(c_off, r2)
        sin_amp_np = self._eval_poly(c_sin, r2)
        cos_amp_np = self._eval_poly(c_cos, r2)
        preds = off_np + sin_amp_np * np.sin(ka) + cos_amp_np * np.cos(ka)

        # Build expression
        r2_str = "(x1**2 + x2**2)"
        arg_str = r2_str if best_arg_name == "r2" else f"({r2_str})**0.5"
        k_str = self._fmt_num(best_k)

        off_str = self._poly_horner_str(c_off, r2_str)
        sin_poly_str = self._poly_horner_str(c_sin, r2_str)
        cos_poly_str = self._poly_horner_str(c_cos, r2_str)

        s_str = f"sin({k_str}*({arg_str}))"
        c_str = f"cos({k_str}*({arg_str}))"

        terms = []
        if off_str != "0.0":
            terms.append(off_str)
        if sin_poly_str != "0.0":
            terms.append(f"({sin_poly_str})*({s_str})")
        if cos_poly_str != "0.0":
            terms.append(f"({cos_poly_str})*({c_str})")

        if not terms:
            expression = "0.0"
        else:
            expression = " + ".join(terms)
            expression = expression.replace("+ -", "- ")

        details = {
            "mse": float(np.mean((y - preds) ** 2)),
            "arg": best_arg_name,
            "k": float(best_k),
        }
        return {
            "expression": expression,
            "predictions": preds.tolist(),
            "details": details,
        }