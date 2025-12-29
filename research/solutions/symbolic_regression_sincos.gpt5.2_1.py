import numpy as np
import sympy as sp


def _safe_eval(expr: str, x1: np.ndarray, x2: np.ndarray) -> np.ndarray:
    env = {
        "__builtins__": {},
        "sin": np.sin,
        "cos": np.cos,
        "exp": np.exp,
        "log": np.log,
        "x1": x1,
        "x2": x2,
    }
    return eval(expr, env, {})


def _fit_affine(u: np.ndarray, y: np.ndarray) -> tuple[float, float, float]:
    u = np.asarray(u, dtype=np.float64)
    y = np.asarray(y, dtype=np.float64)
    A = np.column_stack([u, np.ones_like(u)])
    coef, _, _, _ = np.linalg.lstsq(A, y, rcond=None)
    a = float(coef[0])
    b = float(coef[1])
    pred = a * u + b
    mse = float(np.mean((y - pred) ** 2))
    return a, b, mse


def _sympy_complexity(expr_str: str) -> int:
    x1, x2 = sp.Symbol("x1"), sp.Symbol("x2")
    locals_map = {"sin": sp.sin, "cos": sp.cos, "exp": sp.exp, "log": sp.log, "x1": x1, "x2": x2}
    try:
        expr = sp.sympify(expr_str, locals=locals_map)
    except Exception:
        return 10**9

    unary_funcs = {sp.sin, sp.cos, sp.exp, sp.log}

    def rec(e):
        if e.is_Atom:
            return 0, 0
        if e.func in unary_funcs:
            u_b, u_u = rec(e.args[0])
            return u_b, u_u + 1
        if isinstance(e, sp.Add) or isinstance(e, sp.Mul):
            b = max(0, len(e.args) - 1)
            tb, tu = 0, 0
            for a in e.args:
                cb, cu = rec(a)
                tb += cb
                tu += cu
            return tb + b, tu
        if isinstance(e, sp.Pow):
            b1, u1 = rec(e.args[0])
            b2, u2 = rec(e.args[1])
            return b1 + b2 + 1, u1 + u2
        tb, tu = 0, 0
        for a in e.args:
            cb, cu = rec(a)
            tb += cb
            tu += cu
        return tb, tu

    b, u = rec(expr)
    return int(2 * b + u)


def _snap_coef(c: float, scale: float) -> float:
    if not np.isfinite(c):
        return 0.0
    if abs(c) < max(1e-12, 1e-10 * scale):
        return 0.0
    targets = [-3.0, -2.0, -1.0, -0.5, -1.0 / 3.0, 1.0 / 3.0, 0.5, 1.0, 2.0, 3.0]
    for t in targets:
        if abs(c - t) <= max(1e-7, 1e-5 * max(1.0, abs(t))):
            return float(t)
    return float(c)


def _format_float(c: float) -> str:
    if c == 0.0:
        return "0.0"
    s = f"{c:.12g}"
    if "e" in s or "E" in s:
        s = s.replace("E", "e")
    return s


def _needs_parens(s: str) -> bool:
    if not s:
        return False
    # Conservative: wrap if contains + or - not as leading sign.
    # Also wrap if contains space (sympy can insert spaces).
    if " " in s:
        return True
    if "+" in s:
        return True
    if "-" in s[1:]:
        return True
    return False


def _build_linear_expression(intercept: float, terms: list[tuple[float, str]], scale: float) -> str:
    intercept = _snap_coef(intercept, scale)
    cleaned = []
    for c, f in terms:
        c = _snap_coef(c, scale)
        if c == 0.0:
            continue
        cleaned.append((c, f))

    pieces = []

    if intercept != 0.0 or not cleaned:
        pieces.append(_format_float(intercept))

    for c, f in cleaned:
        if c == 1.0:
            term = f
        elif c == -1.0:
            term = f"-({f})" if _needs_parens(f) else f"-{f}"
        else:
            cf = _format_float(c)
            ff = f"({f})" if _needs_parens(f) else f
            term = f"{cf}*{ff}"
        pieces.append(term)

    expr = " + ".join(pieces)
    expr = expr.replace("+ -", "- ")
    return expr


