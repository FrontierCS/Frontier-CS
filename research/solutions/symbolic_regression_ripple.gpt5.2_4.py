import numpy as np
from typing import Any, Dict, List, Optional, Sequence, Tuple


def _ridge_solve(F: np.ndarray, y: np.ndarray, alpha_scale: float = 1e-12) -> np.ndarray:
    m = F.shape[1]
    FtF = F.T @ F
    tr = float(np.trace(FtF))
    alpha = alpha_scale * (tr / m + 1.0)
    try:
        return np.linalg.solve(FtF + alpha * np.eye(m), F.T @ y)
    except np.linalg.LinAlgError:
        coef, _, _, _ = np.linalg.lstsq(F, y, rcond=None)
        return coef


def _prune_and_refit(F: np.ndarray, desc: List[Tuple[str, float]], y: np.ndarray) -> Tuple[np.ndarray, np.ndarray, List[Tuple[str, float]]]:
    coef = _ridge_solve(F, y)
    abscoef = np.abs(coef)
    mx = float(abscoef.max()) if abscoef.size else 0.0
    if mx <= 0.0 or not np.isfinite(mx):
        return coef, F @ coef, desc

    thr = max(1e-10, 1e-6 * mx)
    keep = abscoef >= thr
    if keep.sum() == 0:
        keep[np.argmax(abscoef)] = True

    F2 = F[:, keep]
    desc2 = [d for d, k in zip(desc, keep) if k]
    coef2 = _ridge_solve(F2, y)

    # One more prune pass for extra sparsity
    abscoef2 = np.abs(coef2)
    mx2 = float(abscoef2.max()) if abscoef2.size else 0.0
    thr2 = max(1e-10, 2e-6 * mx2) if (mx2 > 0.0 and np.isfinite(mx2)) else 1e-10
    keep2 = abscoef2 >= thr2
    if keep2.sum() == 0:
        keep2[np.argmax(abscoef2)] = True

    if keep2.sum() < keep.sum():
        F3 = F2[:, keep2]
        desc3 = [d for d, k in zip(desc2, keep2) if k]
        coef3 = _ridge_solve(F3, y)
        pred3 = F3 @ coef3
        return coef3, pred3, desc3

    pred2 = F2 @ coef2
    return coef2, pred2, desc2


def _fmt_num(x: float) -> str:
    if not np.isfinite(x):
        return "0"
    if abs(x) < 1e-15:
        return "0"
    s = f"{x:.12g}"
    s = s.replace("E", "e")
    return s


def _pow_str(base: str, exp: float) -> str:
    if abs(exp) < 1e-15:
        return "1"
    if abs(exp - 1.0) < 1e-15:
        return base
    exp_s = _fmt_num(exp)
    return f"({base}**{exp_s})"


def _make_expression(
    coef: np.ndarray,
    desc: List[Tuple[str, float]],
    arg_type: str,
    b: Optional[float],
) -> str:
    r2_str = "(x1**2 + x2**2)"
    if arg_type == "r":
        arg_str = f"({r2_str}**0.5)"
    else:
        arg_str = r2_str

    terms: List[str] = []
    if b is None:
        b_s = None
    else:
        b_s = _fmt_num(float(b))

    for c, (kind, exp) in zip(coef.tolist(), desc):
        if not np.isfinite(c) or abs(c) < 1e-15:
            continue
        c_s = _fmt_num(float(c))
        if kind == "poly":
            feat = _pow_str(r2_str, exp)
        elif kind == "sin":
            if b_s is None:
                continue
            trig = f"sin(({b_s})*({arg_str}))"
            amp = _pow_str(r2_str, exp)
            feat = trig if amp == "1" else f"({amp})*({trig})"
        elif kind == "cos":
            if b_s is None:
                continue
            trig = f"cos(({b_s})*({arg_str}))"
            amp = _pow_str(r2_str, exp)
            feat = trig if amp == "1" else f"({amp})*({trig})"
        else:
            continue

        if feat == "1":
            term = f"({c_s})"
        else:
            term = f"({c_s})*({feat})"
        terms.append(term)

    if not terms:
        return "0"

    expr = " + ".join(terms)
    expr = expr.replace("+ (-", "- (")
    return expr


