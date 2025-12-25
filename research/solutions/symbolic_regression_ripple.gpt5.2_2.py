import numpy as np

class Solution:
    def __init__(self, **kwargs):
        self.random_state = kwargs.get("random_state", 42)

    @staticmethod
    def _linear_baseline_mse(X: np.ndarray, y: np.ndarray) -> float:
        x1 = X[:, 0]
        x2 = X[:, 1]
        A = np.column_stack([x1, x2, np.ones_like(x1)])
        coef, _, _, _ = np.linalg.lstsq(A, y, rcond=None)
        pred = A @ coef
        err = y - pred
        return float(np.mean(err * err))

    @staticmethod
    def _lstsq_fit(A: np.ndarray, y: np.ndarray):
        coef, _, _, _ = np.linalg.lstsq(A, y, rcond=None)
        pred = A @ coef
        err = y - pred
        mse = float(np.mean(err * err))
        return coef, pred, mse

    @staticmethod
    def _format_float(v: float) -> str:
        if np.isfinite(v):
            s = f"{float(v):.12g}"
            if s == "-0":
                s = "0"
            return s
        return "0"

    @staticmethod
    def _build_expression(coef: np.ndarray, term_strs: list) -> str:
        parts = []
        for c, t in zip(coef.tolist(), term_strs):
            if not np.isfinite(c) or abs(c) < 1e-14:
                continue
            if t == "1":
                parts.append(f"{Solution._format_float(c)}")
            else:
                if abs(c - 1.0) < 1e-14:
                    parts.append(f"({t})")
                elif abs(c + 1.0) < 1e-14:
                    parts.append(f"(-({t}))")
                else:
                    parts.append(f"({Solution._format_float(c)})*({t})")
        if not parts:
            return "0"
        expr = parts[0]
        for p in parts[1:]:
            expr = f"({expr})+({p})"
        return expr

    @staticmethod
    def _design_matrix(r2: np.ndarray, arg: np.ndarray, w: float, include_inv: bool):
        one = np.ones_like(r2)
        r4 = r2 * r2
        inv = 1.0 / (1.0 + r2) if include_inv else None
        wa = w * arg
        s = np.sin(wa)
        c = np.cos(wa)

        cols = [one, r2, r4]
        names = ["1", "(x1**2 + x2**2)", "(x1**2 + x2**2)**2"]

        if include_inv:
            cols.append(inv)
            names.append("1/(1 + (x1**2 + x2**2))")

        cols.extend([s, r2 * s, r4 * s, c, r2 * c, r4 * c])

        w_str = Solution._format_float(w)
        names.extend([
            f"sin(({w_str})*ARG)",
            f"((x1**2 + x2**2))*sin(({w_str})*ARG)",
            f"((x1**2 + x2**2)**2)*sin(({w_str})*ARG)",
            f"cos(({w_str})*ARG)",
            f"((x1**2 + x2**2))*cos(({w_str})*ARG)",
            f"((x1**2 + x2**2)**2)*cos(({w_str})*ARG)",
        ])

        A = np.column_stack(cols)
        return A, names

    def _fit_ripple(self, X: np.ndarray, y: np.ndarray):
        x1 = X[:, 0]
        x2 = X[:, 1]
        r2 = x1 * x1 + x2 * x2

        r2_max = float(np.max(r2)) if r2.size else 1.0
        r2_max = max(r2_max, 1e-12)

        arg_variants = [
            ("r2", r2, "(x1**2 + x2**2)"),
            ("r", np.sqrt(r2), "((x1**2 + x2**2))**0.5"),
        ]

        # Coarse search: sweep target phase range over data
        t_min, t_max, t_n = 2.0, 200.0, 120
        t_grid = np.linspace(t_min, t_max, t_n)

        best = {
            "mse": np.inf,
            "w": None,
            "arg_id": None,
            "include_inv": None,
        }
        topK = []

        for arg_id, arg_vals, _arg_str in arg_variants:
            arg_max = float(np.max(arg_vals)) if arg_vals.size else 1.0
            arg_max = max(arg_max, 1e-12)
            for include_inv in (False, True):
                # Evaluate MSE for each w quickly
                for t in t_grid:
                    w = float(t / arg_max)
                    A, _ = self._design_matrix(r2, arg_vals, w, include_inv)
                    _, _, mse = self._lstsq_fit(A, y)
                    topK.append((mse, w, arg_id, include_inv))
        topK.sort(key=lambda z: z[0])
        topK = topK[:8]

        # Refine around best candidates
        refined = []
        for mse0, w0, arg_id0, include_inv0 in topK:
            arg_vals0 = r2 if arg_id0 == "r2" else np.sqrt(r2)
            arg_max0 = float(np.max(arg_vals0)) if arg_vals0.size else 1.0
            arg_max0 = max(arg_max0, 1e-12)
            t0 = w0 * arg_max0
            t_lo = max(0.2, t0 * 0.85)
            t_hi = max(t_lo + 0.2, t0 * 1.15)
            t_fine = np.linspace(t_lo, t_hi, 60)
            for t in t_fine:
                w = float(t / arg_max0)
                A, _ = self._design_matrix(r2, arg_vals0, w, include_inv0)
                _, _, mse = self._lstsq_fit(A, y)
                refined.append((mse, w, arg_id0, include_inv0))
        refined.sort(key=lambda z: z[0])
        best_mse, best_w, best_arg_id, best_include_inv = refined[0]

        # Final fit and pruning
        arg_vals = r2 if best_arg_id == "r2" else np.sqrt(r2)
        arg_expr = "(x1**2 + x2**2)" if best_arg_id == "r2" else "((x1**2 + x2**2))**0.5"

        A_full, name_full = self._design_matrix(r2, arg_vals, best_w, best_include_inv)
        coef_full, pred_full, mse_full = self._lstsq_fit(A_full, y)

        # Replace ARG placeholder with chosen argument expression
        name_full = [s.replace("ARG", f"({arg_expr})") for s in name_full]

        idx = list(range(A_full.shape[1]))
        cur_mse = mse_full
        cur_coef = coef_full
        cur_pred = pred_full
        var_y = float(np.var(y)) if y.size else 0.0

        # Greedy elimination
        for _ in range(len(idx) - 1):
            order = np.argsort(np.abs(cur_coef))
            removed = False
            for j in order.tolist():
                if j not in idx:
                    continue
                trial_idx = [k for k in idx if k != j]
                A_t = A_full[:, trial_idx]
                coef_t, pred_t, mse_t = self._lstsq_fit(A_t, y)
                # allow very small degradation
                if mse_t <= cur_mse * (1.0 + 1e-4) + 1e-10 * (var_y + 1.0):
                    idx = trial_idx
                    cur_mse = mse_t
                    cur_coef = coef_t
                    cur_pred = pred_t
                    removed = True
                    break
            if not removed:
                break

        term_strs = [name_full[i] for i in idx]
        expression = self._build_expression(cur_coef, term_strs)

        details = {
            "mse": float(cur_mse),
            "w": float(best_w),
            "arg": best_arg_id,
            "include_inv": bool(best_include_inv),
            "n_terms": int(len(idx)),
        }
        return expression, cur_pred, details

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        X = np.asarray(X, dtype=np.float64)
        y = np.asarray(y, dtype=np.float64).reshape(-1)

        expression, predictions, details = self._fit_ripple(X, y)

        # If something went wrong, fall back to linear model
        if (not isinstance(expression, str)) or (predictions is None) or (not np.all(np.isfinite(predictions))):
            x1 = X[:, 0]
            x2 = X[:, 1]
            A = np.column_stack([x1, x2, np.ones_like(x1)])
            coef, _, _, _ = np.linalg.lstsq(A, y, rcond=None)
            a, b, c = coef.tolist()
            expression = f"({self._format_float(a)})*x1 + ({self._format_float(b)})*x2 + ({self._format_float(c)})"
            predictions = A @ coef
            details = {"fallback": "linear"}

        return {
            "expression": expression,
            "predictions": predictions.tolist() if predictions is not None else None,
            "details": details,
        }