import numpy as np
import sympy as sp


def _generate_monomial_exponents(nvars: int, max_degree: int):
    exps = []
    for total in range(max_degree + 1):
        if nvars == 1:
            exps.append((total,))
            continue
        if nvars == 4:
            for p1 in range(total + 1):
                rem1 = total - p1
                for p2 in range(rem1 + 1):
                    rem2 = rem1 - p2
                    for p3 in range(rem2 + 1):
                        p4 = rem2 - p3
                        exps.append((p1, p2, p3, p4))
        else:
            # generic recursion for completeness
            def rec(prefix, left, vars_left):
                if vars_left == 1:
                    exps.append(tuple(prefix + [left]))
                    return
                for k in range(left + 1):
                    rec(prefix + [k], left - k, vars_left - 1)

            rec([], total, nvars)
    return exps


def _design_matrix_monomials(X, exps, max_degree):
    n = X.shape[0]
    xcols = [X[:, i].astype(np.float64, copy=False) for i in range(X.shape[1])]
    powers = []
    for xi in xcols:
        pows = [np.ones(n, dtype=np.float64)]
        if max_degree >= 1:
            pows.append(xi)
        for k in range(2, max_degree + 1):
            pows.append(pows[-1] * xi)
        powers.append(pows)

    A = np.empty((n, len(exps)), dtype=np.float64)
    for j, (p1, p2, p3, p4) in enumerate(exps):
        col = powers[0][p1]
        col = col * powers[1][p2]
        col = col * powers[2][p3]
        col = col * powers[3][p4]
        A[:, j] = col
    return A


def _ridge_fit(A, y, ridge=1e-12):
    A = np.asarray(A, dtype=np.float64)
    y = np.asarray(y, dtype=np.float64)
    m = A.shape[1]
    if m == 0:
        return np.zeros((0,), dtype=np.float64)

    scale = np.sqrt(np.mean(A * A, axis=0)) + 1e-18
    As = A / scale
    G = As.T @ As
    lam = ridge * (np.trace(G) / m + 1e-18)
    G.flat[:: m + 1] += lam
    rhs = As.T @ y
    try:
        bs = np.linalg.solve(G, rhs)
    except np.linalg.LinAlgError:
        bs, _, _, _ = np.linalg.lstsq(As, y, rcond=None)
    b = bs / scale
    return b


def _select_and_refit(A, y, max_terms=18, frac_grid=None, ridge=1e-12):
    if frac_grid is None:
        frac_grid = (0.0, 1e-12, 1e-10, 1e-8, 1e-6, 1e-4, 1e-3, 1e-2, 5e-2, 1e-1, 2e-1)

    A = np.asarray(A, dtype=np.float64)
    y = np.asarray(y, dtype=np.float64)
    n, m = A.shape
    if m == 0:
        pred = np.full(n, float(np.mean(y)), dtype=np.float64)
        mse = float(np.mean((y - pred) ** 2))
        return {
            "idx": np.zeros((0,), dtype=np.int64),
            "coef": np.zeros((0,), dtype=np.float64),
            "pred": pred,
            "mse": mse,
            "nnz": 0,
        }

    full_coef = _ridge_fit(A, y, ridge=ridge)
    abs_full = np.abs(full_coef)
    max_abs = float(np.max(abs_full)) if m > 0 else 0.0

    best = None
    for frac in frac_grid:
        thr = max(1e-14, frac * max_abs)
        idx = np.where(abs_full >= thr)[0]
        if idx.size == 0:
            # constant-only via best constant in least squares sense:
            pred = np.full(n, float(np.mean(y)), dtype=np.float64)
            mse = float(np.mean((y - pred) ** 2))
            nnz = 0
            obj = mse * 1.02
            if best is None or obj < best["obj"]:
                best = {
                    "idx": idx,
                    "coef": np.zeros((0,), dtype=np.float64),
                    "pred": pred,
                    "mse": mse,
                    "nnz": nnz,
                    "obj": obj,
                }
            continue

        if idx.size > max_terms:
            top = np.argpartition(abs_full, -max_terms)[-max_terms:]
            idx = np.sort(top)

        Asub = A[:, idx]
        coef_sub = _ridge_fit(Asub, y, ridge=ridge)
        pred = Asub @ coef_sub
        mse = float(np.mean((y - pred) ** 2))
        nnz = int(idx.size)
        obj = mse * (1.0 + 0.002 * nnz)
        if best is None or obj < best["obj"]:
            best = {
                "idx": idx,
                "coef": coef_sub,
                "pred": pred,
                "mse": mse,
                "nnz": nnz,
                "obj": obj,
            }

    return {k: v for k, v in best.items() if k != "obj"}


