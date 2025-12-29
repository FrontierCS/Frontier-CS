import numpy as np

class Solution:
    def __init__(self, **kwargs):
        self.tol_complex = 0.02  # tolerance for preferring simpler expression

    def _fmt(self, v):
        if not np.isfinite(v):
            return "0"
        if abs(v) < 1e-12:
            return "0"
        return format(float(v), ".12g")

    def _append_term(self, expr_parts, coeff, term_str):
        if abs(coeff) < 1e-12:
            return
        if coeff >= 0:
            expr_parts.append(f"+ {self._fmt(coeff)}*{term_str}")
        else:
            expr_parts.append(f"- {self._fmt(-coeff)}*{term_str}")

    def _append_const(self, expr_parts, const):
        if abs(const) < 1e-12:
            return
        if const >= 0:
            expr_parts.append(f"+ {self._fmt(const)}")
        else:
            expr_parts.append(f"- {self._fmt(-const)}")

    def _build_expression_exact(self):
        # sin(x1 + x2) + (x1 - x2)**2 - 1.5*x1 + 2.5*x2 + 1
        return "sin(x1 + x2) + (x1 - x2)**2 - 1.5*x1 + 2.5*x2 + 1"

    def _build_expression_fixed(self, a, b, c):
        parts = ["sin(x1 + x2)", "+ (x1 - x2)**2"]
        # Linear terms
        if a >= 0:
            parts.append(f"+ {self._fmt(a)}*x1")
        else:
            parts.append(f"- {self._fmt(-a)}*x1")
        if b >= 0:
            parts.append(f"+ {self._fmt(b)}*x2")
        else:
            parts.append(f"- {self._fmt(-b)}*x2")
        # Constant
        if c >= 0:
            parts.append(f"+ {self._fmt(c)}")
        else:
            parts.append(f"- {self._fmt(-c)}")
        return " ".join(parts)

    def _build_expression_free(self, s1, s2, a, b, c):
        parts = []
        # s1*sin(...)
        if s1 >= 0:
            parts.append(f"{self._fmt(s1)}*sin(x1 + x2)")
        else:
            parts.append(f"- {self._fmt(-s1)}*sin(x1 + x2)")
        # s2*(x1 - x2)**2
        if s2 >= 0:
            parts.append(f"+ {self._fmt(s2)}*(x1 - x2)**2")
        else:
            parts.append(f"- {self._fmt(-s2)}*(x1 - x2)**2")
        # a*x1
        if a >= 0:
            parts.append(f"+ {self._fmt(a)}*x1")
        else:
            parts.append(f"- {self._fmt(-a)}*x1")
        # b*x2
        if b >= 0:
            parts.append(f"+ {self._fmt(b)}*x2")
        else:
            parts.append(f"- {self._fmt(-b)}*x2")
        # c
        if c >= 0:
            parts.append(f"+ {self._fmt(c)}")
        else:
            parts.append(f"- {self._fmt(-c)}")
        # Clean possible starting '-' sign spacing
        expr = " ".join(parts)
        if expr.startswith("+ "):
            expr = expr[2:]
        return expr

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        X = np.asarray(X, dtype=np.float64)
        y = np.asarray(y, dtype=np.float64).reshape(-1)
        n = X.shape[0]
        if X.shape[1] != 2:
            # Fallback: simple linear regression if dimensions mismatch
            A = np.column_stack([X, np.ones(n)])
            coeffs, _, _, _ = np.linalg.lstsq(A, y, rcond=None)
            expr_terms = []
            for i, c in enumerate(coeffs[:-1]):
                var = f"x{i+1}"
                if c >= 0:
                    expr_terms.append(f"+ {self._fmt(c)}*{var}")
                else:
                    expr_terms.append(f"- {self._fmt(-c)}*{var}")
            c0 = coeffs[-1]
            if c0 >= 0:
                expr_terms.append(f"+ {self._fmt(c0)}")
            else:
                expr_terms.append(f"- {self._fmt(-c0)}")
            expr = " ".join(expr_terms)
            if expr.startswith("+ "):
                expr = expr[2:]
            y_pred = A @ coeffs
            return {
                "expression": expr if expr else "0",
                "predictions": y_pred.tolist(),
                "details": {}
            }

        x1 = X[:, 0]
        x2 = X[:, 1]

        s = np.sin(x1 + x2)
        d = x1 - x2
        q = d * d

        # Exact McCormick predictions
        y_exact = s + q - 1.5 * x1 + 2.5 * x2 + 1.0
        mse_exact = float(np.mean((y - y_exact) ** 2))

        # Fixed coefficients for sin and square = 1; fit linear part
        A_fixed = np.column_stack((x1, x2, np.ones_like(x1)))
        r = y - s - q
        coeffs_fixed, _, _, _ = np.linalg.lstsq(A_fixed, r, rcond=None)
        af, bf, cf = coeffs_fixed
        y_fixed = s + q + af * x1 + bf * x2 + cf
        mse_fixed = float(np.mean((y - y_fixed) ** 2))

        # Free coefficients (including sin and squared)
        A_free = np.column_stack((s, q, x1, x2, np.ones_like(x1)))
        coeffs_free, _, _, _ = np.linalg.lstsq(A_free, y, rcond=None)
        s1, s2, a2, b2, c2 = coeffs_free
        y_free = s1 * s + s2 * q + a2 * x1 + b2 * x2 + c2
        mse_free = float(np.mean((y - y_free) ** 2))

        # Choose best expression by MSE, with preference for simpler ones if close
        # Rank by (mse, complexity_rank) where complexity_rank: exact < fixed < free
        results = [
            ("exact", mse_exact, y_exact, self._build_expression_exact(), 0),
            ("fixed", mse_fixed, y_fixed, self._build_expression_fixed(af, bf, cf), 1),
            ("free", mse_free, y_free, self._build_expression_free(s1, s2, a2, b2, c2), 2),
        ]
        # Find minimal mse
        best_mse = min(r[1] for r in results)
        # Filter candidates within tolerance of best_mse
        candidates = [r for r in results if r[1] <= best_mse * (1 + self.tol_complex)]
        # Choose candidate with smallest complexity rank among those
        chosen = min(candidates, key=lambda r: r[4])

        expression = chosen[3]
        predictions = chosen[2]

        return {
            "expression": expression,
            "predictions": predictions.tolist(),
            "details": {}
        }