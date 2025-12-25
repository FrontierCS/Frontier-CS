import numpy as np
import sympy as sp


def _format_float(x: float) -> str:
    if not np.isfinite(x):
        return "0.0"
    xr = float(x)
    if abs(xr) < 1e-14:
        return "0"
    xi = round(xr)
    if abs(xr - xi) < 1e-12 and abs(xi) < 1e12:
        return str(int(xi))
    return format(xr, ".12g")


def _sympy_complexity(expr_str: str) -> int:
    try:
        expr = sp.sympify(expr_str, locals={"sin": sp.sin, "cos": sp.cos, "exp": sp.exp, "log": sp.log})
    except Exception:
        return 0

    def rec(e) -> int:
        if e.is_Atom:
            return 0
        if isinstance(e, sp.Function):
            name = e.func.__name__
            unary = 1 if name in ("sin", "cos", "exp", "log") else 0
            return unary + sum(rec(a) for a in e.args)
        if isinstance(e, sp.Add):
            args = e.args
            return (len(args) - 1) + sum(rec(a) for a in args)
        if isinstance(e, sp.Mul):
            args = e.args
            return (len(args) - 1) + sum(rec(a) for a in args)
        if isinstance(e, sp.Pow):
            return 1 + sum(rec(a) for a in e.args)
        return sum(rec(a) for a in e.args)

    binary_ops = rec(expr)  # counts all ops; will be split below approximately
    # Convert to requested measure: 2*(#binary ops)+(#unary ops).
    # Our rec currently counts unary ops too; adjust by counting unary separately.
    def unary_count(e) -> int:
        if e.is_Atom:
            return 0
        if isinstance(e, sp.Function):
            name = e.func.__name__
            u = 1 if name in ("sin", "cos", "exp", "log") else 0
            return u + sum(unary_count(a) for a in e.args)
        return sum(unary_count(a) for a in e.args)

    u = unary_count(expr)
    b = max(binary_ops - u, 0)
    return int(2 * b + u)


class Solution:
    def __init__(self, **kwargs):
        self.kwargs = kwargs

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        X = np.asarray(X)
        y = np.asarray(y).ravel()

        if X.ndim != 2 or X.shape[1] != 2 or y.shape[0] != X.shape[0]:
            expression = "0"
            return {"expression": expression, "predictions": np.zeros_like(y).tolist(), "details": {"complexity": 0}}

        x1 = X[:, 0].astype(np.float64, copy=False)
        x2 = X[:, 1].astype(np.float64, copy=False)

        # Basis for McCormick-like function: sin(x1+x2), (x1-x2)^2, x1, x2, 1
        t1 = np.sin(x1 + x2)
        t2 = (x1 - x2) ** 2
        ones = np.ones_like(x1)
        A = np.column_stack([t1, t2, x1, x2, ones])

        try:
            coeffs, _, _, _ = np.linalg.lstsq(A, y, rcond=None)
            coeffs = coeffs.astype(np.float64, copy=False)
        except Exception:
            coeffs = np.array([1.0, 1.0, -1.5, 2.5, 1.0], dtype=np.float64)

        # Snap to canonical McCormick coefficients if extremely close
        canonical = np.array([1.0, 1.0, -1.5, 2.5, 1.0], dtype=np.float64)
        if np.all(np.isfinite(coeffs)) and np.max(np.abs(coeffs - canonical)) < 1e-10:
            coeffs = canonical.copy()

        c1, c2, c3, c4, c5 = (float(coeffs[0]), float(coeffs[1]), float(coeffs[2]), float(coeffs[3]), float(coeffs[4]))

        # Build expression, omitting near-zero terms
        terms = []
        if abs(c1) > 1e-14:
            terms.append(f"{_format_float(c1)}*sin(x1 + x2)")
        if abs(c2) > 1e-14:
            terms.append(f"{_format_float(c2)}*(x1 - x2)**2")
        if abs(c3) > 1e-14:
            terms.append(f"{_format_float(c3)}*x1")
        if abs(c4) > 1e-14:
            terms.append(f"{_format_float(c4)}*x2")
        if abs(c5) > 1e-14 or not terms:
            terms.append(f"{_format_float(c5)}")

        expression = " + ".join(terms).replace("+ -", "- ")

        # Predictions
        preds = c1 * t1 + c2 * t2 + c3 * x1 + c4 * x2 + c5

        details = {"complexity": _sympy_complexity(expression)}
        return {"expression": expression, "predictions": preds.tolist(), "details": details}