def _expr_to_sympy_str(expr: str) -> str:
    x1, x2 = sp.Symbol("x1"), sp.Symbol("x2")
    locals_map = {"sin": sp.sin, "cos": sp.cos, "exp": sp.exp, "log": sp.log, "x1": x1, "x2": x2}
    try:
        e = sp.sympify(expr, locals=locals_map)
        e = sp.simplify(e)
        s = str(e)
        # Ensure sympy prints in allowed forms (no "Sympy" wrappers)
        return s
    except Exception:
        return expr


def _baseline_mse(X: np.ndarray, y: np.ndarray) -> float:
    x1 = X[:, 0]
    x2 = X[:, 1]
    A = np.column_stack([x1, x2, np.ones_like(x1)])
    coef, _, _, _ = np.linalg.lstsq(A, y, rcond=None)
    pred = A @ coef
    return float(np.mean((y - pred) ** 2))


def _make_arg_str(a: int, b: int) -> str:
    parts = []
    if a != 0:
        if a == 1:
            parts.append("x1")
        elif a == -1:
            parts.append("-x1")
        else:
            parts.append(f"{a}*x1")
    if b != 0:
        if b == 1:
            parts.append("x2")
        elif b == -1:
            parts.append("-x2")
        else:
            parts.append(f"{b}*x2")
    if not parts:
        return "0"
    s = " + ".join(parts)
    s = s.replace("+ -", "- ")
    return s


def _generate_feature_library(X: np.ndarray) -> tuple[np.ndarray, list[str]]:
    x1 = X[:, 0].astype(np.float64, copy=False)
    x2 = X[:, 1].astype(np.float64, copy=False)
    feats = []
    names = []

    def add(name: str, arr: np.ndarray):
        arr = np.asarray(arr, dtype=np.float64)
        if not np.all(np.isfinite(arr)):
            return
        # Avoid constant/near-constant (except intercept will be separate)
        if np.std(arr) < 1e-12:
            return
        names.append(name)
        feats.append(arr)

    # Base linear terms
    add("x1", x1)
    add("x2", x2)

    # Trig on single vars with small integer multipliers
    for k in (1, 2):
        add(f"sin({k}*x1)" if k != 1 else "sin(x1)", np.sin(k * x1))
        add(f"cos({k}*x1)" if k != 1 else "cos(x1)", np.cos(k * x1))
        add(f"sin({k}*x2)" if k != 1 else "sin(x2)", np.sin(k * x2))
        add(f"cos({k}*x2)" if k != 1 else "cos(x2)", np.cos(k * x2))

    # Trig of linear combinations a*x1 + b*x2 with small integers
    ab_vals = [-2, -1, 0, 1, 2]
    for a in ab_vals:
        for b in ab_vals:
            if a == 0 and b == 0:
                continue
            if a == 0 and abs(b) <= 2:
                continue  # already covered by single-var trig
            if b == 0 and abs(a) <= 2:
                continue  # already covered
            arg = a * x1 + b * x2
            arg_str = _make_arg_str(a, b)
            add(f"sin({arg_str})", np.sin(arg))
            add(f"cos({arg_str})", np.cos(arg))

    # Products of sin/cos of individual vars
    trig1 = [("sin(x1)", np.sin(x1)), ("cos(x1)", np.cos(x1)), ("sin(2*x1)", np.sin(2 * x1)), ("cos(2*x1)", np.cos(2 * x1))]
    trig2 = [("sin(x2)", np.sin(x2)), ("cos(x2)", np.cos(x2)), ("sin(2*x2)", np.sin(2 * x2)), ("cos(2*x2)", np.cos(2 * x2))]
    for n1, a1 in trig1:
        for n2, a2 in trig2:
            add(f"{n1}*{n2}", a1 * a2)

    Phi = np.column_stack(feats) if feats else np.empty((X.shape[0], 0), dtype=np.float64)
    return Phi, names


