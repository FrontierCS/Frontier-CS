import numpy as np
import sympy as sp


def _fmt(x: float) -> str:
    if not np.isfinite(x):
        return "0"
    if abs(x) < 1e-15:
        return "0"
    s = f"{x:.12g}"
    if s == "-0":
        s = "0"
    return s


def _sum_parts(parts):
    if not parts:
        return "0"
    out = parts[0]
    for p in parts[1:]:
        if p.startswith("-"):
            out += " - " + p[1:]
        else:
            out += " + " + p
    return out


def _poly_expr(coefs, z_str, tol=0.0):
    parts = []
    for k, c in enumerate(coefs):
        if not np.isfinite(c) or abs(c) <= tol:
            continue
        cs = _fmt(float(c))
        if cs == "0":
            continue
        if k == 0:
            part = cs
        elif k == 1:
            part = f"{cs}*({z_str})"
        else:
            part = f"{cs}*(({z_str})**{k})"
        parts.append(part)
    return _sum_parts(parts) if parts else "0"


def _build_design(z, w, d_trig, d_const, include_cos):
    n = z.shape[0]
    s = np.sin(w * z)
    m = (d_trig + 1) + (d_trig + 1 if include_cos else 0) + (d_const + 1)
    A = np.empty((n, m), dtype=np.float64)

    col = 0
    zpow = np.ones(n, dtype=np.float64)
    for k in range(d_trig + 1):
        if k > 0:
            zpow = zpow * z
        A[:, col] = zpow * s
        col += 1

    if include_cos:
        c = np.cos(w * z)
        zpow = np.ones(n, dtype=np.float64)
        for k in range(d_trig + 1):
            if k > 0:
                zpow = zpow * z
            A[:, col] = zpow * c
            col += 1

    zpow = np.ones(n, dtype=np.float64)
    for k in range(d_const + 1):
        if k > 0:
            zpow = zpow * z
        A[:, col] = zpow
        col += 1

    return A


def _ridge_solve(A, y, lam=1e-10):
    m = A.shape[1]
    AtA = A.T @ A
    scale = float(np.trace(AtA)) / max(m, 1)
    reg = lam * max(scale, 1e-12)
    AtA.flat[:: m + 1] += reg
    Aty = A.T @ y
    try:
        coef = np.linalg.solve(AtA, Aty)
    except np.linalg.LinAlgError:
        coef, _, _, _ = np.linalg.lstsq(A, y, rcond=None)
    return coef


def _prune_refit(A, y, coef, term_kinds, y_rms, keep_const_idx, min_keep=1):
    pred = A @ coef
    resid = pred - y
    mse = float(np.mean(resid * resid))

    col_rms = np.sqrt(np.mean(A * A, axis=0))
    contrib = np.abs(coef) * col_rms
    thresh = max(1e-4 * y_rms, 1e-12)

    keep = contrib > thresh
    if keep_const_idx is not None:
        keep[keep_const_idx] = True

    # Ensure at least one trig term
    trig_mask = np.array([k in ("sin", "cos") for k, _ in term_kinds], dtype=bool)
    if trig_mask.any() and not np.any(keep & trig_mask):
        j = int(np.argmax(contrib * trig_mask))
        keep[j] = True

    if np.sum(keep) < min_keep:
        j = int(np.argmax(contrib))
        keep[:] = False
        keep[j] = True
        if keep_const_idx is not None:
            keep[keep_const_idx] = True

    if np.all(keep):
        return coef, mse

    A2 = A[:, keep]
    coef2 = _ridge_solve(A2, y, lam=1e-10)
    coef_full = np.zeros_like(coef)
    coef_full[keep] = coef2
    pred2 = A @ coef_full
    resid2 = pred2 - y
    mse2 = float(np.mean(resid2 * resid2))
    return coef_full, mse2 if np.isfinite(mse2) else mse


def _coef_to_groups(coef, d_trig, d_const, include_cos):
    idx = 0
    ps = coef[idx : idx + (d_trig + 1)]
    idx += (d_trig + 1)
    pc = None
    if include_cos:
        pc = coef[idx : idx + (d_trig + 1)]
        idx += (d_trig + 1)
    p0 = coef[idx : idx + (d_const + 1)]
    return ps, pc, p0


