import numpy as np
from itertools import product


def _safe_exp(z):
    return np.exp(np.clip(z, -60.0, 60.0))


def _generate_monomials(max_degree=4):
    exps = []
    for e1 in range(max_degree + 1):
        for e2 in range(max_degree + 1 - e1):
            for e3 in range(max_degree + 1 - e1 - e2):
                e4_max = max_degree - (e1 + e2 + e3)
                for e4 in range(e4_max + 1):
                    deg = e1 + e2 + e3 + e4
                    if deg <= max_degree:
                        exps.append((e1, e2, e3, e4))
    exps.sort(key=lambda t: (sum(t), t))
    return exps


def _monom_expr(e):
    e1, e2, e3, e4 = e
    parts = []
    if e1:
        parts.append("x1" if e1 == 1 else f"x1**{e1}")
    if e2:
        parts.append("x2" if e2 == 1 else f"x2**{e2}")
    if e3:
        parts.append("x3" if e3 == 1 else f"x3**{e3}")
    if e4:
        parts.append("x4" if e4 == 1 else f"x4**{e4}")
    return "1" if not parts else "*".join(parts)


def _format_float(c):
    if not np.isfinite(c):
        return "0.0"
    if c == 0.0:
        return "0.0"
    return format(float(c), ".17g")


def _sum_linear_terms(terms):
    # terms: list of (coef, expr) where expr is a monomial-like string (no + inside) or "1"
    out = []
    first = True
    for coef, expr in terms:
        if not np.isfinite(coef):
            continue
        if abs(coef) < 1e-15:
            continue
        sign = "-" if coef < 0 else "+"
        a = abs(coef)

        if expr == "1":
            core = _format_float(a)
        else:
            if abs(a - 1.0) < 1e-15:
                core = expr
            else:
                core = f"{_format_float(a)}*{expr}"

        if first:
            if coef < 0:
                out.append(f"-{core}")
            else:
                out.append(core)
            first = False
        else:
            out.append(f"{sign}{core}")

    if not out:
        return "0.0"
    return "".join(out)


