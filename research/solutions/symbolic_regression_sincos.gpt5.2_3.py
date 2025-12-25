import numpy as np
import sympy as sp
from itertools import combinations

class Solution:
    def __init__(self, **kwargs):
        self.kwargs = kwargs

    @staticmethod
    def _build_terms(x1: np.ndarray, x2: np.ndarray):
        s1 = np.sin(x1)
        c1 = np.cos(x1)
        s2 = np.sin(x2)
        c2 = np.cos(x2)

        x1x2 = x1 * x2
        x1p2 = x1 + x2
        x1m2 = x1 - x2
        twox1 = 2.0 * x1
        twox2 = 2.0 * x2
        twox1px2 = 2.0 * x1 + x2
        x1ptwox2 = x1 + 2.0 * x2

        terms = []
        terms.append(("x1", x1))
        terms.append(("x2", x2))

        terms.append(("sin(x1)", s1))
        terms.append(("cos(x1)", c1))
        terms.append(("sin(x2)", s2))
        terms.append(("cos(x2)", c2))

        terms.append(("sin(x1 + x2)", np.sin(x1p2)))
        terms.append(("cos(x1 + x2)", np.cos(x1p2)))
        terms.append(("sin(x1 - x2)", np.sin(x1m2)))
        terms.append(("cos(x1 - x2)", np.cos(x1m2)))

        terms.append(("sin(2*x1)", np.sin(twox1)))
        terms.append(("cos(2*x1)", np.cos(twox1)))
        terms.append(("sin(2*x2)", np.sin(twox2)))
        terms.append(("cos(2*x2)", np.cos(twox2)))

        terms.append(("sin(x1*x2)", np.sin(x1x2)))
        terms.append(("cos(x1*x2)", np.cos(x1x2)))

        terms.append(("sin(2*x1 + x2)", np.sin(twox1px2)))
        terms.append(("cos(2*x1 + x2)", np.cos(twox1px2)))
        terms.append(("sin(x1 + 2*x2)", np.sin(x1ptwox2)))
        terms.append(("cos(x1 + 2*x2)", np.cos(x1ptwox2)))

        terms.append(("sin(x1)*sin(x2)", s1 * s2))
        terms.append(("sin(x1)*cos(x2)", s1 * c2))
        terms.append(("cos(x1)*sin(x2)", c1 * s2))
        terms.append(("cos(x1)*cos(x2)", c1 * c2))

        terms.append(("sin(x1)*x2", s1 * x2))
        terms.append(("cos(x1)*x2", c1 * x2))
        terms.append(("sin(x2)*x1", s2 * x1))
        terms.append(("cos(x2)*x1", c2 * x1))

        return terms

    @staticmethod
    def _quantize_number(v: float):
        if not np.isfinite(v):
            return sp.Float(0.0), 0.0
        if abs(v) < 1e-12:
            return sp.Integer(0), 0.0
        if abs(v - 1.0) < 1e-10:
            return sp.Integer(1), 1.0
        if abs(v + 1.0) < 1e-10:
            return sp.Integer(-1), -1.0
        vr = round(v)
        if abs(v - vr) < 1e-10 and abs(vr) <= 10**12:
            return sp.Integer(int(vr)), float(int(vr))
        s = float(f"{v:.12g}")
        return sp.Float(s), s

    @staticmethod
    def _contains_forbidden(expr):
        allowed = {sp.sin, sp.cos, sp.exp, sp.log}
        for node in sp.preorder_traversal(expr):
            if isinstance(node, sp.Function):
                if node.func not in allowed:
                    return True
        return False

    @staticmethod
    def _complexity(expr):
        unary = 0
        binary = 0
        for node in sp.preorder_traversal(expr):
            if isinstance(node, sp.Function):
                if node.func in (sp.sin, sp.cos, sp.exp, sp.log):
                    unary += 1
            elif isinstance(node, sp.Add):
                binary += max(len(node.args) - 1, 0)
            elif isinstance(node, sp.Mul):
                binary += max(len(node.args) - 1, 0)
            elif isinstance(node, sp.Pow):
                binary += 1
        return int(2 * binary + unary)

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        X = np.asarray(X)
        y = np.asarray(y).reshape(-1)
        n = X.shape[0]
        if n == 0:
            return {"expression": "0", "predictions": [], "details": {"complexity": 0}}

        x1_full = X[:, 0].astype(np.float64, copy=False)
        x2_full = X[:, 1].astype(np.float64, copy=False)
        y_full = y.astype(np.float64, copy=False)

        if np.allclose(y_full, y_full.mean(), rtol=0, atol=1e-12):
            c = float(y_full.mean())
            expr = sp.Float(float(f"{c:.12g}"))
            return {
                "expression": str(expr),
                "predictions": (np.full(n, c, dtype=np.float64)).tolist(),
                "details": {"complexity": 0},
            }

        max_fit_n = 8000
        if n > max_fit_n:
            rng = np.random.default_rng(0)
            idx = rng.choice(n, size=max_fit_n, replace=False)
            x1 = x1_full[idx]
            x2 = x2_full[idx]
            yy = y_full[idx]
        else:
            x1 = x1_full
            x2 = x2_full
            yy = y_full

        terms = self._build_terms(x1, x2)
        m = len(terms)
        T = np.column_stack([t[1] for t in terms]).astype(np.float64, copy=False)

        sx1, sx2 = sp.Symbol("x1"), sp.Symbol("x2")
        locals_map = {
            "x1": sx1,
            "x2": sx2,
            "sin": sp.sin,
            "cos": sp.cos,
            "exp": sp.exp,
            "log": sp.log,
        }
        term_sym = [sp.sympify(name, locals=locals_map) for name, _ in terms]

        ones = np.ones_like(yy, dtype=np.float64)
        best = None  # (mse, complexity, subset_indices, coef_vector_quant, coef_vector_float)
        max_terms = 3
        rcond = None

        def fit_subset(idxs):
            if len(idxs) == 0:
                A = ones[:, None]
            else:
                A = np.column_stack([ones, T[:, idxs]])
            coef, _, _, _ = np.linalg.lstsq(A, yy, rcond=rcond)
            pred = A @ coef
            resid = pred - yy
            mse = float(np.mean(resid * resid))
            return coef, mse

        for k in range(0, max_terms + 1):
            for idxs in combinations(range(m), k):
                coef, mse = fit_subset(list(idxs))
                if not np.isfinite(mse):
                    continue

                c0_sym, c0_f = self._quantize_number(float(coef[0]))
                expr = c0_sym
                coef_f = [c0_f]

                for j, ti in enumerate(idxs):
                    cj_sym, cj_f = self._quantize_number(float(coef[j + 1]))
                    coef_f.append(cj_f)
                    if cj_f == 0.0:
                        continue
                    expr = expr + cj_sym * term_sym[ti]

                if expr == 0:
                    comp = 0
                else:
                    expr_s = expr
                    try:
                        expr_try = sp.simplify(expr_s)
                        if not self._contains_forbidden(expr_try):
                            expr_s = expr_try
                    except Exception:
                        pass
                    comp = self._complexity(expr_s)
                    expr = expr_s

                if best is None or mse < best[0] - 1e-12 or (abs(mse - best[0]) <= 1e-12 and comp < best[1]):
                    best = (mse, comp, list(idxs), coef, expr, coef_f)

        if best is None:
            c = float(y_full.mean())
            expr = sp.Float(float(f"{c:.12g}"))
            return {
                "expression": str(expr),
                "predictions": (np.full(n, c, dtype=np.float64)).tolist(),
                "details": {"complexity": 0},
            }

        _, best_comp, best_idxs, coef_raw, best_expr_sym, _ = best

        # Refit on full data using best subset
        terms_full = self._build_terms(x1_full, x2_full)
        T_full = np.column_stack([t[1] for t in terms_full]).astype(np.float64, copy=False)
        ones_full = np.ones_like(y_full, dtype=np.float64)
        if len(best_idxs) == 0:
            A_full = ones_full[:, None]
        else:
            A_full = np.column_stack([ones_full, T_full[:, best_idxs]])
        coef_full, _, _, _ = np.linalg.lstsq(A_full, y_full, rcond=rcond)
        pred_full = A_full @ coef_full

        # Build final sympy expression with quantized coefficients
        c0_sym, _ = self._quantize_number(float(coef_full[0]))
        expr_final = c0_sym
        for j, ti in enumerate(best_idxs):
            cj_sym, _ = self._quantize_number(float(coef_full[j + 1]))
            if cj_sym == 0:
                continue
            expr_final = expr_final + cj_sym * term_sym[ti]
        if expr_final != 0:
            try:
                expr_try = sp.simplify(expr_final)
                if not self._contains_forbidden(expr_try):
                    expr_final = expr_try
            except Exception:
                pass

        expr_str = sp.sstr(expr_final)

        # Ensure expression uses only allowed function names (no SymPy module prefix)
        expr_str = expr_str.replace("Sin", "sin").replace("Cos", "cos").replace("Exp", "exp").replace("Log", "log")

        comp_final = self._complexity(expr_final)

        return {
            "expression": expr_str,
            "predictions": pred_full.tolist(),
            "details": {"complexity": comp_final},
        }