def _forward_select(Phi: np.ndarray, names: list[str], y: np.ndarray, max_terms: int = 5) -> tuple[list[int], np.ndarray, float]:
    n, k = Phi.shape
    y = y.astype(np.float64, copy=False)

    # Always include intercept separately; fit on [Phi_selected, 1]
    remaining = list(range(k))
    selected: list[int] = []
    best_coef = None
    best_mse = np.inf

    models = []

    def fit(idxs: list[int]) -> tuple[np.ndarray, float]:
        if idxs:
            A = np.column_stack([Phi[:, idxs], np.ones(n)])
        else:
            A = np.ones((n, 1), dtype=np.float64)
        coef, _, _, _ = np.linalg.lstsq(A, y, rcond=None)
        pred = A @ coef
        mse = float(np.mean((y - pred) ** 2))
        return coef, mse

    # start with intercept only
    coef0, mse0 = fit([])
    models.append(([], coef0, mse0))
    best_coef, best_mse = coef0, mse0

    for _ in range(max_terms):
        best_local = None
        best_local_mse = np.inf
        best_local_coef = None
        for j in remaining:
            idxs = selected + [j]
            coef, mse = fit(idxs)
            if mse < best_local_mse:
                best_local_mse = mse
                best_local = j
                best_local_coef = coef
        if best_local is None:
            break
        # Require meaningful improvement
        if best_mse - best_local_mse <= max(1e-14, 1e-10 * (abs(best_mse) + 1.0)):
            break
        selected.append(best_local)
        remaining.remove(best_local)
        best_mse = best_local_mse
        best_coef = best_local_coef
        models.append((selected.copy(), best_coef.copy(), best_mse))

    # Choose simplest within tolerance of best MSE
    best_mse_overall = min(m[2] for m in models)
    tol = max(1e-12, 1e-6 * (np.var(y) + 1e-12))
    candidates = [m for m in models if m[2] <= best_mse_overall + tol]

    def model_complexity(m):
        idxs, coef, _ = m
        intercept = coef[-1] if len(coef) >= 1 else 0.0
        terms = []
        for t, j in enumerate(idxs):
            terms.append((float(coef[t]), names[j]))
        expr = _build_linear_expression(float(intercept), terms, scale=float(np.std(y) + 1e-12))
        expr = _expr_to_sympy_str(expr)
        return _sympy_complexity(expr)

    candidates.sort(key=lambda m: (model_complexity(m), m[2], len(m[0])))
    idxs, coef, mse = candidates[0]
    return idxs, coef, float(mse)