class Solution:
    def __init__(self, **kwargs):
        self.max_degree = int(kwargs.get("max_degree", 4))
        self.max_terms = int(kwargs.get("max_terms", 14))
        self.prune_tol = float(kwargs.get("prune_tol", 1e-6))

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        X = np.asarray(X, dtype=np.float64)
        y = np.asarray(y, dtype=np.float64).reshape(-1)
        n = X.shape[0]
        if n == 0:
            return {"expression": "0.0", "predictions": [], "details": {}}
        if X.ndim != 2 or X.shape[1] != 4:
            raise ValueError("X must have shape (n, 4).")

        x1 = X[:, 0]
        x2 = X[:, 1]
        x3 = X[:, 2]
        x4 = X[:, 3]

        # Precompute powers up to max_degree
        maxd = self.max_degree
        p1 = [np.ones_like(x1), x1]
        p2 = [np.ones_like(x2), x2]
        p3 = [np.ones_like(x3), x3]
        p4 = [np.ones_like(x4), x4]
        for k in range(2, maxd + 1):
            p1.append(p1[-1] * x1)
            p2.append(p2[-1] * x2)
            p3.append(p3[-1] * x3)
            p4.append(p4[-1] * x4)

        mon_exps = _generate_monomials(max_degree=maxd)
        m = len(mon_exps)

        Mon = np.empty((n, m), dtype=np.float64)
        mon_exprs = []
        for j, e in enumerate(mon_exps):
            e1, e2, e3, e4 = e
            Mon[:, j] = p1[e1] * p2[e2] * p3[e3] * p4[e4]
            mon_exprs.append(_monom_expr(e))

        # Damping functions
        r2_all = x1 * x1 + x2 * x2 + x3 * x3 + x4 * x4
        dampings = []
        dampings.append(("1", np.ones_like(y), "1"))
        dampings.append(("exp(-(x1**2+x2**2+x3**2+x4**2))", _safe_exp(-r2_all), "all"))
        dampings.append(("exp(-0.5*(x1**2+x2**2+x3**2+x4**2))", _safe_exp(-0.5 * r2_all), "half_all"))
        dampings.append(("exp(-2*(x1**2+x2**2+x3**2+x4**2))", _safe_exp(-2.0 * r2_all), "two_all"))
        r2_12 = x1 * x1 + x2 * x2
        r2_34 = x3 * x3 + x4 * x4
        dampings.append(("exp(-(x1**2+x2**2))", _safe_exp(-r2_12), "12"))
        dampings.append(("exp(-(x3**2+x4**2))", _safe_exp(-r2_34), "34"))
        dampings.append(("exp(-(x1**2))", _safe_exp(-(x1 * x1)), "x1sq"))
        dampings.append(("exp(-(x2**2))", _safe_exp(-(x2 * x2)), "x2sq"))
        dampings.append(("exp(-(x3**2))", _safe_exp(-(x3 * x3)), "x3sq"))
        dampings.append(("exp(-(x4**2))", _safe_exp(-(x4 * x4)), "x4sq"))
        dampings.append(("exp(-x4)", _safe_exp(-x4), "x4"))

        # Build candidate feature matrix Phi excluding intercept.
        # Exclude constant monomial for undamped ("1") to avoid duplication with intercept.
        cols = []
        desc = []  # (damp_expr, monom_expr)
        for damp_expr, damp_vals, damp_key in dampings:
            if damp_key == "1":
                start_j = 1  # skip monomial "1"
            else:
                start_j = 0
            block = Mon[:, start_j:] * damp_vals[:, None]
            cols.append(block)
            for j in range(start_j, m):
                desc.append((damp_expr, mon_exprs[j]))
        Phi = np.concatenate(cols, axis=1) if cols else np.empty((n, 0), dtype=np.float64)
        p = Phi.shape[1]

        # Remove near-constant/invalid columns
        col_mean = np.mean(Phi, axis=0) if p else np.array([], dtype=np.float64)
        Phi_c = Phi - col_mean
        norms = np.sqrt(np.sum(Phi_c * Phi_c, axis=0)) if p else np.array([], dtype=np.float64)
        keep = np.isfinite(norms) & (norms > 1e-12)
        if p:
            Phi = Phi[:, keep]
            Phi_c = Phi_c[:, keep]
            norms = norms[keep]
            desc = [d for d, k in zip(desc, keep.tolist()) if k]
        p = Phi.shape[1]

        # If nothing left, fall back to intercept
        if p == 0:
            c0 = float(np.mean(y))
            expr = _format_float(c0)
            preds = np.full(n, c0, dtype=np.float64)
            return {"expression": expr, "predictions": preds.tolist(), "details": {}}

        Phi_std = Phi_c / norms

        # OMP selection
        active = []
        used = np.zeros(p, dtype=bool)
        ones = np.ones((n, 1), dtype=np.float64)

        best_beta = None
        best_active = None
        best_mse = np.inf

        y_var = float(np.var(y)) + 1e-12
        target_improve = 1e-12 * y_var

        residual = y - np.mean(y)
        prev_rss = float(np.dot(residual, residual))

        max_terms = max(1, int(self.max_terms))
        for _ in range(max_terms):
            corr = np.abs(Phi_std.T @ residual)
            corr[used] = -1.0
            j = int(np.argmax(corr))
            if corr[j] <= 0.0 or not np.isfinite(corr[j]):
                break
            active.append(j)
            used[j] = True

            A = np.concatenate([ones, Phi[:, active]], axis=1)
            beta, _, _, _ = np.linalg.lstsq(A, y, rcond=None)
            pred = A @ beta
            residual = y - pred
            rss = float(np.dot(residual, residual))
            mse = rss / n

            if mse < best_mse:
                best_mse = mse
                best_beta = beta.copy()
                best_active = active.copy()

            if prev_rss - rss < target_improve:
                break
            prev_rss = rss

        if best_beta is None:
            c0 = float(np.mean(y))
            expr = _format_float(c0)
            preds = np.full(n, c0, dtype=np.float64)
            return {"expression": expr, "predictions": preds.tolist(), "details": {}}

        active = best_active
        beta = best_beta

        # Prune small coefficients (excluding intercept)
        scale = float(np.std(y)) + 1e-12
        tol = self.prune_tol * scale
        if len(active) > 0:
            keep_idx = [i for i, b in enumerate(beta[1:]) if abs(b) > tol and np.isfinite(b)]
            active2 = [active[i] for i in keep_idx]
        else:
            active2 = []

        A2 = np.concatenate([ones, Phi[:, active2]], axis=1)
        beta2, _, _, _ = np.linalg.lstsq(A2, y, rcond=None)
        pred2 = A2 @ beta2

        # Build expression with grouping by damping
        group = {}  # damp_expr -> list of (coef, monom_expr)
        # Add intercept as (coef, "1") under damp "1"
        group.setdefault("1", []).append((float(beta2[0]), "1"))

        for coef, col_idx in zip(beta2[1:], active2):
            damp_expr, mon_expr = desc[col_idx]
            group.setdefault(damp_expr, []).append((float(coef), mon_expr))

        # Construct final expression
        parts = []
        if "1" in group:
            poly = _sum_linear_terms(group["1"])
            if poly not in ("0.0", "0"):
                parts.append(poly)

        for damp_expr in sorted([k for k in group.keys() if k != "1"]):
            poly = _sum_linear_terms(group[damp_expr])
            if poly in ("0.0", "0"):
                continue
            if damp_expr == "1":
                parts.append(poly)
            else:
                parts.append(f"({poly})*{damp_expr}")

        expression = _sum_linear_terms([(1.0, "1")])  # placeholder, replaced below
        if not parts:
            expression = "0.0"
        else:
            expression = parts[0]
            for pstr in parts[1:]:
                if pstr.startswith("-"):
                    expression = f"{expression}{pstr}"
                else:
                    expression = f"{expression}+{pstr}"

        return {
            "expression": expression,
            "predictions": pred2.tolist(),
            "details": {}
        }