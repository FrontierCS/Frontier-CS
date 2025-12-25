import numpy as np
import itertools
from typing import Dict, List, Tuple, Any


def _safe_exp(z: np.ndarray) -> np.ndarray:
    return np.exp(np.clip(z, -80.0, 80.0))


def _format_float(x: float) -> str:
    if not np.isfinite(x):
        return "0.0"
    if abs(x) < 1e-15:
        return "0.0"
    return f"{x:.12g}"


def _combine_linear_terms(terms: List[Tuple[float, str]]) -> str:
    if not terms:
        return "0.0"

    merged: Dict[str, float] = {}
    for c, e in terms:
        if not np.isfinite(c):
            continue
        if abs(c) < 1e-14:
            continue
        merged[e] = merged.get(e, 0.0) + float(c)

    cleaned: List[Tuple[float, str]] = []
    for e, c in merged.items():
        if abs(c) >= 1e-12:
            cleaned.append((c, e))

    if not cleaned:
        return "0.0"

    def key_fn(t):
        c, e = t
        if e == "1":
            return (0, 0, -abs(c))
        return (1, len(e), -abs(c))

    cleaned.sort(key=key_fn)

    def term_body(abscoef: float, expr: str) -> str:
        if expr == "1":
            return _format_float(abscoef)
        if abs(abscoef - 1.0) < 5e-13:
            return f"({expr})"
        return f"{_format_float(abscoef)}*({expr})"

    parts: List[str] = []
    for i, (c, e) in enumerate(cleaned):
        if i == 0:
            if c < 0:
                parts.append("-" + term_body(-c, e))
            else:
                parts.append(term_body(c, e))
        else:
            if c < 0:
                parts.append(" - " + term_body(-c, e))
            else:
                parts.append(" + " + term_body(c, e))
    return "".join(parts)


def _ridge_lstsq(A: np.ndarray, y: np.ndarray, alpha: float = 1e-10) -> np.ndarray:
    k = A.shape[1]
    if k == 0:
        return np.zeros((0,), dtype=np.float64)
    ATA = A.T @ A
    if alpha > 0:
        ATA = ATA + alpha * np.eye(k, dtype=np.float64)
    ATy = A.T @ y
    try:
        return np.linalg.solve(ATA, ATy)
    except np.linalg.LinAlgError:
        return np.linalg.lstsq(A, y, rcond=None)[0]