class Solution:
    def __init__(self, **kwargs):
        self.kwargs = kwargs

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        X = np.asarray(X, dtype=np.float64)
        y = np.asarray(y, dtype=np.float64).reshape(-1)
        n = X.shape[0]
        x1 = X[:, 0]
        x2 = X[:, 1]
        y_scale = float(np.std(y) + 1e-12)

        # Baseline
        try:
            base_mse = _baseline_mse(X, y)
        except Exception:
            base_mse = float(np.mean((y - np.mean(y)) ** 2))

        # First: try a curated list of very low-complexity expressions
        base_exprs = [
            "sin(x1)",
            "cos(x1)",
            "sin(x2)",
            "cos(x2)",
            "sin(x1)+sin(x2)",
            "sin(x1)+cos(x2)",
            "cos(x1)+sin(x2)",
            "cos(x1)+cos(x2)",
            "sin(x1)-sin(x2)",
            "sin(x1)-cos(x2)",
            "cos(x1)-sin(x2)",
            "cos(x1)-cos(x2)",
            "sin(x1)*sin(x2)",
            "sin(x1)*cos(x2)",
            "cos(x1)*sin(x2)",
            "cos(x1)*cos(x2)",
            "sin(x1+x2)",
            "cos(x1+x2)",
            "sin(x1-x2)",
            "cos(x1-x2)",
            "sin(2*x1)",
            "cos(2*x1)",
            "sin(2*x2)",
            "cos(2*x2)",
        ]

        best_expr = None
        best_pred = None
        best_mse = np.inf
        best_comp = 10**9

        for e in base_exprs:
            try:
                u = _safe_eval(e, x1, x2)
                if u.shape != y.shape or not np.all(np.isfinite(u)):
                    continue
            except Exception:
                continue

            mse0 = float(np.mean((y - u) ** 2))
            expr0 = _expr_to_sympy_str(e)
            comp0 = _sympy_complexity(expr0)

            # Consider affine scaling if it helps substantially
            a, b, mse1 = _fit_affine(u, y)

            # Build potentially simplified scaled expression
            a_s = _snap_coef(a, y_scale)
            b_s = _snap_coef(b, y_scale)
            if a_s == 0.0:
                expr1 = _format_float(b_s)
            else:
                if a_s == 1.0:
                    if b_s == 0.0:
                        expr1 = e
                    else:
                        expr1 = f"{e} + {_format_float(b_s)}"
                elif a_s == -1.0:
                    if b_s == 0.0:
                        expr1 = f"-({e})"
                    else:
                        expr1 = f"-({e}) + {_format_float(b_s)}"
                else:
                    expr1 = f"{_format_float(a_s)}*({e})"
                    if b_s != 0.0:
                        expr1 = f"{expr1} + {_format_float(b_s)}"
            expr1 = expr1.replace("+ -", "- ")
            expr1 = _expr_to_sympy_str(expr1)
            comp1 = _sympy_complexity(expr1)

            # Choose between unscaled and scaled using primary MSE, then complexity
            for expr_cand, mse_cand, comp_cand in ((expr0, mse0, comp0), (expr1, mse1, comp1)):
                if mse_cand < best_mse - 1e-15 or (abs(mse_cand - best_mse) <= max(1e-12, 1e-6 * (np.var(y) + 1e-12)) and comp_cand < best_comp):
                    try:
                        pred_cand = _safe_eval(expr_cand, x1, x2)
                        if pred_cand.shape != y.shape or not np.all(np.isfinite(pred_cand)):
                            continue
                    except Exception:
                        continue
                    best_expr = expr_cand
                    best_mse = float(mse_cand)
                    best_comp = int(comp_cand)
                    best_pred = pred_cand

        # If not good enough, run feature selection on a broader library
        # Heuristic: if we didn't beat linear baseline by a lot, search broader.
        if best_expr is None or best_mse > 0.05 * base_mse:
            Phi, names = _generate_feature_library(X)
            if Phi.shape[1] > 0:
                idxs, coef, mse = _forward_select(Phi, names, y, max_terms=5)

                # Build expression from selected features + intercept
                intercept = float(coef[-1])
                terms = []
                for t, j in enumerate(idxs):
                    terms.append((float(coef[t]), names[j]))

                expr = _build_linear_expression(intercept, terms, scale=y_scale)
                expr = _expr_to_sympy_str(expr)

                try:
                    pred = _safe_eval(expr, x1, x2)
                    if pred.shape == y.shape and np.all(np.isfinite(pred)):
                        comp = _sympy_complexity(expr)
                        mse2 = float(np.mean((y - pred) ** 2))
                        # Prefer this if significantly better, or similar but simpler
                        if best_expr is None or mse2 < best_mse - 1e-12 or (abs(mse2 - best_mse) <= max(1e-12, 1e-6 * (np.var(y) + 1e-12)) and comp < best_comp):
                            best_expr, best_pred, best_mse, best_comp = expr, pred, mse2, comp
                except Exception:
                    pass

        # Final fallback: constant mean
        if best_expr is None:
            c = float(np.mean(y))
            best_expr = _format_float(c)
            best_pred = np.full(n, c, dtype=np.float64)
            best_mse = float(np.mean((y - best_pred) ** 2))
            best_comp = _sympy_complexity(best_expr)

        return {
            "expression": str(best_expr),
            "predictions": best_pred.tolist() if best_pred is not None else None,
            "details": {
                "complexity": int(best_comp),
                "mse": float(best_mse),
            },
        }