def _build_expression(z_str, w, d_trig, d_const, include_cos, coef, tol=0.0):
    ps, pc, p0 = _coef_to_groups(coef, d_trig, d_const, include_cos)
    w_str = _fmt(float(w))

    sin_arg = f"(({w_str})*({z_str}))"
    parts = []

    ps_str = _poly_expr(ps, z_str, tol=tol)
    if ps_str != "0":
        parts.append(f"({ps_str})*sin({sin_arg})")

    if include_cos and pc is not None:
        pc_str = _poly_expr(pc, z_str, tol=tol)
        if pc_str != "0":
            parts.append(f"({pc_str})*cos({sin_arg})")

    p0_str = _poly_expr(p0, z_str, tol=tol)
    if p0_str != "0":
        parts.append(f"({p0_str})")

    return _sum_parts(parts) if parts else "0"


def _sympy_complexity(expr_str: str):
    try:
        x1, x2 = sp.Symbol("x1"), sp.Symbol("x2")
        expr = sp.sympify(expr_str, locals={"sin": sp.sin, "cos": sp.cos, "exp": sp.exp, "log": sp.log, "x1": x1, "x2": x2})
    except Exception:
        return None

    bin_ops = 0
    un_ops = 0
    for node in sp.preorder_traversal(expr):
        f = getattr(node, "func", None)
        if f in (sp.sin, sp.cos, sp.exp, sp.log):
            un_ops += 1
        elif f is sp.Add or f is sp.Mul:
            try:
                bin_ops += max(len(node.args) - 1, 0)
            except Exception:
                pass
        elif f is sp.Pow:
            bin_ops += 1
    return int(2 * bin_ops + un_ops)


