import numpy as np
import itertools
import sympy as sp


class Solution:
    def __init__(self, **kwargs):
        self.max_terms = int(kwargs.get("max_terms", 4))
        self.max_harmonic = int(kwargs.get("max_harmonic", 3))
        self.include_cross = bool(kwargs.get("include_cross", True))
        self.include_sumdiff = bool(kwargs.get("include_sumdiff", True))

    @staticmethod
    def _sympy_complexity(expr: sp.Expr) -> int:
        sin, cos, exp, log = sp.sin, sp.cos, sp.exp, sp.log
        unary_funcs = (sin, cos, exp, log)

        binary_ops = 0
        unary_ops = 0

        stack = [expr]
        while stack:
            e = stack.pop()
            if isinstance(e, sp.Function):
                if e.func in unary_funcs:
                    unary_ops += 1
                stack.extend(e.args)
            elif isinstance(e, sp.Add) or isinstance(e, sp.Mul):
                args = e.args
                if len(args) >= 2:
                    binary_ops += (len(args) - 1)
                stack.extend(args)
            elif isinstance(e, sp.Pow):
                binary_ops += 1
                stack.extend(e.args)
            else:
                if hasattr(e, "args"):
                    stack.extend(e.args)

        return int(2 * binary_ops + unary_ops)

    @staticmethod
    def _safe_lstsq(A: np.ndarray, y: np.ndarray) -> np.ndarray:
        # If ill-conditioned or underdetermined, fall back to ridge
        n, p = A.shape
        if n >= p:
            try:
                coeffs, _, _, _ = np.linalg.lstsq(A, y, rcond=None)
                if np.all(np.isfinite(coeffs)):
                    return coeffs
            except Exception:
                pass
        # ridge fallback
        lam = 1e-8
        ATA = A.T @ A
        ATy = A.T @ y
        ATA.flat[:: ATA.shape[0] + 1] += lam
        try:
            coeffs = np.linalg.solve(ATA, ATy)
        except Exception:
            coeffs, _, _, _ = np.linalg.lstsq(A, y, rcond=None)
        return coeffs

    @staticmethod
    def _format_float(c: float) -> str:
        if not np.isfinite(c):
            return "0.0"
        # Avoid "-0.0"
        if abs(c) < 1e-15:
            c = 0.0
        s = f"{c:.12g}"
        if s == "-0":
            s = "0"
        return s

    @classmethod
    def _build_expression(cls, intercept: float, coefs: np.ndarray, term_exprs: list, coef_tol: float = 1e-12) -> str:
        parts = []
        if np.isfinite(intercept) and abs(intercept) > coef_tol:
            parts.append(cls._format_float(float(intercept)))

        for c, texpr in zip(coefs, term_exprs):
            c = float(c)
            if not np.isfinite(c) or abs(c) <= coef_tol:
                continue

            if abs(c - 1.0) < 1e-6:
                parts.append(f"({texpr})")
            elif abs(c + 1.0) < 1e-6:
                parts.append(f"(-({texpr}))")
            else:
                parts.append(f"({cls._format_float(c)})*({texpr})")

        if not parts:
            return "0.0"
        expr = " + ".join(parts)
        return expr

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        X = np.asarray(X)
        y = np.asarray(y).reshape(-1)
        n = X.shape[0]
        x1 = X[:, 0].astype(np.float64, copy=False)
        x2 = X[:, 1].astype(np.float64, copy=False)

        # Precompute basis
        term_exprs = []
        cols = []

        def add_term(expr_str: str, values: np.ndarray):
            if values is None:
                return
            v = np.asarray(values, dtype=np.float64)
            if v.shape != (n,):
                return
            if not np.all(np.isfinite(v)):
                return
            # Skip near-constant zero columns
            if np.std(v) < 1e-14:
                return
            term_exprs.append(expr_str)
            cols.append(v)

        # Linear terms (sometimes helpful)
        add_term("x1", x1)
        add_term("x2", x2)

        with np.errstate(all="ignore"):
            # Harmonics
            for k in range(1, max(1, self.max_harmonic) + 1):
                if k == 1:
                    add_term("sin(x1)", np.sin(x1))
                    add_term("cos(x1)", np.cos(x1))
                    add_term("sin(x2)", np.sin(x2))
                    add_term("cos(x2)", np.cos(x2))
                else:
                    ks = self._format_float(float(k))
                    add_term(f"sin(({ks})*x1)", np.sin(k * x1))
                    add_term(f"cos(({ks})*x1)", np.cos(k * x1))
                    add_term(f"sin(({ks})*x2)", np.sin(k * x2))
                    add_term(f"cos(({ks})*x2)", np.cos(k * x2))

            if self.include_sumdiff:
                add_term("sin(x1 + x2)", np.sin(x1 + x2))
                add_term("cos(x1 + x2)", np.cos(x1 + x2))
                add_term("sin(x1 - x2)", np.sin(x1 - x2))
                add_term("cos(x1 - x2)", np.cos(x1 - x2))

            if self.include_cross:
                s1, c1 = np.sin(x1), np.cos(x1)
                s2, c2 = np.sin(x2), np.cos(x2)
                add_term("sin(x1)*sin(x2)", s1 * s2)
                add_term("sin(x1)*cos(x2)", s1 * c2)
                add_term("cos(x1)*sin(x2)", c1 * s2)
                add_term("cos(x1)*cos(x2)", c1 * c2)

        if not cols:
            pred = np.full(n, float(np.mean(y)) if n else 0.0)
            expr = self._format_float(float(pred[0] if n else 0.0))
            return {"expression": expr, "predictions": pred.tolist(), "details": {"complexity": 0}}

        F = np.column_stack(cols)  # (n, m)
        m = F.shape[1]
        ones = np.ones((n, 1), dtype=np.float64)

        # Model selection: minimize MSE, tie-break on estimated complexity later
        max_terms = min(self.max_terms, m)
        best = None  # (mse, idxs, coeffs, pred)
        best_mse = np.inf
        tol_rel = 1e-12
        tol_abs = 1e-14

        # Evaluate small subset sizes first to encourage simple models
        for k in range(0, max_terms + 1):
            for idxs in itertools.combinations(range(m), k):
                if k == 0:
                    A = ones
                    coeffs = self._safe_lstsq(A, y)
                    pred = A @ coeffs
                    mse = float(np.mean((y - pred) ** 2))
                    if mse + tol_abs < best_mse:
                        best_mse = mse
                        best = (mse, idxs, coeffs, pred)
                    continue

                Fi = F[:, idxs]
                A = np.concatenate([ones, Fi], axis=1)
                coeffs = self._safe_lstsq(A, y)
                pred = A @ coeffs
                mse = float(np.mean((y - pred) ** 2))

                if mse + tol_abs < best_mse * (1.0 - tol_rel):
                    best_mse = mse
                    best = (mse, idxs, coeffs, pred)
                elif abs(mse - best_mse) <= max(tol_abs, tol_rel * max(1.0, best_mse)):
                    # Keep the simpler one (by rough count: fewer terms, and prefer fewer cross/sumdiff terms)
                    if best is None or k < len(best[1]):
                        best_mse = mse
                        best = (mse, idxs, coeffs, pred)

        if best is None:
            pred = np.full(n, float(np.mean(y)) if n else 0.0)
            expr = self._format_float(float(pred[0] if n else 0.0))
            return {"expression": expr, "predictions": pred.tolist(), "details": {"complexity": 0}}

        mse, idxs, coeffs, pred = best
        intercept = float(coeffs[0]) if coeffs.size else 0.0
        term_coefs = coeffs[1:] if coeffs.size > 1 else np.array([], dtype=np.float64)
        selected_exprs = [term_exprs[i] for i in idxs]

        expression = self._build_expression(intercept, term_coefs, selected_exprs)

        # Compute exact complexity via sympy
        try:
            x1s, x2s = sp.Symbol("x1"), sp.Symbol("x2")
            expr_sym = sp.sympify(expression, locals={"sin": sp.sin, "cos": sp.cos, "exp": sp.exp, "log": sp.log, "x1": x1s, "x2": x2s})
            complexity = self._sympy_complexity(expr_sym)
            # Re-stringify to ensure sympy-parsable canonical form without changing allowed funcs
            expression = str(expr_sym)
        except Exception:
            complexity = None

        details = {}
        if complexity is not None:
            details["complexity"] = int(complexity)

        return {
            "expression": expression,
            "predictions": pred.tolist(),
            "details": details,
        }