def _build_features(r2: np.ndarray, exps: Sequence[float], arg_type: str, b: Optional[float]) -> Tuple[np.ndarray, List[Tuple[str, float]]]:
    n = r2.shape[0]
    exps_arr = np.array(exps, dtype=np.float64)

    P = np.empty((n, len(exps_arr)), dtype=np.float64)
    for j, e in enumerate(exps_arr):
        if abs(e) < 1e-15:
            P[:, j] = 1.0
        else:
            P[:, j] = np.power(r2, e, dtype=np.float64)

    desc: List[Tuple[str, float]] = []
    if b is None:
        F = P
        for e in exps_arr.tolist():
            desc.append(("poly", float(e)))
        return F, desc

    if arg_type == "r":
        arg = np.sqrt(r2)
    else:
        arg = r2

    z = float(b) * arg
    s = np.sin(z)
    c = np.cos(z)

    F = np.concatenate([P, P * s[:, None], P * c[:, None]], axis=1)

    for e in exps_arr.tolist():
        desc.append(("poly", float(e)))
    for e in exps_arr.tolist():
        desc.append(("sin", float(e)))
    for e in exps_arr.tolist():
        desc.append(("cos", float(e)))

    return F, desc


def _evaluate_candidate(r2: np.ndarray, exps: Sequence[float], arg_type: str, b: Optional[float], y: np.ndarray) -> Tuple[float, np.ndarray, np.ndarray, List[Tuple[str, float]]]:
    F, desc = _build_features(r2, exps, arg_type, b)
    coef, pred, desc2 = _prune_and_refit(F, desc, y)
    mse = float(np.mean((y - pred) ** 2))
    return mse, coef, pred, desc2


def _local_refine_b(
    r2: np.ndarray,
    exps: Sequence[float],
    arg_type: str,
    b0: float,
    y: np.ndarray,
    iters: int = 25,
) -> Tuple[float, float, np.ndarray, np.ndarray, List[Tuple[str, float]]]:
    best_b = float(b0)
    best_mse, best_coef, best_pred, best_desc = _evaluate_candidate(r2, exps, arg_type, best_b, y)

    step = 0.5
    for _ in range(iters):
        if step < 1e-3:
            break
        candidates = [max(1e-6, best_b - step), best_b, best_b + step]
        improved = False
        for bb in candidates:
            mse, coef, pred, desc = _evaluate_candidate(r2, exps, arg_type, bb, y)
            if mse < best_mse:
                best_mse, best_b, best_coef, best_pred, best_desc = mse, bb, coef, pred, desc
                improved = True
        if not improved:
            step *= 0.5

    return best_b, best_mse, best_coef, best_pred, best_desc