class Solution:
    def __init__(self, **kwargs):
        self.kwargs = kwargs

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        X = np.asarray(X, dtype=np.float64)
        y = np.asarray(y, dtype=np.float64).reshape(-1)
        n = X.shape[0]
        x1 = X[:, 0]
        x2 = X[:, 1]
        y_rms = float(np.sqrt(np.mean(y * y))) + 1e-12
        y_var = float(np.var(y)) + 1e-12

        # Linear baseline (fallback)
        A_lin = np.column_stack([x1, x2, np.ones_like(x1)])
        try:
            coef_lin, _, _, _ = np.linalg.lstsq(A_lin, y, rcond=None)
            pred_lin = A_lin @ coef_lin
            mse_lin = float(np.mean((pred_lin - y) ** 2))
        except Exception:
            coef_lin = np.array([0.0, 0.0, float(np.mean(y))], dtype=np.float64)
            pred_lin = A_lin @ coef_lin
            mse_lin = float(np.mean((pred_lin - y) ** 2))

        rng = np.random.RandomState(0)
        m_search = min(n, 2500)
        if m_search < n:
            idx = rng.choice(n, size=m_search, replace=False)
        else:
            idx = np.arange(n)

        candidates = [
            {"z": "r2", "d_trig": 2, "d_const": 2, "cos": True},
            {"z": "r2", "d_trig": 1, "d_const": 1, "cos": True},
            {"z": "r2", "d_trig": 1, "d_const": 1, "cos": False},
            {"z": "r2", "d_trig": 0, "d_const": 0, "cos": True},
            {"z": "r2", "d_trig": 0, "d_const": 0, "cos": False},
            {"z": "r", "d_trig": 1, "d_const": 1, "cos": True},
            {"z": "r", "d_trig": 1, "d_const": 1, "cos": False},
            {"z": "r", "d_trig": 0, "d_const": 0, "cos": True},
            {"z": "r", "d_trig": 0, "d_const": 0, "cos": False},
        ]

        best = None

        for cand in candidates:
            ztype = cand["z"]
            d_trig = int(cand["d_trig"])
            d_const = int(cand["d_const"])
            include_cos = bool(cand["cos"])

            if ztype == "r2":
                z = x1 * x1 + x2 * x2
                z_str = "(x1**2 + x2**2)"
            else:
                z = np.sqrt(x1 * x1 + x2 * x2)
                z_str = "((x1**2 + x2**2)**0.5)"

            z_s = z[idx]
            y_s = y[idx]

            zmin, zmax = np.percentile(z_s, [1.0, 99.0])
            zrange = float(max(zmax - zmin, 1e-6))
            w_min = 0.1
            w_max = min(300.0, 220.0 / zrange)
            if not np.isfinite(w_max) or w_max <= w_min:
                continue

            grid_n = 80
            w_grid = np.linspace(w_min, w_max, grid_n, dtype=np.float64)
            best_ws = []

            # coarse
            for w in w_grid:
                A = _build_design(z_s, float(w), d_trig, d_const, include_cos)
                coef = _ridge_solve(A, y_s, lam=1e-10)
                pred = A @ coef
                mse = float(np.mean((pred - y_s) ** 2))
                if np.isfinite(mse):
                    best_ws.append((mse, float(w)))

            if not best_ws:
                continue

            best_ws.sort(key=lambda t: t[0])
            top = best_ws[:2]
            step = (w_max - w_min) / max(grid_n - 1, 1)

            # refine
            refine_list = []
            for _, w0 in top:
                a = max(w_min, w0 - 6.0 * step)
                b = min(w_max, w0 + 6.0 * step)
                if b <= a:
                    continue
                ww = np.linspace(a, b, 40, dtype=np.float64)
                for w in ww:
                    A = _build_design(z_s, float(w), d_trig, d_const, include_cos)
                    coef = _ridge_solve(A, y_s, lam=1e-10)
                    pred = A @ coef
                    mse = float(np.mean((pred - y_s) ** 2))
                    if np.isfinite(mse):
                        refine_list.append((mse, float(w)))

            if refine_list:
                refine_list.sort(key=lambda t: t[0])
                w_best = refine_list[0][1]
            else:
                w_best = best_ws[0][1]

            # full fit on all data
            A_full = _build_design(z, w_best, d_trig, d_const, include_cos)
            coef_full = _ridge_solve(A_full, y, lam=1e-10)

            # term kinds for pruning and constant index
            term_kinds = []
            for k in range(d_trig + 1):
                term_kinds.append(("sin", k))
            if include_cos:
                for k in range(d_trig + 1):
                    term_kinds.append(("cos", k))
            for k in range(d_const + 1):
                term_kinds.append(("poly", k))

            keep_const_idx = (d_trig + 1) + (d_trig + 1 if include_cos else 0) + 0  # poly k=0
            coef_pruned, mse_full = _prune_refit(
                A_full, y, coef_full, term_kinds, y_rms=y_rms, keep_const_idx=keep_const_idx
            )

            # build expression with stronger threshold to keep it compact
            expr = _build_expression(z_str, w_best, d_trig, d_const, include_cos, coef_pruned, tol=1e-10 * y_rms)
            if expr == "0":
                continue

            comp = _sympy_complexity(expr)
            if comp is None:
                comp = 10_000

            # objective trades off MSE and complexity mildly
            obj = mse_full + (1e-4 * y_var) * float(comp)

            pred_full = A_full @ coef_pruned
            if not np.all(np.isfinite(pred_full)):
                continue

            candidate = {
                "expression": expr,
                "predictions": pred_full,
                "mse": float(mse_full),
                "complexity": int(comp),
                "objective": float(obj),
            }

            if best is None or candidate["objective"] < best["objective"]:
                best = candidate

        if best is None:
            a, b, c = coef_lin
            expr = _sum_parts([f"{_fmt(float(a))}*x1", f"{_fmt(float(b))}*x2", f"{_fmt(float(c))}"])
            comp = _sympy_complexity(expr)
            if comp is None:
                comp = 0
            return {
                "expression": expr,
                "predictions": pred_lin.tolist(),
                "details": {"mse": mse_lin, "complexity": int(comp)},
            }

        return {
            "expression": best["expression"],
            "predictions": best["predictions"].tolist(),
            "details": {"mse": best["mse"], "complexity": best["complexity"], "baseline_mse": mse_lin},
        }