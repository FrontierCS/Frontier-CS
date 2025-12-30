import numpy as np
from dataclasses import dataclass
from typing import List, Tuple, Optional, Dict, Any


def _fmt_float(x: float) -> str:
    if not np.isfinite(x):
        return "0.0"
    if abs(x) < 1e-15:
        x = 0.0
    s = f"{x:.12g}"
    if s == "-0":
        s = "0"
    if s == "-0.0":
        s = "0.0"
    return s


def _gen_exponent_vectors(num_vars: int, degree: int):
    if num_vars == 1:
        yield (degree,)
        return
    for e in range(degree + 1):
        for rest in _gen_exponent_vectors(num_vars - 1, degree - e):
            yield (e,) + rest


def _monomial_expr_from_exps(exps: Tuple[int, int, int, int]) -> str:
    parts = []
    for i, e in enumerate(exps):
        if e == 0:
            continue
        v = f"x{i+1}"
        if e == 1:
            parts.append(v)
        else:
            parts.append(f"{v}**{e}")
    if not parts:
        return "1"
    return "*".join(parts)


def _build_monomials(X: np.ndarray, max_degree: int = 3):
    n, d = X.shape
    assert d == 4
    x = [X[:, i].astype(np.float64, copy=False) for i in range(4)]
    ones = np.ones(n, dtype=np.float64)

    powv = []
    for i in range(4):
        p = [ones, x[i]]
        p.append(x[i] * x[i])
        p.append(p[2] * x[i])
        powv.append(p)

    mon_vals: List[np.ndarray] = []
    mon_exprs: List[str] = []
    mon_degs: List[int] = []

    # degree 0..max_degree in fixed order
    for deg in range(max_degree + 1):
        for exps in _gen_exponent_vectors(4, deg):
            expr = _monomial_expr_from_exps(exps)
            v = ones
            for i, e in enumerate(exps):
                if e:
                    v = v * powv[i][e]
            mon_vals.append(v)
            mon_exprs.append(expr)
            mon_degs.append(deg)

    return mon_vals, mon_exprs, mon_degs


def _ridge_fit(Phi: np.ndarray, y: np.ndarray, lam: float) -> np.ndarray:
    # Column scaling for conditioning; return coefficients in original scale
    col_scale = np.sqrt(np.mean(Phi * Phi, axis=0)) + 1e-12
    Phi_s = Phi / col_scale
    if lam <= 0.0:
        c_s, _, _, _ = np.linalg.lstsq(Phi_s, y, rcond=None)
    else:
        G = Phi_s.T @ Phi_s
        b = Phi_s.T @ y
        m = G.shape[0]
        G.flat[:: m + 1] += lam
        c_s = np.linalg.solve(G, b)
    c = c_s / col_scale
    c[~np.isfinite(c)] = 0.0
    return c


def _bic(mse: float, n: int, k: int) -> float:
    return n * np.log(max(mse, 1e-24)) + k * np.log(max(n, 2))


def _select_sparse(
    Phi: np.ndarray,
    exprs: List[str],
    y: np.ndarray,
    lam: float,
    max_terms: int = 12
):
    n, m = Phi.shape
    c_full = _ridge_fit(Phi, y, lam)
    yhat_full = Phi @ c_full
    mse_full = float(np.mean((y - yhat_full) ** 2))

    abs_c = np.abs(c_full)
    maxabs = float(np.max(abs_c)) if m else 0.0
    if maxabs <= 0.0:
        # fallback constant
        c0 = float(np.mean(y))
        return np.array([c0], dtype=np.float64), ["1"], np.full(n, c0, dtype=np.float64)

    fracs = [0.0, 1e-8, 1e-7, 1e-6, 3e-6, 1e-5, 3e-5, 1e-4, 3e-4, 1e-3, 3e-3, 1e-2, 3e-2, 1e-1]
    best = {
        "bic": _bic(mse_full, n, int(np.count_nonzero(c_full))),
        "mse": mse_full,
        "c": c_full,
        "mask": np.ones(m, dtype=bool),
        "yhat": yhat_full,
    }

    for f in fracs:
        thr = f * maxabs
        mask = abs_c > thr
        k = int(np.count_nonzero(mask))
        if k == 0:
            # keep the single strongest term
            j = int(np.argmax(abs_c))
            mask = np.zeros(m, dtype=bool)
            mask[j] = True
            k = 1

        if k > max_terms:
            idx = np.argsort(abs_c[mask])[::-1]
            active = np.flatnonzero(mask)[idx[:max_terms]]
            mask2 = np.zeros(m, dtype=bool)
            mask2[active] = True
            mask = mask2
            k = int(np.count_nonzero(mask))

        Phi_sel = Phi[:, mask]
        c_sel = _ridge_fit(Phi_sel, y, lam)
        yhat = Phi_sel @ c_sel
        mse = float(np.mean((y - yhat) ** 2))
        bicv = _bic(mse, n, k)
        if (bicv < best["bic"] - 1e-12) or (abs(bicv - best["bic"]) <= 1e-12 and mse < best["mse"]):
            best = {"bic": bicv, "mse": mse, "c": c_sel, "mask": mask, "yhat": yhat}

    mask = best["mask"]
    c_sel = best["c"]
    exprs_sel = [exprs[i] for i in range(m) if mask[i]]
    return c_sel, exprs_sel, best["yhat"]


