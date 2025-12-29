import numpy as np
import itertools
import sympy as sp

class Solution:
    def __init__(self, **kwargs):
        self.kwargs = kwargs

    @staticmethod
    def _format_float(v: float) -> str:
        if v == 0.0:
            return "0"
        s = f"{v:.12g}"
        if s == "-0":
            s = "0"
        return s

    @staticmethod
    def _snap_coeff(c: float, scale: float, tol_zero: float = 1e-8, tol_one: float = 5e-3) -> float:
        if abs(c) <= tol_zero * scale:
            return 0.0
        if abs(c - 1.0) <= tol_one:
            return 1.0
        if abs(c + 1.0) <= tol_one:
            return -1.0
        return float(c)

    @staticmethod
    def _sympy_complexity(expr_str: str) -> int:
        sin, cos, exp, log = sp.sin, sp.cos, sp.exp, sp.log
        x1, x2 = sp.Symbol("x1"), sp.Symbol("x2")
        try:
            expr = sp.sympify(expr_str, locals={"sin": sin, "cos": cos, "exp": exp, "log": log, "x1": x1, "x2": x2})
        except Exception:
            return 10**9

        unary_funcs = {sp.sin, sp.cos, sp.exp, sp.log}
        binary = 0
        unary = 0

        def rec(e):
            nonlocal binary, unary
            if isinstance(e, sp.Add):
                args = e.args
                binary += max(0, len(args) - 1)
                for a in args:
                    rec(a)
                return
            if isinstance(e, sp.Mul):
                args = e.args
                binary += max(0, len(args) - 1)
                for a in args:
                    rec(a)
                return
            if isinstance(e, sp.Pow):
                binary += 1
                rec(e.base)
                rec(e.exp)
                return
            f = getattr(e, "func", None)
            if f in unary_funcs:
                unary += 1
                if e.args:
                    rec(e.args[0])
                return
            if hasattr(e, "args"):
                for a in e.args:
                    rec(a)

        rec(expr)
        return int(2 * binary + unary)

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        X = np.asarray(X, dtype=np.float64)
        y = np.asarray(y, dtype=np.float64).reshape(-1)
        n = X.shape[0]
        x1 = X[:, 0]
        x2 = X[:, 1]

        terms = []
        # (name, values, base_bin, base_unary)
        terms.append(("x1", x1, 0, 0))
        terms.append(("x2", x2, 0, 0))
        terms.append(("sin(x1)", np.sin(x1), 0, 1))
        terms.append(("cos(x1)", np.cos(x1), 0, 1))
        terms.append(("sin(x2)", np.sin(x2), 0, 1))
        terms.append(("cos(x2)", np.cos(x2), 0, 1))

        x1px2 = x1 + x2
        x1mx2 = x1 - x2
        terms.append(("sin(x1+x2)", np.sin(x1px2), 1, 1))
        terms.append(("cos(x1+x2)", np.cos(x1px2), 1, 1))
        terms.append(("sin(x1-x2)", np.sin(x1mx2), 1, 1))
        terms.append(("cos(x1-x2)", np.cos(x1mx2), 1, 1))

        two_x1 = 2.0 * x1
        two_x2 = 2.0 * x2
        terms.append(("sin(2*x1)", np.sin(two_x1), 1, 1))
        terms.append(("cos(2*x1)", np.cos(two_x1), 1, 1))
        terms.append(("sin(2*x2)", np.sin(two_x2), 1, 1))
        terms.append(("cos(2*x2)", np.cos(two_x2), 1, 1))

        sinx1 = np.sin(x1)
        cosx1 = np.cos(x1)
        sinx2 = np.sin(x2)
        cosx2 = np.cos(x2)
        terms.append(("sin(x1)*cos(x2)", sinx1 * cosx2, 1, 2))
        terms.append(("cos(x1)*sin(x2)", cosx1 * sinx2, 1, 2))
        terms.append(("sin(x1)*sin(x2)", sinx1 * sinx2, 1, 2))
        terms.append(("cos(x1)*cos(x2)", cosx1 * cosx2, 1, 2))
        terms.append(("x1*x2", x1 * x2, 1, 0))

        m = len(terms)
        F = np.empty((n, m), dtype=np.float64)
        base_bin = np.empty(m, dtype=np.int32)
        base_un = np.empty(m, dtype=np.int32)
        names = []
        for j, (nm, vals, bb, bu) in enumerate(terms):
            names.append(nm)
            F[:, j] = vals
            base_bin[j] = bb
            base_un[j] = bu

        ones = np.ones(n, dtype=np.float64)
        scale = float(max(1.0, np.std(y) if n > 1 else 1.0))

        def est_complexity(subset, coeffs):
            c0 = coeffs[0]
            nz = []
            intercept_nz = abs(c0) > 1e-8 * scale
            mulcount = 0
            bb = 0
            bu = 0
            for idx, cj in zip(subset, coeffs[1:]):
                if abs(cj) <= 1e-8 * scale:
                    continue
                nz.append((idx, cj))
                bb += int(base_bin[idx])
                bu += int(base_un[idx])
                if not (abs(abs(cj) - 1.0) <= 1e-3):
                    mulcount += 1
            num_parts = (1 if intercept_nz else 0) + len(nz)
            addcount = max(0, num_parts - 1)
            binops = bb + mulcount + addcount
            return int(2 * binops + bu)

        best_mse = float("inf")
        best_c = 10**9
        best_subset = ()
        best_coeffs = np.array([0.0], dtype=np.float64)

        max_k = 4
        # also include k=0 (intercept-only)
        for k in range(0, max_k + 1):
            for subset in itertools.combinations(range(m), k):
                if k == 0:
                    A = ones.reshape(-1, 1)
                else:
                    A = np.column_stack([ones, F[:, subset]])
                coeffs, _, _, _ = np.linalg.lstsq(A, y, rcond=None)
                pred = A @ coeffs
                r = y - pred
                mse = float((r @ r) / n)
                cplx = est_complexity(subset, coeffs)
                if (mse < best_mse - 1e-12) or (abs(mse - best_mse) <= 1e-12 and cplx < best_c):
                    best_mse = mse
                    best_c = cplx
                    best_subset = subset
                    best_coeffs = coeffs

        # Build final expression with snapping
        coeffs = best_coeffs.copy()
        subset = best_subset

        c0 = self._snap_coeff(float(coeffs[0]), scale, tol_zero=5e-3, tol_one=5e-3)
        term_parts = []
        for idx, cj in zip(subset, coeffs[1:]):
            cj = self._snap_coeff(float(cj), scale, tol_zero=1e-8, tol_one=5e-3)
            if cj == 0.0:
                continue
            term_parts.append((cj, names[idx]))

        parts = []
        if c0 != 0.0 or not term_parts:
            parts.append(("const", c0))

        for cj, nm in term_parts:
            parts.append((nm, cj))

        if not parts:
            expression = "0"
        else:
            expr_chunks = []
            first = True
            for nm, val in parts:
                if nm == "const":
                    c = float(val)
                    if c == 0.0 and term_parts:
                        continue
                    s_abs = self._format_float(abs(c))
                    if first:
                        if c < 0:
                            expr_chunks.append(f"-{s_abs}")
                        else:
                            expr_chunks.append(f"{self._format_float(c)}")
                        first = False
                    else:
                        if c < 0:
                            expr_chunks.append(f"- {s_abs}")
                        else:
                            expr_chunks.append(f"+ {s_abs}")
                    continue

                c = float(val)
                sign = "-" if c < 0 else "+"
                ac = abs(c)
                if abs(ac - 1.0) <= 1e-15:
                    seg = nm
                else:
                    seg = f"{self._format_float(ac)}*{nm}"
                if first:
                    if sign == "-":
                        expr_chunks.append(f"-{seg}")
                    else:
                        expr_chunks.append(seg)
                    first = False
                else:
                    expr_chunks.append(f"{sign} {seg}")

            expression = " ".join(expr_chunks).strip()
            if expression == "":
                expression = "0"

        # Predictions from expression
        local_env = {"sin": np.sin, "cos": np.cos, "exp": np.exp, "log": np.log}
        with np.errstate(all="ignore"):
            try:
                preds = eval(expression, {"__builtins__": {}}, {"x1": x1, "x2": x2, **local_env})
                preds = np.asarray(preds, dtype=np.float64).reshape(-1)
                if preds.shape[0] != n or not np.all(np.isfinite(preds)):
                    preds = (ones * float(best_coeffs[0]) + (F[:, subset] @ best_coeffs[1:]) if len(subset) > 0 else ones * float(best_coeffs[0]))
            except Exception:
                preds = (ones * float(best_coeffs[0]) + (F[:, subset] @ best_coeffs[1:]) if len(subset) > 0 else ones * float(best_coeffs[0]))

        details = {}
        cplx2 = self._sympy_complexity(expression)
        if cplx2 < 10**9:
            details["complexity"] = int(cplx2)

        return {
            "expression": expression,
            "predictions": preds.tolist(),
            "details": details,
        }