import numpy as np
import itertools
import math

try:
    from pysr import PySRRegressor
except Exception:
    PySRRegressor = None


def _fmt_float(x: float) -> str:
    if not np.isfinite(x):
        return "0.0"
    ax = abs(x)
    if ax < 1e-14:
        return "0.0"
    s = format(float(x), ".12g")
    if s == "-0":
        s = "0"
    if "e" in s or "E" in s:
        s = s.replace("E", "e")
    return s


def _term_needs_parens(term: str) -> bool:
    return ("+" in term) or ("-" in term[1:]) or ("/" in term) or (" " in term)


def _build_linear_expression(intercept: float, terms: list, coeffs: np.ndarray) -> str:
    parts = []
    b = float(intercept)
    if abs(b) >= 1e-12:
        parts.append(_fmt_float(b))

    for c, t in zip(coeffs, terms):
        c = float(c)
        if abs(c) < 1e-10:
            continue
        if abs(c - 1.0) < 5e-7:
            parts.append(t)
        elif abs(c + 1.0) < 5e-7:
            if _term_needs_parens(t):
                parts.append(f"-({t})")
            else:
                parts.append(f"-{t}")
        else:
            cs = _fmt_float(c)
            if _term_needs_parens(t):
                parts.append(f"{cs}*({t})")
            else:
                parts.append(f"{cs}*{t}")

    if not parts:
        return "0.0"

    expr = parts[0]
    for p in parts[1:]:
        if p.startswith("-"):
            expr = f"{expr} {p}"
        else:
            expr = f"{expr} + {p}"
    expr = expr.replace(" + -", " - ")
    return expr