def _build_expression_from_terms(coefs: np.ndarray, term_exprs: List[str]) -> str:
    # coefs correspond to term_exprs, already sparse
    idx = np.argsort(np.abs(coefs))[::-1]
    parts = []
    for j in idx:
        c = float(coefs[j])
        if not np.isfinite(c) or abs(c) < 1e-15:
            continue
        term = term_exprs[j]
        sign = "-" if c < 0 else "+"
        a = abs(c)
        if term == "1":
            core = _fmt_float(a)
        else:
            if abs(a - 1.0) < 1e-12:
                core = f"({term})"
            else:
                core = f"({_fmt_float(a)})*({term})"
        parts.append((sign, core))

    if not parts:
        return "0.0"

    # first term
    sign0, core0 = parts[0]
    if sign0 == "-":
        expr = f"-{core0}"
    else:
        expr = f"{core0}"

    for sign, core in parts[1:]:
        if sign == "-":
            expr += f" - {core}"
        else:
            expr += f" + {core}"
    return expr


class Solution:
    def __init__(self, **kwargs):
        self.max_degree = int(kwargs.get("max_degree", 3))
        self.max_terms = int(kwargs.get("max_terms", 12))
        self.lambdas = kwargs.get("lambdas", [0.0, 1e-8, 1e-6, 1e-4, 1e-2])
        self.alphas = kwargs.get("alphas", [0.125, 0.25, 0.5, 0.75, 1.0, 1.5, 2.0])
        self.damping_forms = kwargs.get(
            "damping_forms",
            ["all", "12", "34"]
        )

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        X = np.asarray(X, dtype=np.float64)
        y = np.asarray(y, dtype=np.float64).reshape(-1)
        n, d = X.shape
        if d != 4:
            raise ValueError("X must have shape (n, 4)")

        x1, x2, x3, x4 = X[:, 0], X[:, 1], X[:, 2], X[:, 3]
        x1_2 = x1 * x1
        x2_2 = x2 * x2
        x3_2 = x3 * x3
        x4_2 = x4 * x4

        mon_vals, mon_exprs, _ = _build_monomials(X, max_degree=self.max_degree)

        # undamped base: constant + linear
        und_vals = [np.ones(n, dtype=np.float64), x1, x2, x3, x4]
        und_exprs = ["1", "x1", "x2", "x3", "x4"]

        damping_candidates = []
        if "all" in self.damping_forms:
            damping_candidates.append(
                ("(x1**2+x2**2+x3**2+x4**2)", x1_2 + x2_2 + x3_2 + x4_2)
            )
        if "12" in self.damping_forms:
            damping_candidates.append(
                ("(x1**2+x2**2)", x1_2 + x2_2)
            )
        if "34" in self.damping_forms:
            damping_candidates.append(
                ("(x3**2+x4**2)", x3_2 + x4_2)
            )

        best_global = {
            "bic": np.inf,
            "mse": np.inf,
            "expression": "0.0",
            "predictions": np.full(n, float(np.mean(y)) if n else 0.0, dtype=np.float64),
            "terms": 0,
        }

        for damp_str, damp_val in damping_candidates:
            for alpha in self.alphas:
                E = np.exp(-float(alpha) * damp_val)

                # Build feature matrix per candidate
                # Columns: undamped base + (monomials * E)
                damp_expr = f"exp(-{_fmt_float(float(alpha))}*{damp_str})"

                cols = []
                exprs = []

                for v, e in zip(und_vals, und_exprs):
                    cols.append(v)
                    exprs.append(e)

                for mv, me in zip(mon_vals, mon_exprs):
                    cols.append(mv * E)
                    if me == "1":
                        exprs.append(damp_expr)
                    else:
                        exprs.append(f"({me})*{damp_expr}")

                Phi = np.column_stack(cols).astype(np.float64, copy=False)

                for lam in self.lambdas:
                    c_sel, exprs_sel, yhat = _select_sparse(
                        Phi, exprs, y, lam=float(lam), max_terms=self.max_terms
                    )
                    mse = float(np.mean((y - yhat) ** 2))
                    k = len(exprs_sel)
                    bicv = _bic(mse, n, k)

                    if (bicv < best_global["bic"] - 1e-12) or (abs(bicv - best_global["bic"]) <= 1e-12 and mse < best_global["mse"]):
                        expression = _build_expression_from_terms(c_sel, exprs_sel)
                        best_global = {
                            "bic": bicv,
                            "mse": mse,
                            "expression": expression,
                            "predictions": yhat,
                            "terms": k,
                        }

        return {
            "expression": best_global["expression"],
            "predictions": best_global["predictions"].tolist(),
            "details": {
                "mse": best_global["mse"],
                "terms": best_global["terms"],
            },
        }