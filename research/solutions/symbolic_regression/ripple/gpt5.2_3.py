import numpy as np
import sympy as sp


def _fmt_float(v: float) -> str:
    if not np.isfinite(v):
        return "0.0"
    av = abs(v)
    if av < 1e-15:
        return "0.0"
    s = f"{v:.15g}"
    if s == "-0":
        s = "0"
    return s


def _safe_percentile(a: np.ndarray, q: float) -> float:
    a = np.asarray(a, dtype=np.float64)
    a = a[np.isfinite(a)]
    if a.size == 0:
        return 0.0
    return float(np.percentile(a, q))


def _fit_ridge_scaled(A: np.ndarray, y: np.ndarray, lam: float = 1e-10) -> np.ndarray:
    A = np.asarray(A, dtype=np.float64)
    y = np.asarray(y, dtype=np.float64)
    m = A.shape[1]
    col_rms = np.sqrt(np.mean(A * A, axis=0))
    col_rms = np.where(col_rms > 0.0, col_rms, 1.0)
    As = A / col_rms
    G = As.T @ As
    b = As.T @ y
    if lam > 0:
        G = G + lam * np.eye(m, dtype=np.float64)
    try:
        beta_s = np.linalg.solve(G, b)
    except np.linalg.LinAlgError:
        beta_s = np.linalg.lstsq(G, b, rcond=None)[0]
    beta = beta_s / col_rms
    return beta


def _prune_and_refit(A: np.ndarray, y: np.ndarray, exprs: list, lam: float, keep_constant: bool = True):
    beta = _fit_ridge_scaled(A, y, lam=lam)
    y_std = float(np.std(y)) if np.isfinite(np.std(y)) else 1.0
    thr = max(1e-12, 1e-10 * max(1.0, y_std))
    keep = np.abs(beta) > thr
    if keep_constant and len(keep) > 0:
        keep[0] = True

    # Ensure at least one term
    if not np.any(keep):
        keep[0] = True

    # Refit if pruned
    if int(np.sum(keep)) < A.shape[1]:
        A2 = A[:, keep]
        beta2 = _fit_ridge_scaled(A2, y, lam=lam)
        exprs2 = [e for e, k in zip(exprs, keep) if k]
        return beta2, A2, exprs2
    return beta, A, exprs


def _build_expression(beta: np.ndarray, exprs: list) -> str:
    beta = np.asarray(beta, dtype=np.float64)
    terms = []
    for c, e in zip(beta, exprs):
        if not np.isfinite(c):
            continue
        if abs(c) < 1e-15:
            continue
        if e == "1":
            terms.append(("const", float(c), ""))
        else:
            terms.append(("term", float(c), e))

    if not terms:
        return "0.0"

    # Place constant first for readability
    terms_sorted = sorted(terms, key=lambda t: 0 if t[0] == "const" else 1)

    out = ""
    first = True
    for kind, c, e in terms_sorted:
        sign = "-" if c < 0 else "+"
        ac = abs(c)
        if kind == "const":
            part = _fmt_float(ac)
        else:
            part = f"({_fmt_float(ac)})*({e})"

        if first:
            if sign == "-":
                out = f"-{part}"
            else:
                out = f"{part}"
            first = False
        else:
            if sign == "-":
                out += f" - {part}"
            else:
                out += f" + {part}"
    return out if out else "0.0"


def _estimate_complexity(expr_str: str) -> int:
    try:
        x1, x2 = sp.Symbol("x1"), sp.Symbol("x2")
        expr = sp.sympify(expr_str, locals={"sin": sp.sin, "cos": sp.cos, "exp": sp.exp, "log": sp.log, "x1": x1, "x2": x2})
    except Exception:
        return 10**9

    binary_ops = 0
    unary_ops = 0

    def rec(node):
        nonlocal binary_ops, unary_ops
        if isinstance(node, sp.Add):
            binary_ops += max(0, len(node.args) - 1)
        elif isinstance(node, sp.Mul):
            binary_ops += max(0, len(node.args) - 1)
        elif isinstance(node, sp.Pow):
            binary_ops += 1
        if isinstance(node, sp.Function):
            if node.func in (sp.sin, sp.cos, sp.exp, sp.log):
                unary_ops += 1
        for a in getattr(node, "args", ()):
            rec(a)

    rec(expr)
    return int(2 * binary_ops + unary_ops)