class Solution:
    def __init__(self, **kwargs):
        self.max_terms = int(kwargs.get("max_terms", 10))
        self.random_state = int(kwargs.get("random_state", 0))

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        X = np.asarray(X, dtype=np.float64)
        y = np.asarray(y, dtype=np.float64)
        n, d = X.shape
        if d != 4:
            raise ValueError("Expected X shape (n, 4).")

        x1, x2, x3, x4 = X[:, 0], X[:, 1], X[:, 2], X[:, 3]
        xs = [x1, x2, x3, x4]
        names = ["x1", "x2", "x3", "x4"]

        ones = np.ones(n, dtype=np.float64)
        x_sq = [xi * xi for xi in xs]
        x_cb = [x_sq[i] * xs[i] for i in range(4)]

        pair_idx = [(0, 1), (0, 2), (0, 3), (1, 2), (1, 3), (2, 3)]
        triple_idx = [(0, 1, 2), (0, 1, 3), (0, 2, 3), (1, 2, 3)]

        # Polynomial library (pure polynomial terms, no exp)
        poly_base: List[Tuple[str, np.ndarray]] = []
        poly_base.append(("1", ones))
        for i in range(4):
            poly_base.append((names[i], xs[i]))
        for i in range(4):
            poly_base.append((f"{names[i]}**2", x_sq[i]))
        for i in range(4):
            poly_base.append((f"{names[i]}**3", x_cb[i]))
        for (i, j) in pair_idx:
            poly_base.append((f"{names[i]}*{names[j]}", xs[i] * xs[j]))
        for i in range(4):
            for j in range(4):
                if i == j:
                    continue
                poly_base.append((f"({names[i]}**2)*{names[j]}", x_sq[i] * xs[j]))
        for (i, j, k) in triple_idx:
            poly_base.append((f"{names[i]}*{names[j]}*{names[k]}", xs[i] * xs[j] * xs[k]))
        for (i, j) in pair_idx:
            poly_base.append((f"({names[i]}**2)*({names[j]}**2)", x_sq[i] * x_sq[j]))

        # Polynomial terms to multiply with exp factors
        poly_mult: List[Tuple[str, np.ndarray]] = []
        poly_mult.append(("1", ones))
        for i in range(4):
            poly_mult.append((names[i], xs[i]))
        for (i, j) in pair_idx:
            poly_mult.append((f"{names[i]}*{names[j]}", xs[i] * xs[j]))

        # Exponential factors
        exp_factors: List[Tuple[str, np.ndarray]] = []
        exp_factors.append(("1", ones))

        scales_sq = [0.5, 1.0, 2.0]
        # square-sum subsets (sizes 1..4)
        for r in [1, 2, 3, 4]:
            for subset in itertools.combinations(range(4), r):
                sum_vals = np.zeros(n, dtype=np.float64)
                sum_expr_parts = []
                for idx in subset:
                    sum_vals += x_sq[idx]
                    sum_expr_parts.append(f"{names[idx]}**2")
                sum_expr = " + ".join(sum_expr_parts)
                for s in scales_sq:
                    if s == 1.0:
                        expr = f"exp(-({sum_expr}))"
                        vals = _safe_exp(-(sum_vals))
                    else:
                        expr = f"exp(-{_format_float(s)}*({sum_expr}))"
                        vals = _safe_exp(-(s * sum_vals))
                    exp_factors.append((expr, vals))

        scales_lin = [0.5, 1.0, 2.0]
        for i in range(4):
            for s in scales_lin:
                if s == 1.0:
                    expr = f"exp(-{names[i]})"
                    vals = _safe_exp(-xs[i])
                else:
                    expr = f"exp(-{_format_float(s)}*{names[i]})"
                    vals = _safe_exp(-(s * xs[i]))
                exp_factors.append((expr, vals))
        for (i, j) in pair_idx:
            for s in scales_lin:
                if s == 1.0:
                    expr = f"exp(-({names[i]} + {names[j]}))"
                    vals = _safe_exp(-(xs[i] + xs[j]))
                else:
                    expr = f"exp(-{_format_float(s)}*({names[i]} + {names[j]}))"
                    vals = _safe_exp(-(s * (xs[i] + xs[j])))
                exp_factors.append((expr, vals))

        # Build features: pure polynomials + (poly_mult * exp_factors excluding "1")
        feat_vals: List[np.ndarray] = []
        feat_poly: List[str] = []
        feat_exp: List[str] = []

        # Ensure one unique constant feature first
        feat_vals.append(ones)
        feat_poly.append("1")
        feat_exp.append("1")

        # Pure polynomial features (excluding constant already added)
        for (pexpr, pval) in poly_base[1:]:
            feat_vals.append(np.nan_to_num(pval, nan=0.0, posinf=0.0, neginf=0.0))
            feat_poly.append(pexpr)
            feat_exp.append("1")

        # Exponential-multiplied features
        for (eexpr, evals) in exp_factors[1:]:
            evals = np.nan_to_num(evals, nan=0.0, posinf=0.0, neginf=0.0)
            for (pexpr, pval) in poly_mult:
                if pexpr == "1":
                    feat_vals.append(evals)
                    feat_poly.append("1")
                    feat_exp.append(eexpr)
                else:
                    feat_vals.append(np.nan_to_num(pval * evals, nan=0.0, posinf=0.0, neginf=0.0))
                    feat_poly.append(pexpr)
                    feat_exp.append(eexpr)

        Phi = np.column_stack(feat_vals).astype(np.float64, copy=False)
        m = Phi.shape[1]

        # Remove near-constant/zero columns (except the intercept at col 0)
        col_norm = np.linalg.norm(Phi, axis=0)
        keep = np.ones(m, dtype=bool)
        keep[0] = True
        keep[1:] = col_norm[1:] > 1e-14
        if not np.all(keep):
            Phi = Phi[:, keep]
            col_norm = col_norm[keep]
            feat_poly = [p for p, k in zip(feat_poly, keep) if k]
            feat_exp = [e for e, k in zip(feat_exp, keep) if k]
            m = Phi.shape[1]

        # OMP with ridge refit
        y0 = np.nan_to_num(y, nan=0.0, posinf=0.0, neginf=0.0)
        selected: List[int] = [0]
        A = Phi[:, selected]
        coef = _ridge_lstsq(A, y0, alpha=1e-10)
        pred = A @ coef
        res = y0 - pred
        best_mse = float(np.mean(res * res))
        last_mse = best_mse

        max_terms = int(max(2, min(self.max_terms, m)))
        for _ in range(max_terms - 1):
            corr = Phi.T @ res
            score = np.abs(corr) / (col_norm + 1e-18)
            score[selected] = 0.0
            j = int(np.argmax(score))
            if score[j] <= 0.0 or (not np.isfinite(score[j])):
                break

            candidate_selected = selected + [j]
            A = Phi[:, candidate_selected]
            c = _ridge_lstsq(A, y0, alpha=1e-10)
            p = A @ c
            r = y0 - p
            mse = float(np.mean(r * r))

            if mse > last_mse * (1.0 - 1e-10):
                # Accept only if it doesn't get worse (tiny tolerance)
                # But allow small fluctuations if large potential correlation.
                if mse > last_mse * (1.0 + 1e-7):
                    break

            selected = candidate_selected
            coef = c
            pred = p
            res = r
            last_mse = mse
            if mse < best_mse:
                best_mse = mse

            if len(selected) >= 3:
                rel_improve = (best_mse / (np.mean(y0 * y0) + 1e-18))
                if rel_improve < 1e-16:
                    break
            if len(selected) >= max_terms:
                break

        # Prune small coefficients and refit
        coef_full = coef
        selected_full = selected
        y_scale = float(np.std(y0) + 1e-12)
        keep_sel = [i for i, c in zip(selected_full, coef_full) if abs(float(c)) >= 1e-10 * y_scale or i == 0]
        if len(keep_sel) < len(selected_full):
            A = Phi[:, keep_sel]
            coef = _ridge_lstsq(A, y0, alpha=1e-10)
            selected = keep_sel
            pred = A @ coef
        else:
            coef = coef_full
            selected = selected_full

        # Build expression with factoring by exp factor
        groups: Dict[str, List[Tuple[float, str]]] = {}
        for idx, c in zip(selected, coef):
            c = float(c)
            if not np.isfinite(c) or abs(c) < 1e-14:
                continue
            poly_str = feat_poly[idx]
            exp_str = feat_exp[idx]
            groups.setdefault(exp_str, []).append((c, poly_str))

        group_exprs: List[str] = []
        # Put exp="1" first for readability
        exp_keys = list(groups.keys())
        exp_keys.sort(key=lambda k: (k != "1", len(k)))

        for exp_str in exp_keys:
            poly_sum = _combine_linear_terms(groups[exp_str])
            if poly_sum == "0.0":
                continue
            if exp_str == "1":
                group_exprs.append(poly_sum)
            else:
                if poly_sum == "1.0":
                    group_exprs.append(exp_str)
                elif poly_sum == "-1.0":
                    group_exprs.append(f"-({exp_str})")
                else:
                    group_exprs.append(f"({poly_sum})*({exp_str})")

        if not group_exprs:
            expression = "0.0"
        else:
            # Combine group expressions
            # Treat each group as "+ 1*(group)"
            combined_terms = [(1.0, ge) for ge in group_exprs]
            expression = _combine_linear_terms(combined_terms)
            if expression == "0.0":
                expression = "0.0"

        # Compute predictions
        env = {
            "x1": x1,
            "x2": x2,
            "x3": x3,
            "x4": x4,
            "exp": np.exp,
            "sin": np.sin,
            "cos": np.cos,
            "log": np.log,
        }
        try:
            preds = eval(expression, {"__builtins__": {}}, env)
            if np.isscalar(preds):
                preds = np.full(n, float(preds), dtype=np.float64)
            else:
                preds = np.asarray(preds, dtype=np.float64)
                if preds.shape != (n,):
                    preds = np.reshape(preds, (n,))
            preds = np.nan_to_num(preds, nan=0.0, posinf=0.0, neginf=0.0)
        except Exception:
            preds = np.asarray(pred, dtype=np.float64)
            preds = np.nan_to_num(preds, nan=0.0, posinf=0.0, neginf=0.0)

        return {
            "expression": expression,
            "predictions": preds.tolist(),
            "details": {
                "n_features": int(Phi.shape[1]),
                "n_selected": int(len(selected)),
                "mse_train": float(np.mean((y0 - preds) ** 2)),
            },
        }