class Solution:
    def __init__(self, **kwargs):
        self.max_terms = int(kwargs.get("max_terms", 4))
        self.use_pysr_fallback = bool(kwargs.get("use_pysr_fallback", True))
        self.random_state = int(kwargs.get("random_state", 42))

    def _candidate_terms(self, x1: np.ndarray, x2: np.ndarray):
        s1 = np.sin(x1)
        c1 = np.cos(x1)
        s2 = np.sin(x2)
        c2 = np.cos(x2)

        s2x1 = np.sin(2.0 * x1)
        c2x1 = np.cos(2.0 * x1)
        s3x1 = np.sin(3.0 * x1)
        c3x1 = np.cos(3.0 * x1)

        s2x2 = np.sin(2.0 * x2)
        c2x2 = np.cos(2.0 * x2)
        s3x2 = np.sin(3.0 * x2)
        c3x2 = np.cos(3.0 * x2)

        xp = x1 + x2
        xm = x1 - x2
        sp = np.sin(xp)
        cp = np.cos(xp)
        sm = np.sin(xm)
        cm = np.cos(xm)

        terms = []
        def add(name, vec):
            terms.append((name, vec.astype(np.float64, copy=False)))

        add("x1", x1)
        add("x2", x2)

        add("sin(x1)", s1)
        add("cos(x1)", c1)
        add("sin(x2)", s2)
        add("cos(x2)", c2)

        add("sin(2*x1)", s2x1)
        add("cos(2*x1)", c2x1)
        add("sin(3*x1)", s3x1)
        add("cos(3*x1)", c3x1)

        add("sin(2*x2)", s2x2)
        add("cos(2*x2)", c2x2)
        add("sin(3*x2)", s3x2)
        add("cos(3*x2)", c3x2)

        add("sin(x1 + x2)", sp)
        add("cos(x1 + x2)", cp)
        add("sin(x1 - x2)", sm)
        add("cos(x1 - x2)", cm)

        add("sin(x1)*sin(x2)", s1 * s2)
        add("sin(x1)*cos(x2)", s1 * c2)
        add("cos(x1)*sin(x2)", c1 * s2)
        add("cos(x1)*cos(x2)", c1 * c2)

        add("sin(x1)**2", s1 * s1)
        add("cos(x1)**2", c1 * c1)
        add("sin(x2)**2", s2 * s2)
        add("cos(x2)**2", c2 * c2)

        add("sin(2*x1)*cos(2*x2)", s2x1 * c2x2)
        add("cos(2*x1)*sin(2*x2)", c2x1 * s2x2)
        add("sin(2*x1)*sin(2*x2)", s2x1 * s2x2)
        add("cos(2*x1)*cos(2*x2)", c2x1 * c2x2)

        return terms

    def _fit_best_subset(self, X: np.ndarray, y: np.ndarray):
        x1 = X[:, 0].astype(np.float64, copy=False)
        x2 = X[:, 1].astype(np.float64, copy=False)

        cand = self._candidate_terms(x1, x2)
        names = [t[0] for t in cand]
        F = np.column_stack([t[1] for t in cand])  # (n, m)
        n, m = F.shape

        y = y.astype(np.float64, copy=False)
        y_mean = float(np.mean(y))
        y_centered = y - y_mean
        y_var = float(np.var(y_centered)) + 1e-18

        best = None  # (bic, mse, k, subset_idx, coeffs_with_intercept)
        idxs = np.arange(m)

        # Precompute ones column
        ones = np.ones(n, dtype=np.float64)

        max_terms = max(1, min(self.max_terms, m))
        for k in range(1, max_terms + 1):
            for subset in itertools.combinations(idxs, k):
                A = np.column_stack([ones, F[:, subset]])
                try:
                    coef, _, _, _ = np.linalg.lstsq(A, y, rcond=None)
                except np.linalg.LinAlgError:
                    continue
                pred = A @ coef
                resid = y - pred
                sse = float(resid @ resid)
                mse = sse / n

                # BIC with floor on mse to avoid log(0)
                mse_floor = max(mse, 1e-18 * y_var)
                p = k + 1
                bic = n * math.log(mse_floor) + p * math.log(max(n, 2))

                if best is None:
                    best = (bic, mse, k, subset, coef)
                else:
                    if (bic < best[0] - 1e-12) or (abs(bic - best[0]) <= 1e-12 and (mse < best[1] - 1e-12)) or (
                        abs(bic - best[0]) <= 1e-12 and abs(mse - best[1]) <= 1e-12 and k < best[2]
                    ):
                        best = (bic, mse, k, subset, coef)

        if best is None:
            # Fallback: constant
            expression = _fmt_float(y_mean)
            return expression, np.full_like(y, y_mean), {"mse": float(np.mean((y - y_mean) ** 2)), "method": "constant"}

        _, mse, k, subset, coef = best
        chosen_terms = [names[i] for i in subset]
        intercept = float(coef[0])
        coeffs = coef[1:].copy()

        # Clean near-zero coefficients
        mask = np.abs(coeffs) >= 1e-10
        if not np.all(mask):
            coeffs = coeffs[mask]
            chosen_terms = [t for t, keep in zip(chosen_terms, mask) if keep]
            if len(chosen_terms) == 0:
                expression = _fmt_float(intercept)
                pred = np.full_like(y, intercept)
                return expression, pred, {"mse": float(np.mean((y - pred) ** 2)), "method": "sparse_ls"}

        expression = _build_linear_expression(intercept, chosen_terms, coeffs)

        # Compute predictions
        A_full = np.column_stack([ones] + [F[:, names.index(t)] for t in chosen_terms]) if chosen_terms else ones[:, None]
        if chosen_terms:
            coef_full = np.concatenate([[intercept], coeffs])
            pred = A_full @ coef_full
        else:
            pred = np.full_like(y, intercept)

        return expression, pred, {"mse": float(np.mean((y - pred) ** 2)), "method": "sparse_ls", "k": int(len(chosen_terms))}

    def _pysr_fallback(self, X: np.ndarray, y: np.ndarray):
        if PySRRegressor is None:
            return None
        try:
            model = PySRRegressor(
                niterations=40,
                populations=10,
                population_size=40,
                maxsize=25,
                binary_operators=["+", "-", "*", "/", "**"],
                unary_operators=["sin", "cos", "exp", "log"],
                model_selection="best",
                verbosity=0,
                progress=False,
                random_state=self.random_state,
            )
            model.fit(X, y, variable_names=["x1", "x2"])
            expr = str(model.sympy())
            pred = model.predict(X).astype(np.float64, copy=False)
            return expr, pred, {"mse": float(np.mean((y - pred) ** 2)), "method": "pysr"}
        except Exception:
            return None

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        X = np.asarray(X)
        y = np.asarray(y).reshape(-1)
        if X.ndim != 2 or X.shape[1] != 2:
            raise ValueError("X must have shape (n, 2)")
        n = X.shape[0]
        if y.shape[0] != n:
            raise ValueError("y must have shape (n,)")

        expression, pred, details = self._fit_best_subset(X, y)

        if self.use_pysr_fallback and (details.get("mse", np.inf) > 1e-8 * (float(np.var(y)) + 1e-18)):
            fb = self._pysr_fallback(X, y)
            if fb is not None:
                expr2, pred2, details2 = fb
                if details2.get("mse", np.inf) < details.get("mse", np.inf) * 0.99:
                    expression, pred, details = expr2, pred2, details2

        return {
            "expression": expression,
            "predictions": pred.tolist(),
            "details": details,
        }