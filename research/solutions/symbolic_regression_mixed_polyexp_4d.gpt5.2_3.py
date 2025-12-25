import numpy as np

def _fmt_float(x: float) -> str:
    if not np.isfinite(x):
        return "0.0"
    if abs(x) < 1e-15:
        return "0.0"
    s = format(float(x), ".12g")
    return s

def _build_monomials(X: np.ndarray, max_degree: int = 3):
    n, d = X.shape
    assert d == 4
    x1 = X[:, 0]
    x2 = X[:, 1]
    x3 = X[:, 2]
    x4 = X[:, 3]

    xs = [x1, x2, x3, x4]
    varnames = ["x1", "x2", "x3", "x4"]

    # Precompute powers for each variable up to max_degree
    pow_cache = []
    for i in range(4):
        pows = [np.ones(n, dtype=np.float64)]
        for k in range(1, max_degree + 1):
            pows.append(pows[-1] * xs[i])
        pow_cache.append(pows)

    exps = []
    exprs = []
    cols = []

    def expr_from_exp(e):
        parts = []
        for vi, pi in enumerate(e):
            if pi == 0:
                continue
            vn = varnames[vi]
            if pi == 1:
                parts.append(vn)
            else:
                parts.append(f"{vn}**{pi}")
        if not parts:
            return "1"
        return "*".join(parts)

    # Generate all monomials up to total degree max_degree (including constant)
    for a in range(max_degree + 1):
        for b in range(max_degree + 1 - a):
            for c in range(max_degree + 1 - a - b):
                for dd in range(max_degree + 1 - a - b - c):
                    deg = a + b + c + dd
                    if deg > max_degree:
                        continue
                    e = (a, b, c, dd)
                    exps.append(e)
                    exprs.append(expr_from_exp(e))
                    col = pow_cache[0][a] * pow_cache[1][b] * pow_cache[2][c] * pow_cache[3][dd]
                    cols.append(col)

    A = np.column_stack(cols).astype(np.float64, copy=False)
    return A, exprs, exps

def _ridge_solve(D: np.ndarray, y: np.ndarray, lam: float = 1e-10):
    # Solve (D^T D + lam I) beta = D^T y
    DtD = D.T @ D
    p = DtD.shape[0]
    DtD.flat[::p + 1] += lam
    Dty = D.T @ y
    try:
        beta = np.linalg.solve(DtD, Dty)
    except np.linalg.LinAlgError:
        beta, *_ = np.linalg.lstsq(D, y, rcond=None)
    return beta

def _omp_select(D: np.ndarray, y: np.ndarray, max_terms: int = 10, corr_tol: float = 1e-14):
    n, m = D.shape
    norms = np.linalg.norm(D, axis=0)
    valid = norms > 1e-14
    if not np.any(valid):
        return np.zeros(m, dtype=np.float64), [], float(np.mean((y - y.mean()) ** 2))

    idx_map = np.nonzero(valid)[0]
    Dv = D[:, valid]
    norms_v = norms[valid]
    Dn = Dv / norms_v

    selected = []
    selected_set = set()
    residual = y.copy()
    coef_sel = np.zeros(0, dtype=np.float64)

    for _ in range(max_terms):
        corr = Dn.T @ residual
        j = int(np.argmax(np.abs(corr)))
        if abs(corr[j]) < corr_tol:
            break
        col_idx = int(idx_map[j])
        if col_idx in selected_set:
            break
        selected.append(col_idx)
        selected_set.add(col_idx)

        Ds = D[:, selected]
        coef_sel = _ridge_solve(Ds, y, lam=1e-10)
        residual = y - Ds @ coef_sel

        if len(selected) >= max_terms:
            break

    coef = np.zeros(m, dtype=np.float64)
    if selected:
        coef[np.array(selected, dtype=int)] = coef_sel
        pred = D[:, selected] @ coef_sel
        mse = float(np.mean((y - pred) ** 2))
    else:
        mse = float(np.mean((y - y.mean()) ** 2))
    return coef, selected, mse

def _monomial_ops(exp_tuple):
    # Approx binary ops for monomial itself (excluding coefficient mult)
    power_ops = sum(1 for p in exp_tuple if p >= 2)
    factors = sum(1 for p in exp_tuple if p >= 1)
    mult_ops = max(factors - 1, 0)
    return power_ops + mult_ops

