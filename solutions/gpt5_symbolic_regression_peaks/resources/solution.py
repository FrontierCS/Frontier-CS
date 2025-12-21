import numpy as np
import sympy as sp

class Solution:
    def __init__(self, **kwargs):
        self.kwargs = kwargs

    def _format_float(self, x):
        if not np.isfinite(x):
            return "0"
        if abs(x) < 1e-14:
            return "0"
        s = f"{x:.12g}"
        # Remove trailing decimal point if integer-like
        if "." in s:
            s = s.rstrip("0").rstrip(".")
            if s == "-0":
                s = "0"
        return s

    def _predict_params(self, x1, x2, a, b, c, b1, f, py, use_const=False, d0=0.0):
        x1_sq = x1 * x1
        x2_sq = x2 * x2
        e00 = np.exp(-(x1_sq + x2_sq))
        e01 = np.exp(-(x1_sq + (x2 + b1) * (x2 + b1)))
        e10 = np.exp(-((x1 + f) * (x1 + f) + x2_sq))
        t1 = (1.0 - x1) ** 2 * e01
        t2 = (x1 / 5.0 - x1 ** 3 - x2 ** py) * e00
        t3 = e10
        out = a * t1 + b * t2 + c * t3
        if use_const:
            out = out + d0
        return out

    def _build_expression(self, a, b, c, b1, f, py, use_const=False, d0=0.0):
        sa = self._format_float(a)
        sb = self._format_float(b)
        sc = self._format_float(c)
        sb1 = self._format_float(b1)
        sf = self._format_float(f)
        term1 = f"{sa}*(1 - x1)**2*exp(-x1**2 - (x2 + {sb1})**2)"
        term2 = f"{sb}*(x1/5 - x1**3 - x2**{int(py)})*exp(-x1**2 - x2**2)"
        term3 = f"{sc}*exp(-(x1 + {sf})**2 - x2**2)"
        expr = f"{term1} + {term2} + {term3}"
        if use_const and abs(d0) > 0:
            sd0 = self._format_float(d0)
            if sd0.startswith("-"):
                expr = f"{expr} {sd0}"
            else:
                expr = f"{expr} + {sd0}"
        return expr

    def _compute_complexity(self, expr_str):
        try:
            expr = sp.sympify(expr_str, locals={"exp": sp.exp, "sin": sp.sin, "cos": sp.cos, "log": sp.log})
        except Exception:
            return None

        binary_ops = 0
        unary_ops = 0

        def count_ops(e):
            nonlocal binary_ops, unary_ops
            if isinstance(e, sp.Add):
                # n-ary add uses n-1 binary additions
                binary_ops += max(len(e.args) - 1, 0)
            elif isinstance(e, sp.Mul):
                # n-ary mul uses n-1 binary multiplications
                binary_ops += max(len(e.args) - 1, 0)
            elif isinstance(e, sp.Pow):
                binary_ops += 1
            elif isinstance(e, sp.Function):
                if e.func in (sp.exp, sp.sin, sp.cos, sp.log):
                    unary_ops += 1
            for arg in e.args:
                count_ops(arg)

        count_ops(expr)
        return 2 * binary_ops + unary_ops

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        x1 = X[:, 0]
        x2 = X[:, 1]

        # Precompute reusable components
        x1_sq = x1 * x1
        x2_sq = x2 * x2
        ones = np.ones_like(x1)

        e00 = np.exp(-(x1_sq + x2_sq))

        # Candidate parameters near the classic "peaks" function
        b1_candidates = [1.0, 0.9, 1.1]
        f_candidates = [1.0, 0.9, 1.1]
        py_candidates = [5, 3, 7]

        # Precompute exponentials for candidate shifts
        e01_map = {}
        for b1 in b1_candidates:
            e01_map[b1] = np.exp(-(x1_sq + (x2 + b1) * (x2 + b1)))
        e10_map = {}
        for f in f_candidates:
            e10_map[f] = np.exp(-((x1 + f) * (x1 + f) + x2_sq))

        # Precompute x2 powers
        x2_pow_map = {}
        for py in py_candidates:
            x2_pow_map[py] = x2 ** py

        candidates = []

        # Exact MATLAB-style peaks as a candidate
        try:
            t1_exact = (1.0 - x1) ** 2 * e01_map[1.0]
            t2_exact = (x1 / 5.0 - x1 ** 3 - x2_pow_map[5]) * e00
            t3_exact = e10_map[1.0]
            pred_exact = 3.0 * t1_exact - 10.0 * t2_exact - (1.0 / 3.0) * t3_exact
            mse_exact = float(np.mean((y - pred_exact) ** 2))
            expr_exact = "3*(1 - x1)**2*exp(-x1**2 - (x2 + 1)**2) - 10*(x1/5 - x1**3 - x2**5)*exp(-x1**2 - x2**2) - 1/3*exp(-(x1 + 1)**2 - x2**2)"
            comp_exact = self._compute_complexity(expr_exact)
            candidates.append({
                "mse": mse_exact,
                "expr": expr_exact,
                "pred": pred_exact,
                "complexity": comp_exact if comp_exact is not None else 0
            })
        except Exception:
            pass

        # Fit linear coefficients for template basis functions across parameter grid
        for b1 in b1_candidates:
            e01 = e01_map[b1]
            base_t1 = (1.0 - x1) ** 2 * e01
            for f in f_candidates:
                e10 = e10_map[f]
                base_t3 = e10
                for py in py_candidates:
                    x2p = x2_pow_map[py]
                    base_t2 = (x1 / 5.0 - x1 ** 3 - x2p) * e00

                    # Fit without constant
                    A3 = np.column_stack([base_t1, base_t2, base_t3])
                    try:
                        coef3, _, _, _ = np.linalg.lstsq(A3, y, rcond=None)
                        a3, b3, c3 = coef3
                        pred3 = A3 @ coef3
                        mse3 = float(np.mean((y - pred3) ** 2))
                        expr3 = self._build_expression(a3, b3, c3, b1, f, py, use_const=False, d0=0.0)
                        comp3 = self._compute_complexity(expr3)
                        candidates.append({
                            "mse": mse3,
                            "expr": expr3,
                            "pred": pred3,
                            "complexity": comp3 if comp3 is not None else 0
                        })
                    except Exception:
                        pass

                    # Fit with constant
                    A4 = np.column_stack([base_t1, base_t2, base_t3, ones])
                    try:
                        coef4, _, _, _ = np.linalg.lstsq(A4, y, rcond=None)
                        a4, b4, c4, d0 = coef4
                        pred4 = A4 @ coef4
                        mse4 = float(np.mean((y - pred4) ** 2))
                        expr4 = self._build_expression(a4, b4, c4, b1, f, py, use_const=True, d0=d0)
                        comp4 = self._compute_complexity(expr4)
                        candidates.append({
                            "mse": mse4,
                            "expr": expr4,
                            "pred": pred4,
                            "complexity": comp4 if comp4 is not None else 0
                        })
                    except Exception:
                        pass

        # Also include a simple linear baseline as a fallback candidate
        try:
            A_lin = np.column_stack([x1, x2, np.ones_like(x1)])
            coef_lin, _, _, _ = np.linalg.lstsq(A_lin, y, rcond=None)
            aL, bL, cL = coef_lin
            pred_lin = A_lin @ coef_lin
            mse_lin = float(np.mean((y - pred_lin) ** 2))
            expr_lin = f"{self._format_float(aL)}*x1 + {self._format_float(bL)}*x2 + {self._format_float(cL)}"
            comp_lin = self._compute_complexity(expr_lin)
            candidates.append({
                "mse": mse_lin,
                "expr": expr_lin,
                "pred": pred_lin,
                "complexity": comp_lin if comp_lin is not None else 0
            })
        except Exception:
            pass

        # Choose best candidate by MSE, ties broken by lower complexity
        if not candidates:
            # Fallback very simple expression
            expression = "x1 + x2"
            predictions = X[:, 0] + X[:, 1]
            return {
                "expression": expression,
                "predictions": predictions.tolist(),
                "details": {}
            }

        candidates.sort(key=lambda d: (d["mse"], d["complexity"]))
        best = candidates[0]
        expression = best["expr"]
        predictions = best["pred"]
        details = {"complexity": best["complexity"]}

        return {
            "expression": expression,
            "predictions": predictions.tolist(),
            "details": details
        }