class Solution:
    def __init__(self, **kwargs):
        self.kwargs = kwargs

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        X = np.asarray(X, dtype=np.float64)
        y = np.asarray(y, dtype=np.float64).reshape(-1)
        n = X.shape[0]
        if n == 0:
            return {"expression": "0.0", "predictions": None, "details": {"mse": None, "complexity": 0}}

        x1 = X[:, 0]
        x2 = X[:, 1]
        r2 = x1 * x1 + x2 * x2
        r = np.sqrt(np.maximum(r2, 0.0))

        y_mean = float(np.mean(y))
        y_var = float(np.var(y))
        lam = 1e-10 * max(1.0, y_var)

        # Baseline linear model: a*x1 + b*x2 + c
        A_lin = np.column_stack([np.ones(n), x1, x2])
        beta_lin = _fit_ridge_scaled(A_lin, y, lam=lam)
        pred_lin = A_lin @ beta_lin
        mse_lin = float(np.mean((y - pred_lin) ** 2))

        best = {
            "objective": mse_lin,
            "mse": mse_lin,
            "expr": _build_expression(beta_lin, ["1", "x1", "x2"]),
            "pred": pred_lin,
            "family": "linear",
            "n_terms": 3,
        }

        def consider(A, exprs, family, mse_weight=1.0):
            nonlocal best
            beta, A2, exprs2 = _prune_and_refit(A, y, exprs, lam=lam, keep_constant=True)
            pred = A2 @ beta
            mse = float(np.mean((y - pred) ** 2))

            # Mild complexity penalty
            m = len(exprs2)
            objective = mse_weight * mse * (1.0 + 0.002 * max(0, m - 1))

            if not np.isfinite(objective):
                return

            if objective < best["objective"]:
                best = {
                    "objective": objective,
                    "mse": mse,
                    "expr": _build_expression(beta, exprs2),
                    "pred": pred,
                    "family": family,
                    "n_terms": m,
                }

        # Candidate frequency generation (adaptive + fixed)
        def make_w_candidates(t: np.ndarray) -> list:
            t95 = _safe_percentile(t, 95.0)
            t95 = max(t95, 1e-6)
            w_base = 30.0 / t95
            w_base = float(np.clip(w_base, 0.05, 200.0))
            mult = [0.5, 1.0, 2.0, 3.0, 4.0, 5.0, 7.0, 10.0, 15.0, 20.0]
            fixed = [0.5, 1.0, 2.0, 3.0, 4.0, 5.0, 7.0, 10.0, 12.0, 15.0, 20.0, 25.0, 30.0]
            cand = set()
            for m in mult:
                cand.add(w_base * m)
                cand.add(w_base * np.pi * m)
            for w in fixed:
                cand.add(float(w))
                cand.add(float(np.pi * w))
            # Filter
            out = [w for w in cand if np.isfinite(w) and 0.02 <= w <= 400.0]
            out.sort()
            # Limit to top ~24 spread out
            if len(out) > 24:
                idx = np.linspace(0, len(out) - 1, 24).astype(int)
                out = [out[i] for i in idx]
            return out

        # Polynomial-only radial models (in r2 and r)
        for t, t_expr, fam in [
            (r2, "(x1**2 + x2**2)", "poly_r2"),
            (r, "((x1**2 + x2**2)**0.5)", "poly_r"),
        ]:
            t_pows = [np.ones(n), t]
            t_pows.append(t_pows[1] * t)
            for pb in (0, 1, 2):
                cols = []
                exprs = []
                for p in range(pb + 1):
                    cols.append(t_pows[p])
                    if p == 0:
                        exprs.append("1")
                    elif p == 1:
                        exprs.append(t_expr)
                    else:
                        exprs.append(f"({t_expr})**{p}")
                A = np.column_stack(cols)
                consider(A, exprs, f"{fam}_deg{pb}", mse_weight=1.0)

        # Trig radial models
        def radial_trig_models(t: np.ndarray, t_expr: str, family_prefix: str):
            w_cands = make_w_candidates(t)
            t_pows = [np.ones(n), t, t * t]
            trig_cache = {}
            for w in w_cands:
                arg = w * t
                s = np.sin(arg)
                c = np.cos(arg)
                trig_cache[w] = (s, c)

            for w in w_cands:
                s, c = trig_cache[w]
                w_str = _fmt_float(float(w))
                sin_expr = f"sin(({w_str})*({t_expr}))"
                cos_expr = f"cos(({w_str})*({t_expr}))"

                for pb in (0, 1, 2):
                    for da in (0, 1, 2):
                        # sin only
                        cols = []
                        exprs = []
                        for p in range(pb + 1):
                            cols.append(t_pows[p])
                            if p == 0:
                                exprs.append("1")
                            elif p == 1:
                                exprs.append(t_expr)
                            else:
                                exprs.append(f"({t_expr})**{p}")
                        for p in range(da + 1):
                            cols.append(t_pows[p] * s)
                            if p == 0:
                                exprs.append(sin_expr)
                            elif p == 1:
                                exprs.append(f"({t_expr})*({sin_expr})")
                            else:
                                exprs.append(f"(({t_expr})**{p})*({sin_expr})")
                        A = np.column_stack(cols)
                        consider(A, exprs, f"{family_prefix}_sin_w{w_str}_pb{pb}_da{da}", mse_weight=1.0)

                        # sin + cos
                        cols2 = list(cols)
                        exprs2 = list(exprs)
                        for p in range(da + 1):
                            cols2.append(t_pows[p] * c)
                            if p == 0:
                                exprs2.append(cos_expr)
                            elif p == 1:
                                exprs2.append(f"({t_expr})*({cos_expr})")
                            else:
                                exprs2.append(f"(({t_expr})**{p})*({cos_expr})")
                        A2 = np.column_stack(cols2)
                        consider(A2, exprs2, f"{family_prefix}_sincos_w{w_str}_pb{pb}_da{da}", mse_weight=1.0)

        radial_trig_models(r2, "(x1**2 + x2**2)", "radial_r2")
        radial_trig_models(r, "((x1**2 + x2**2)**0.5)", "radial_r")

        # Separable trig models (in x1 and x2)
        def separable_trig_models():
            ax95 = max(_safe_percentile(np.abs(x1), 95.0), 1e-6)
            bx95 = max(_safe_percentile(np.abs(x2), 95.0), 1e-6)
            wx_base = float(np.clip(25.0 / ax95, 0.05, 400.0))
            wy_base = float(np.clip(25.0 / bx95, 0.05, 400.0))
            mult = [0.5, 1.0, 2.0, 3.0, 4.0, 5.0, 7.0, 10.0]
            w_cands = set()
            for m in mult:
                w_cands.add(wx_base * m)
                w_cands.add(wy_base * m)
                w_cands.add(wx_base * np.pi * m)
                w_cands.add(wy_base * np.pi * m)
            fixed = [1.0, 2.0, 3.0, 5.0, 7.0, 10.0, 12.0, 15.0, 20.0]
            for w in fixed:
                w_cands.add(float(w))
                w_cands.add(float(np.pi * w))
            w_list = [w for w in w_cands if np.isfinite(w) and 0.02 <= w <= 400.0]
            w_list.sort()
            if len(w_list) > 18:
                idx = np.linspace(0, len(w_list) - 1, 18).astype(int)
                w_list = [w_list[i] for i in idx]

            # small polynomial baseline in x1,x2
            base_cols = [np.ones(n), x1, x2, x1 * x1, x2 * x2]
            base_exprs = ["1", "x1", "x2", "(x1**2)", "(x2**2)"]
            for w in w_list:
                w_str = _fmt_float(float(w))
                s1 = np.sin(w * x1)
                c1 = np.cos(w * x1)
                s2 = np.sin(w * x2)
                c2 = np.cos(w * x2)
                cols = list(base_cols) + [s1, s2]
                exprs = list(base_exprs) + [f"sin(({w_str})*(x1))", f"sin(({w_str})*(x2))"]
                A = np.column_stack(cols)
                consider(A, exprs, f"separable_sin_w{w_str}", mse_weight=1.0)

                cols2 = list(base_cols) + [s1, c1, s2, c2]
                exprs2 = list(base_exprs) + [
                    f"sin(({w_str})*(x1))",
                    f"cos(({w_str})*(x1))",
                    f"sin(({w_str})*(x2))",
                    f"cos(({w_str})*(x2))",
                ]
                A2 = np.column_stack(cols2)
                consider(A2, exprs2, f"separable_sincos_w{w_str}", mse_weight=1.0)

        separable_trig_models()

        expression = best["expr"]
        complexity = _estimate_complexity(expression)

        return {
            "expression": expression,
            "predictions": np.asarray(best["pred"], dtype=np.float64),
            "details": {
                "mse": float(best["mse"]),
                "family": best["family"],
                "n_terms": int(best["n_terms"]),
                "complexity": int(complexity),
                "baseline_linear_mse": float(mse_lin),
            },
        }