def _sympy_poly_from_selection(coef_sub, idx, exps, symbols, float_prec=16):
    x1, x2, x3, x4 = symbols
    poly = sp.Integer(0)
    for c, j in zip(coef_sub, idx):
        if not np.isfinite(c):
            continue
        csp = sp.Float(float(c), float_prec)
        p1, p2, p3, p4 = exps[int(j)]
        term = csp
        if p1:
            term *= x1 ** int(p1)
        if p2:
            term *= x2 ** int(p2)
        if p3:
            term *= x3 ** int(p3)
        if p4:
            term *= x4 ** int(p4)
        poly += term
    return poly


def _sympy_S(symbols, S_name):
    x1, x2, x3, x4 = symbols
    if S_name == "all":
        return x1**2 + x2**2 + x3**2 + x4**2
    if S_name == "12":
        return x1**2 + x2**2
    if S_name == "34":
        return x3**2 + x4**2
    if S_name == "1":
        return x1**2
    if S_name == "2":
        return x2**2
    if S_name == "3":
        return x3**2
    if S_name == "4":
        return x4**2
    return x1**2 + x2**2 + x3**2 + x4**2


def _complexity_sympy(expr):
    unary_funcs = (sp.sin, sp.cos, sp.exp, sp.log)

    binary_ops = 0
    unary_ops = 0

    def rec(e):
        nonlocal binary_ops, unary_ops
        if isinstance(e, sp.Add):
            args = e.args
            if len(args) > 1:
                binary_ops += len(args) - 1
            for a in args:
                rec(a)
        elif isinstance(e, sp.Mul):
            args = e.args
            if len(args) > 1:
                binary_ops += len(args) - 1
            for a in args:
                rec(a)
        elif isinstance(e, sp.Pow):
            binary_ops += 1
            rec(e.base)
            rec(e.exp)
        else:
            f = getattr(e, "func", None)
            if f in unary_funcs:
                unary_ops += 1
                for a in e.args:
                    rec(a)
            else:
                for a in getattr(e, "args", ()):
                    rec(a)

    rec(expr)
    return int(2 * binary_ops + unary_ops)