def _exp_arg_ops(weights):
    terms = [(i, w) for i, w in enumerate(weights) if w > 0.0]
    if not terms:
        return 0
    add_ops = max(len(terms) - 1, 0)
    ops = add_ops
    for _, w in terms:
        # x**2 -> power op
        ops += 1
        # w*x**2 -> multiplication if w != 1
        if abs(w - 1.0) > 1e-12:
            ops += 1
    return ops

def _model_complexity(selected_cols, mA, weights, monomial_exps):
    # We assume expression rendered as:
    # poly0 + poly1*exp(-arg)  (poly0 or poly1 may be absent)
    k0 = 0
    k1 = 0
    bin_ops_poly0 = 0
    bin_ops_poly1 = 0

    for j in selected_cols:
        if j < mA:
            k0 += 1
            e = monomial_exps[j]
            ops = _monomial_ops(e)
            if e != (0, 0, 0, 0):
                ops += 1  # coefficient multiplication
            bin_ops_poly0 += ops
        else:
            k1 += 1
            e = monomial_exps[j - mA]
            ops = _monomial_ops(e)
            if e != (0, 0, 0, 0):
                ops += 1  # coefficient multiplication
            bin_ops_poly1 += ops

    if k0 > 0:
        bin_ops_poly0 += (k0 - 1)  # additions
    if k1 > 0:
        bin_ops_poly1 += (k1 - 1)  # additions

    binary_ops = bin_ops_poly0 + bin_ops_poly1
    unary_ops = 0

    use_exp = (k1 > 0) and any(w > 0.0 for w in weights)
    if use_exp:
        unary_ops += 1  # exp
        binary_ops += _exp_arg_ops(weights)
        binary_ops += 1  # poly1 * exp
    if k0 > 0 and use_exp:
        binary_ops += 1  # poly0 + (poly1*exp)

    C = 2 * binary_ops + unary_ops
    return int(C)

def _build_poly_str(coefs, exprs, coef_tol=0.0):
    # Build sum of terms; returns ("0.0" if empty)
    terms = []
    for c, e in zip(coefs, exprs):
        if not np.isfinite(c):
            continue
        if abs(c) <= coef_tol:
            continue
        terms.append((float(c), e))
    if not terms:
        return "0.0", 0

    # Sort by descending abs coefficient for readability
    terms.sort(key=lambda t: -abs(t[0]))

    out = []
    n_terms = 0
    for c, e in terms:
        if abs(c) <= coef_tol:
            continue
        n_terms += 1
        sign = "-" if c < 0 else "+"
        ac = abs(c)

        if e == "1":
            tstr = _fmt_float(ac)
        else:
            if abs(ac - 1.0) < 1e-12:
                tstr = e
            else:
                tstr = f"{_fmt_float(ac)}*{e}"

        out.append((sign, tstr))

    if not out:
        return "0.0", 0

    first_sign, first_term = out[0]
    if first_sign == "-":
        s = "-" + first_term
    else:
        s = first_term

    for sign, tstr in out[1:]:
        s += f" {sign} {tstr}"
    return s, n_terms

def _build_exp_str(weights):
    parts = []
    for i, w in enumerate(weights):
        if w <= 0.0:
            continue
        v = f"x{i+1}**2"
        if abs(w - 1.0) < 1e-12:
            parts.append(v)
        else:
            parts.append(f"{_fmt_float(w)}*{v}")
    if not parts:
        return None
    arg = " + ".join(parts)
    return f"exp(-({arg}))"

def _compute_E(X, weights):
    if not any(w > 0.0 for w in weights):
        return None
    x1 = X[:, 0]
    x2 = X[:, 1]
    x3 = X[:, 2]
    x4 = X[:, 3]
    arg = np.zeros(X.shape[0], dtype=np.float64)
    ws = weights
    if ws[0] > 0.0:
        arg += ws[0] * x1 * x1
    if ws[1] > 0.0:
        arg += ws[1] * x2 * x2
    if ws[2] > 0.0:
        arg += ws[2] * x3 * x3
    if ws[3] > 0.0:
        arg += ws[3] * x4 * x4
    return np.exp(-arg)

