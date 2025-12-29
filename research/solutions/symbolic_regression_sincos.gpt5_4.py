import numpy as np

class Solution:
    def __init__(self, **kwargs):
        self.kwargs = kwargs

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        x1 = np.asarray(X[:, 0], dtype=float)
        x2 = np.asarray(X[:, 1], dtype=float)
        y = np.asarray(y, dtype=float).ravel()
        n = y.shape[0]

        # Precompute features
        ones = np.ones_like(x1)
        s1 = np.sin(x1)
        c1 = np.cos(x1)
        s2 = np.sin(x2)
        c2 = np.cos(x2)
        s1c2 = s1 * c2
        c1s2 = c1 * s2
        c1c2 = c1 * c2
        s1s2 = s1 * s2
        sinp = np.sin(x1 + x2)
        sind = np.sin(x1 - x2)
        cosp = np.cos(x1 + x2)
        cosd = np.cos(x1 - x2)
        sin2x1 = np.sin(2.0 * x1)
        cos2x1 = np.cos(2.0 * x1)
        sin2x2 = np.sin(2.0 * x2)
        cos2x2 = np.cos(2.0 * x2)

        feat = {
            "1": ones,
            "s1": s1,
            "c1": c1,
            "s2": s2,
            "c2": c2,
            "s1c2": s1c2,
            "c1s2": c1s2,
            "c1c2": c1c2,
            "s1s2": s1s2,
            "sinp": sinp,
            "sind": sind,
            "cosp": cosp,
            "cosd": cosd,
            "sin2x1": sin2x1,
            "cos2x1": cos2x1,
            "sin2x2": sin2x2,
            "cos2x2": cos2x2,
        }
        expr_map = {
            "1": "1",
            "s1": "sin(x1)",
            "c1": "cos(x1)",
            "s2": "sin(x2)",
            "c2": "cos(x2)",
            "s1c2": "sin(x1)*cos(x2)",
            "c1s2": "cos(x1)*sin(x2)",
            "c1c2": "cos(x1)*cos(x2)",
            "s1s2": "sin(x1)*sin(x2)",
            "sinp": "sin(x1 + x2)",
            "sind": "sin(x1 - x2)",
            "cosp": "cos(x1 + x2)",
            "cosd": "cos(x1 - x2)",
            "sin2x1": "sin(2*x1)",
            "cos2x1": "cos(2*x1)",
            "sin2x2": "sin(2*x2)",
            "cos2x2": "cos(2*x2)",
        }

        def fmt(c: float) -> str:
            if not np.isfinite(c):
                return "0"
            if abs(c) < 1e-12:
                return "0"
            return format(float(c), ".12g")

        def build_expression(term_names, weights):
            # separate constant
            constant = 0.0
            items = []
            for name, w in zip(term_names, weights):
                if abs(w) < 1e-12:
                    continue
                if name == "1":
                    constant += w
                else:
                    items.append((name, w))

            expr = ""
            # start with constant if present
            if abs(constant) >= 1e-12:
                expr = fmt(constant)

            for name, w in items:
                term = expr_map[name]
                sign = "+" if w > 0 else "-"
                mag = abs(w)
                if abs(mag - 1.0) < 1e-12:
                    part = term
                else:
                    part = f"{fmt(mag)}*{term}"
                if expr == "":
                    expr = part if sign == "+" else f"-{part}"
                else:
                    expr += f" {sign} {part}"
            if expr == "":
                expr = "0"
            return expr

        def term_base_complexity(name: str):
            # returns (unary_ops, binary_ops) excluding coefficient multiplication and outer sums
            if name in ("s1", "c1", "s2", "c2"):
                return (1, 0)
            if name in ("s1c2", "c1s2", "c1c2", "s1s2"):
                return (2, 1)
            if name in ("sinp", "sind", "cosp", "cosd"):
                return (1, 1)
            if name in ("sin2x1", "cos2x1", "sin2x2", "cos2x2"):
                return (1, 1)  # one mul inside (2*xi)
            if name == "1":
                return (0, 0)
            return (0, 0)

        def compute_complexity(term_names, weights):
            unary = 0
            binary = 0
            num_terms = 0
            const_nonzero = False
            for name, w in zip(term_names, weights):
                if abs(w) < 1e-12:
                    continue
                if name == "1":
                    const_nonzero = True
                    continue
                num_terms += 1
                u, b = term_base_complexity(name)
                unary += u
                binary += b
                if abs(abs(w) - 1.0) > 1e-12:
                    binary += 1  # coefficient multiplication
            items = num_terms + (1 if const_nonzero else 0)
            if items > 1:
                binary += (items - 1)  # sums at top-level
            return int(2 * binary + unary)

        def evaluate_expression(expr: str, x1_arr, x2_arr):
            local_dict = {
                "x1": x1_arr,
                "x2": x2_arr,
                "sin": np.sin,
                "cos": np.cos,
                "exp": np.exp,
                "log": np.log,
            }
            try:
                res = eval(expr, {"__builtins__": {}}, local_dict)
            except Exception:
                res = None
            if res is None:
                return None
            if np.isscalar(res):
                return np.full_like(x1_arr, float(res), dtype=float)
            return np.asarray(res, dtype=float)

        def ls_fit(term_names):
            F = np.column_stack([feat[name] for name in term_names])
            w, _, _, _ = np.linalg.lstsq(F, y, rcond=None)
            return w, F

        std_y = float(np.std(y)) if np.isfinite(np.std(y)) else 1.0
        small_coeff_thr = max(1e-8, 1e-6 * std_y)
        const_snap_thr = max(1e-8, 0.02 * std_y)
        snap_rel = 0.05
        mse_tol_improve = 1e-12

        def try_candidate(term_names):
            w, F = ls_fit(term_names)
            yhat = F @ w
            mse = float(np.mean((y - yhat) ** 2))
            expr = build_expression(term_names, w)
            comp = compute_complexity(term_names, w)
            res_expr = expr
            res_w = w.copy()
            res_mse = mse
            res_comp = comp

            # Simplify coefficients: remove tiny, snap to +/-1, zero constant if small
            w_simpl = w.copy()
            for i, name in enumerate(term_names):
                if name == "1":
                    continue
                c = w_simpl[i]
                if abs(c) < small_coeff_thr:
                    w_simpl[i] = 0.0
                else:
                    for target in (1.0, -1.0):
                        if abs(c - target) <= max(snap_rel * max(abs(c), abs(target)), 1e-6):
                            w_simpl[i] = target
                            break
            # constant term
            if "1" in term_names:
                idx_c = term_names.index("1")
                if abs(w_simpl[idx_c]) <= const_snap_thr:
                    w_simpl[idx_c] = 0.0

            expr_simpl = build_expression(term_names, w_simpl)
            yhat_simpl = evaluate_expression(expr_simpl, x1, x2)
            if yhat_simpl is not None and yhat_simpl.shape == y.shape:
                mse_simpl = float(np.mean((y - yhat_simpl) ** 2))
                comp_simpl = compute_complexity(term_names, w_simpl)
                # Accept simplification if MSE not significantly worse and complexity not higher
                if (mse_simpl <= res_mse * 1.02 + 1e-15) and (comp_simpl < res_comp or mse_simpl + mse_tol_improve < res_mse):
                    res_expr = expr_simpl
                    res_w = w_simpl
                    res_mse = mse_simpl
                    res_comp = comp_simpl
                    yhat = yhat_simpl
                else:
                    yhat = F @ w
            else:
                yhat = F @ w

            return res_expr, yhat, res_mse, res_comp

        # Candidate term sets
        candidates = [
            ["s1", "c2", "1"],
            ["s1", "c1", "s2", "c2", "1"],
            ["sinp", "1"],
            ["s1c2", "1"],
            ["s1c2", "c1s2", "1"],
            ["s1", "c2", "s1c2", "1"],
            ["s1", "c2", "s1c2", "c1s2", "c1c2", "s1s2", "1"],
            ["s1", "s2", "1"],
            ["c1", "c2", "1"],
            ["s1", "c2", "sin2x1", "sin2x2", "cos2x1", "cos2x2", "1"],
        ]

        best_expr = None
        best_pred = None
        best_mse = np.inf
        best_comp = 10**9

        for terms in candidates:
            expr, pred, mse_val, comp_val = try_candidate(terms)
            if pred is None:
                continue
            if (mse_val + mse_tol_improve < best_mse) or (abs(mse_val - best_mse) <= mse_tol_improve and comp_val < best_comp):
                best_expr = expr
                best_pred = pred
                best_mse = mse_val
                best_comp = comp_val

        # As a fallback, if nothing worked, default to sin(x1) + cos(x2)
        if best_expr is None:
            best_expr = "sin(x1) + cos(x2)"
            best_pred = evaluate_expression(best_expr, x1, x2)
            if best_pred is None or best_pred.shape != y.shape:
                best_pred = np.zeros_like(y)
            best_comp = 2 * 1 + 2  # one plus (binary), two unary

        return {
            "expression": best_expr,
            "predictions": np.asarray(best_pred, dtype=float).tolist(),
            "details": {"complexity": int(best_comp)}
        }