class Solution:
    def __init__(self, **kwargs: Any):
        self.random_state = int(kwargs.get("random_state", 0))

    def solve(self, X: np.ndarray, y: np.ndarray) -> Dict[str, Any]:
        X = np.asarray(X, dtype=np.float64)
        y = np.asarray(y, dtype=np.float64).reshape(-1)
        n = X.shape[0]
        if n == 0:
            return {"expression": "0", "predictions": [], "details": {"complexity": 0}}

        x1 = X[:, 0]
        x2 = X[:, 1]
        r2 = x1 * x1 + x2 * x2
        r2 = np.maximum(r2, 0.0)

        # Linear baseline
        A = np.column_stack([x1, x2, np.ones_like(x1)])
        try:
            lin_coef, _, _, _ = np.linalg.lstsq(A, y, rcond=None)
        except np.linalg.LinAlgError:
            lin_coef = np.zeros(3, dtype=np.float64)
        lin_pred = A @ lin_coef
        lin_mse = float(np.mean((y - lin_pred) ** 2))
        best = {
            "mse": lin_mse,
            "expr": f"({_fmt_num(float(lin_coef[0]))})*x1 + ({_fmt_num(float(lin_coef[1]))})*x2 + ({_fmt_num(float(lin_coef[2]))})",
            "pred": lin_pred,
            "terms": 3,
            "arg_type": "none",
            "b": None,
            "exps": None,
        }

        y_var = float(np.var(y)) + 1e-12

        # Candidates
        b_list: List[float] = []
        b_list.extend([float(k) for k in range(1, 36)])
        b_list.extend([float(k) for k in range(40, 61, 2)])
        for k in range(1, 9):
            b_list.append(float(k) * float(np.pi))
        b_list = sorted(set(b_list))

        exp_sets_r2: List[List[float]] = [
            [0.0, 1.0],
            [0.0, 1.0, 2.0],
            [0.0, 1.0, 2.0, 3.0],
        ]
        exp_sets_r: List[List[float]] = [
            [0.0, 0.5, 1.0],
            [0.0, 0.5, 1.0, 1.5],
            [0.0, 0.5, 1.0, 1.5, 2.0],
        ]

        # Polynomial-only candidates (low complexity)
        for exps in (exp_sets_r2[0], exp_sets_r2[1], exp_sets_r2[2], exp_sets_r[0], exp_sets_r[1]):
            mse, coef, pred, desc = _evaluate_candidate(r2, exps, "r2", None, y)
            terms = len(desc)
            obj = mse + (2e-6 * y_var) * max(0, terms - 3)
            if obj < best["mse"] + (2e-6 * y_var) * max(0, best["terms"] - 3):
                expr = _make_expression(coef, desc, "r2", None)
                best.update({"mse": mse, "expr": expr, "pred": pred, "terms": terms, "arg_type": "r2", "b": None, "exps": exps})

        # Trig ripple candidates
        search_families = [
            ("r2", exp_sets_r2),
            ("r", exp_sets_r),
        ]

        best_trig = None
        for arg_type, exp_sets in search_families:
            for exps in exp_sets:
                for b in b_list:
                    mse, coef, pred, desc = _evaluate_candidate(r2, exps, arg_type, b, y)
                    terms = len(desc)
                    obj = mse + (2e-6 * y_var) * max(0, terms - 6)
                    best_obj = best["mse"] + (2e-6 * y_var) * max(0, best["terms"] - 6)
                    if obj < best_obj:
                        expr = _make_expression(coef, desc, arg_type, b)
                        best.update({"mse": mse, "expr": expr, "pred": pred, "terms": terms, "arg_type": arg_type, "b": b, "exps": exps})
                        best_trig = (arg_type, exps, b)

        # Local refinement of b around best trig candidate
        if best_trig is not None:
            arg_type, exps, b0 = best_trig
            rb, rmse, rcoef, rpred, rdesc = _local_refine_b(r2, exps, arg_type, float(b0), y, iters=20)
            rterms = len(rdesc)
            robj = rmse + (2e-6 * y_var) * max(0, rterms - 6)
            best_obj = best["mse"] + (2e-6 * y_var) * max(0, best["terms"] - 6)
            if robj < best_obj:
                rexpr = _make_expression(rcoef, rdesc, arg_type, rb)
                best.update({"mse": rmse, "expr": rexpr, "pred": rpred, "terms": rterms, "arg_type": arg_type, "b": rb, "exps": exps})

        # Final expression cleanup: avoid accidental "+ -" patterns
        expression = best["expr"].replace("+ -", "- ")
        predictions = best["pred"]
        if predictions is None or not isinstance(predictions, np.ndarray) or predictions.shape[0] != n:
            predictions = np.zeros(n, dtype=np.float64)

        details = {
            "mse": float(best["mse"]),
            "n_terms": int(best["terms"]),
        }

        return {
            "expression": expression,
            "predictions": predictions.tolist(),
            "details": details,
        }