def _generate_weight_configs(rng):
    ks = [0.25, 0.5, 1.0, 2.0]
    configs = []

    # None
    configs.append((0.0, 0.0, 0.0, 0.0))

    # All vars same
    for k in ks:
        configs.append((k, k, k, k))

    # Single var
    for i in range(4):
        for k in ks:
            w = [0.0, 0.0, 0.0, 0.0]
            w[i] = k
            configs.append(tuple(w))

    # Pairs
    pairs = [(0, 1), (0, 2), (0, 3), (1, 2), (1, 3), (2, 3)]
    for (i, j) in pairs:
        for k in ks:
            w = [0.0, 0.0, 0.0, 0.0]
            w[i] = k
            w[j] = k
            configs.append(tuple(w))

    # Triples
    triples = [(0, 1, 2), (0, 1, 3), (0, 2, 3), (1, 2, 3)]
    for (i, j, kidx) in triples:
        for k in ks:
            w = [0.0, 0.0, 0.0, 0.0]
            w[i] = k
            w[j] = k
            w[kidx] = k
            configs.append(tuple(w))

    # Random combos from a small grid
    grid = [0.0, 0.5, 1.0, 2.0]
    seen = set(configs)
    for _ in range(48):
        w = tuple(float(rng.choice(grid)) for _ in range(4))
        if w == (0.0, 0.0, 0.0, 0.0):
            continue
        if w in seen:
            continue
        seen.add(w)
        configs.append(w)

    # Deduplicate while preserving order
    out = []
    seen = set()
    for w in configs:
        if w in seen:
            continue
        seen.add(w)
        out.append(w)
    return out