class Solution:
    def __init__(self, **kwargs):
        self.max_degree = int(kwargs.get("max_degree", 4))
        self.max_terms = int(kwargs.get("max_terms", 18))
        self.ridge = float(kwargs.get("ridge", 1e-12))

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        X = np.asarray(X, dtype=np.float64)
        y = np.asarray(y, dtype=np.float64)
        n, d = X.shape
        if d != 4:
            raise ValueError("Expected X with shape (n, 4).")

        x1v, x2v, x3v, x4v = X[:, 0], X[:, 1], X[:, 2], X[:, 3]

        max_deg = self.max_degree
        exps = _generate_monomial_exponents(4, max_deg)
        A_poly = _design_matrix_monomials(X, exps, max_deg)

        # Precompute S variants and grids
        S_defs = {
            "all": x1v * x1v + x2v * x2v + x3v * x3v + x4v * x4v,
            "12": x1v * x1v + x2v * x2v,
            "34": x3v * x3v + x4v * x4v,
            "1": x1v * x1v,
            "2": x2v * x2v,
            "3": x3v * x3v,
            "4": x4v * x4v,
        }

        # Choose a grid based on typical scale of S_all
        S_all = S_defs["all"]
        s_med = float(np.median(S_all)) if n > 0 else 1.0
        s_med = max(s_med, 1e-6)
        # Want exp(-a*S) to vary; if S around s_med, exp(-a*s_med) in [0.05, 0.95]
        # => a in [ -ln(0.95)/s_med, -ln(0.05)/s_med ]
        a_min = float(-np.log(0.95) / s_med)
        a_max = float(-np.log(0.05) / s_med)
        a_min = max(a_min, 1e-3)
        a_max = min(max(a_max, a_min * 50.0), 20.0)
        a_grid = np.geomspace(a_min, a_max, num=8).tolist()
        # include common values if within range
        for v in (0.1, 0.2, 0.5, 1.0, 2.0):
            if v >= a_min * 0.8 and v <= a_max * 1.2:
                a_grid.append(v)
        a_grid = sorted(set(float(a) for a in a_grid))

        best_model = None

        def consider(model):
            nonlocal best_model
            if best_model is None:
                best_model = model
                return
            # Primary: MSE. Secondary: fewer terms. Tertiary: fewer exp terms.
            if model["mse"] < best_model["mse"] * 0.999:
                best_model = model
                return
            if model["mse"] <= best_model["mse"] * 1.0005:
                if model.get("nnz_total", 10**9) < best_model.get("nnz_total", 10**9):
                    best_model = model
                    return
                if model.get("exp_terms", 0) < best_model.get("exp_terms", 0):
                    best_model = model
                    return

        # Model 0: constant
        ymean = float(np.mean(y)) if n > 0 else 0.0
        pred0 = np.full(n, ymean, dtype=np.float64)
        mse0 = float(np.mean((y - pred0) ** 2)) if n > 0 else 0.0
        consider({
            "type": "const",
            "mse": mse0,
            "pred": pred0,
            "params": {"c": ymean},
            "nnz_total": 1,
            "exp_terms": 0,
        })

        # Model A: polynomial
        selA = _select_and_refit(A_poly, y, max_terms=self.max_terms, ridge=self.ridge)
        consider({
            "type": "poly",
            "mse": selA["mse"],
            "pred": selA["pred"],
            "params": {"idx": selA["idx"], "coef": selA["coef"]},
            "nnz_total": int(selA["nnz"]),
            "exp_terms": 0,
        })

        # Model B/C: exp-damped polynomial and polynomial + exp-damped polynomial
        for S_name, S_vals in S_defs.items():
            for a in a_grid:
                E = np.exp(-a * S_vals)

                # exp * poly
                A_exp = A_poly * E[:, None]
                selB = _select_and_refit(A_exp, y, max_terms=self.max_terms, ridge=self.ridge)
                consider({
                    "type": "exp_poly",
                    "mse": selB["mse"],
                    "pred": selB["pred"],
                    "params": {"S_name": S_name, "a": float(a), "idx": selB["idx"], "coef": selB["coef"]},
                    "nnz_total": int(selB["nnz"]),
                    "exp_terms": 1,
                })

                # poly + exp*poly
                A_mix = np.concatenate([A_poly, A_exp], axis=1)
                selC = _select_and_refit(A_mix, y, max_terms=self.max_terms, ridge=self.ridge)
                consider({
                    "type": "poly_plus_exp",
                    "mse": selC["mse"],
                    "pred": selC["pred"],
                    "params": {"S_name": S_name, "a": float(a), "idx": selC["idx"], "coef": selC["coef"], "m": A_poly.shape[1]},
                    "nnz_total": int(selC["nnz"]),
                    "exp_terms": 1,
                })

        # Model D: sum of two exp-damped polynomials (only for S=all to limit search)
        S_name = "all"
        S_vals = S_defs[S_name]
        # smaller grid for pairs
        if len(a_grid) > 8:
            a_grid_pair = a_grid[::2]
        else:
            a_grid_pair = a_grid[:]
        if len(a_grid_pair) >= 2:
            for i in range(len(a_grid_pair)):
                for j in range(i + 1, len(a_grid_pair)):
                    a1 = float(a_grid_pair[i])
                    a2 = float(a_grid_pair[j])
                    E1 = np.exp(-a1 * S_vals)
                    E2 = np.exp(-a2 * S_vals)
                    A1 = A_poly * E1[:, None]
                    A2 = A_poly * E2[:, None]
                    A2mix = np.concatenate([A1, A2], axis=1)
                    selD = _select_and_refit(A2mix, y, max_terms=self.max_terms, ridge=self.ridge)
                    consider({
                        "type": "exp_plus_exp",
                        "mse": selD["mse"],
                        "pred": selD["pred"],
                        "params": {"S_name": S_name, "a1": a1, "a2": a2, "idx": selD["idx"], "coef": selD["coef"], "m": A_poly.shape[1]},
                        "nnz_total": int(selD["nnz"]),
                        "exp_terms": 2,
                    })

        # Build final sympy expression
        x1, x2, x3, x4 = sp.symbols("x1 x2 x3 x4")
        symbols = (x1, x2, x3, x4)

        model_type = best_model["type"]
        params = best_model["params"]
        pred = best_model["pred"]

        if model_type == "const":
            expr = sp.Float(float(params["c"]), 16)

        elif model_type == "poly":
            expr = _sympy_poly_from_selection(params["coef"], params["idx"], exps, symbols)

        elif model_type == "exp_poly":
            poly = _sympy_poly_from_selection(params["coef"], params["idx"], exps, symbols)
            Ssym = _sympy_S(symbols, params["S_name"])
            a = sp.Float(float(params["a"]), 16)
            expr = sp.exp(-a * Ssym) * poly

        elif model_type == "poly_plus_exp":
            m0 = int(params["m"])
            idx = params["idx"]
            coef = params["coef"]
            left_mask = idx < m0
            right_mask = idx >= m0

            poly1 = _sympy_poly_from_selection(coef[left_mask], idx[left_mask], exps, symbols)
            idx2 = idx[right_mask] - m0
            poly2 = _sympy_poly_from_selection(coef[right_mask], idx2, exps, symbols)

            Ssym = _sympy_S(symbols, params["S_name"])
            a = sp.Float(float(params["a"]), 16)
            expr = poly1 + sp.exp(-a * Ssym) * poly2

        elif model_type == "exp_plus_exp":
            m0 = int(params["m"])
            idx = params["idx"]
            coef = params["coef"]
            left_mask = idx < m0
            right_mask = idx >= m0

            poly1 = _sympy_poly_from_selection(coef[left_mask], idx[left_mask], exps, symbols)
            idx2 = idx[right_mask] - m0
            poly2 = _sympy_poly_from_selection(coef[right_mask], idx2, exps, symbols)

            Ssym = _sympy_S(symbols, params["S_name"])
            a1 = sp.Float(float(params["a1"]), 16)
            a2 = sp.Float(float(params["a2"]), 16)
            expr = sp.exp(-a1 * Ssym) * poly1 + sp.exp(-a2 * Ssym) * poly2

        else:
            expr = sp.Float(ymean, 16)

        # Minor cleanup
        try:
            expr = sp.nsimplify(expr, rational=False, constants=[])
        except Exception:
            pass

        expr_str = sp.sstr(expr)
        complexity = _complexity_sympy(expr)

        details = {
            "mse": float(best_model["mse"]),
            "model_type": model_type,
            "complexity": int(complexity),
            "nnz_total": int(best_model.get("nnz_total", 0)),
            "exp_terms": int(best_model.get("exp_terms", 0)),
            "max_degree": int(self.max_degree),
        }

        return {
            "expression": expr_str,
            "predictions": pred.tolist() if pred is not None else None,
            "details": details,
        }