class Solution:
    def __init__(self, **kwargs):
        self.random_state = int(kwargs.get("random_state", 42))

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        X = np.asarray(X, dtype=np.float64)
        y = np.asarray(y, dtype=np.float64).reshape(-1)
        n = X.shape[0]
        if n == 0:
            return {"expression": "0.0", "predictions": [], "details": {"complexity": 0}}

        y_var = float(np.var(y))
        if not np.isfinite(y_var) or y_var < 1e-30:
            const = float(np.mean(y[np.isfinite(y)]) if np.any(np.isfinite(y)) else 0.0)
            expr = _fmt_float(const)
            preds = np.full(n, const, dtype=np.float64)
            return {"expression": expr, "predictions": preds.tolist(), "details": {"complexity": 0}}

        rng = np.random.default_rng(self.random_state)

        A, mon_exprs, mon_exps = _build_monomials(X, max_degree=3)
        mA = A.shape[1]

        # Subsample for model selection
        n_sub = min(n, 3000)
        if n_sub < n:
            sub_idx = rng.choice(n, size=n_sub, replace=False)
        else:
            sub_idx = np.arange(n)
        Xs = X[sub_idx]
        ys = y[sub_idx]
        As = A[sub_idx]

        # Train/val split
        if n_sub >= 80:
            perm = rng.permutation(n_sub)
            n_tr = int(0.7 * n_sub)
            tr = perm[:n_tr]
            va = perm[n_tr:]
        else:
            tr = np.arange(n_sub)
            va = np.arange(n_sub)

        Atr = As[tr]
        ytr = ys[tr]
        Ava = As[va]
        yva = ys[va]

        weight_configs = _generate_weight_configs(rng)

        best = None  # (objective, mse_val, weights, max_terms, coef_full, selected, complexity)
        max_terms_list = [6, 10]

        for weights in weight_configs:
            weights = tuple(float(w) for w in weights)
            has_exp = any(w > 0.0 for w in weights)

            if has_exp:
                Etr = _compute_E(Xs[tr], weights)
                Eva = _compute_E(Xs[va], weights)
                if Etr is None or Eva is None:
                    continue
                Dtr = np.hstack([Atr, Atr * Etr[:, None]])
                Dva = np.hstack([Ava, Ava * Eva[:, None]])
            else:
                Dtr = Atr
                Dva = Ava

            for max_terms in max_terms_list:
                coef, selected, _ = _omp_select(Dtr, ytr, max_terms=max_terms, corr_tol=1e-14)
                if not selected:
                    pred_va = np.full_like(yva, float(np.mean(ytr)))
                    mse_va = float(np.mean((yva - pred_va) ** 2))
                    C = 0
                else:
                    Ds_va = Dva[:, selected]
                    pred_va = Ds_va @ coef[np.array(selected, dtype=int)]
                    mse_va = float(np.mean((yva - pred_va) ** 2))
                    C = _model_complexity(selected, mA, weights, mon_exps) if has_exp else _model_complexity(selected, mA, (0.0, 0.0, 0.0, 0.0), mon_exps)

                if not np.isfinite(mse_va):
                    continue

                # Objective: primarily mse, tie-break by complexity
                obj = mse_va * (1.0 + 5e-4 * max(C - 60, 0)) + 1e-10 * C
                cand = (obj, mse_va, weights, max_terms, coef, selected, C, has_exp)
                if best is None or cand[0] < best[0] or (cand[0] == best[0] and cand[6] < best[6]):
                    best = cand

        if best is None:
            const = float(np.mean(y))
            expr = _fmt_float(const)
            preds = np.full(n, const, dtype=np.float64)
            return {"expression": expr, "predictions": preds.tolist(), "details": {"complexity": 0}}

        _, _, weights_best, max_terms_best, _, _, _, has_exp_best = best

        # Final fit on full data
        if has_exp_best and any(w > 0.0 for w in weights_best):
            E = _compute_E(X, weights_best)
            D = np.hstack([A, A * E[:, None]])
        else:
            E = None
            D = A

        coef_full, selected_full, _ = _omp_select(D, y, max_terms=max_terms_best, corr_tol=1e-14)
        if not selected_full:
            const = float(np.mean(y))
            expr = _fmt_float(const)
            preds = np.full(n, const, dtype=np.float64)
            return {"expression": expr, "predictions": preds.tolist(), "details": {"complexity": 0}}

        # Optional pruning of tiny coefficients
        sel = np.array(selected_full, dtype=int)
        csel = coef_full[sel]
        max_abs = float(np.max(np.abs(csel))) if csel.size else 0.0
        thresh = max(1e-12, 1e-10 * max_abs)
        keep_mask = np.abs(csel) > thresh
        sel = sel[keep_mask]
        if sel.size == 0:
            const = float(np.mean(y))
            expr = _fmt_float(const)
            preds = np.full(n, const, dtype=np.float64)
            return {"expression": expr, "predictions": preds.tolist(), "details": {"complexity": 0}}

        # Refit on kept columns for best coefficients
        Ds = D[:, sel]
        beta = _ridge_solve(Ds, y, lam=1e-12)

        # Build split coefficients for poly0 and poly1
        poly0_coef = np.zeros(mA, dtype=np.float64)
        poly1_coef = np.zeros(mA, dtype=np.float64)

        if has_exp_best and any(w > 0.0 for w in weights_best):
            for j, b in zip(sel, beta):
                if j < mA:
                    poly0_coef[j] += b
                else:
                    poly1_coef[j - mA] += b
        else:
            for j, b in zip(sel, beta):
                poly0_coef[j] += b

        # Prune again for string building
        scale0 = float(np.max(np.abs(poly0_coef))) if np.any(poly0_coef) else 0.0
        scale1 = float(np.max(np.abs(poly1_coef))) if np.any(poly1_coef) else 0.0
        tol0 = max(1e-14, 1e-12 * scale0)
        tol1 = max(1e-14, 1e-12 * scale1)

        poly0_str, k0 = _build_poly_str(poly0_coef, mon_exprs, coef_tol=tol0)
        poly1_str, k1 = _build_poly_str(poly1_coef, mon_exprs, coef_tol=tol1)

        exp_str = _build_exp_str(weights_best) if (k1 > 0 and any(w > 0.0 for w in weights_best)) else None

        if exp_str is not None and k1 > 0:
            damped = f"({poly1_str})*{exp_str}"
            if poly0_str != "0.0" and k0 > 0:
                expression = f"({poly0_str}) + {damped}"
            else:
                expression = damped
        else:
            expression = f"({poly0_str})" if poly0_str != "0.0" else "0.0"

        # Compute predictions
        pred = A @ poly0_coef
        if exp_str is not None and k1 > 0 and E is not None:
            pred = pred + (A @ poly1_coef) * E

        # Complexity estimate
        if exp_str is not None and k1 > 0:
            selected_for_complexity = []
            # approximate selected cols after pruning
            nz0 = np.nonzero(np.abs(poly0_coef) > tol0)[0]
            nz1 = np.nonzero(np.abs(poly1_coef) > tol1)[0]
            selected_for_complexity.extend(nz0.tolist())
            selected_for_complexity.extend((nz1 + mA).tolist())
            C = _model_complexity(selected_for_complexity, mA, weights_best, mon_exps)
        else:
            nz0 = np.nonzero(np.abs(poly0_coef) > tol0)[0]
            C = _model_complexity(nz0.tolist(), mA, (0.0, 0.0, 0.0, 0.0), mon_exps)

        return {
            "expression": expression,
            "predictions": pred.tolist(),
            "details": {"complexity": int(C)},
        }