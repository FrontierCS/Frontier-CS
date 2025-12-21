import numpy as np
from sympy import sympify, Add, Mul, Pow, sin as sym_sin, cos as sym_cos, exp as sym_exp, log as sym_log

class Solution:
    def __init__(self, **kwargs):
        self.max_terms = int(kwargs.get("max_terms", 6))
        self.tol_rel = float(kwargs.get("tol_rel", 1e-6))
        self.coeff_tol = float(kwargs.get("coeff_tol", 1e-10))
        self.random_state = kwargs.get("random_state", 42)

    def _build_features(self, x1, x2):
        # Precompute base trigs
        s1 = np.sin(x1)
        c1 = np.cos(x1)
        s2 = np.sin(x2)
        c2 = np.cos(x2)
        s12 = np.sin(x1 + x2)
        c12 = np.cos(x1 + x2)
        s1m2 = np.sin(x1 - x2)
        c1m2 = np.cos(x1 - x2)
        s2x1 = np.sin(2 * x1)
        c2x1 = np.cos(2 * x1)
        s2x2 = np.sin(2 * x2)
        c2x2 = np.cos(2 * x2)

        features = [
            ("sin(x1)", s1),
            ("cos(x1)", c1),
            ("sin(x2)", s2),
            ("cos(x2)", c2),
            ("x1", x1),
            ("x2", x2),
            ("sin(x1)*cos(x2)", s1 * c2),
            ("cos(x1)*sin(x2)", c1 * s2),
            ("sin(x1)*sin(x2)", s1 * s2),
            ("cos(x1)*cos(x2)", c1 * c2),
            ("sin(x1 + x2)", s12),
            ("cos(x1 + x2)", c12),
            ("sin(x1 - x2)", s1m2),
            ("cos(x1 - x2)", c1m2),
            ("sin(2*x1)", s2x1),
            ("cos(2*x1)", c2x1),
            ("sin(2*x2)", s2x2),
            ("cos(2*x2)", c2x2),
        ]
        exprs = [e for e, _ in features]
        F = np.column_stack([v for _, v in features])
        return F, exprs

    def _omp_select(self, F, y, max_terms, tol_rel):
        n, m = F.shape
        # Normalize columns for correlation selection (but refit on original)
        col_norms = np.sqrt(np.sum(F * F, axis=0))
        col_norms[col_norms == 0] = 1.0

        selected = []
        best_selected = []
        best_coef = None
        best_mse = np.inf

        A_intercept = np.ones((n, 1))
        # initial fit with only intercept
        coef_intercept = np.linalg.lstsq(A_intercept, y, rcond=None)[0]
        y_pred = A_intercept @ coef_intercept
        residual = y - y_pred
        mse_prev = np.mean(residual ** 2)
        best_mse = mse_prev
        best_coef = coef_intercept
        best_selected = []

        y_var = float(np.var(y)) + 1e-15
        tol_abs = max(tol_rel * y_var, 1e-12)

        for _ in range(max_terms):
            # Correlation with residual
            corrs = (F.T @ residual) / col_norms
            corrs_abs = np.abs(corrs)
            # Mask already selected
            if selected:
                mask = np.ones(m, dtype=bool)
                mask[selected] = False
                corrs_abs = corrs_abs * mask
            # Choose best new feature
            j = int(np.argmax(corrs_abs))
            if j in selected:
                # No progress possible
                break
            selected.append(j)

            # Refit with intercept + all selected
            A = np.column_stack([A_intercept, F[:, selected]])
            coef = np.linalg.lstsq(A, y, rcond=None)[0]
            y_pred = A @ coef
            residual = y - y_pred
            mse = np.mean(residual ** 2)

            improvement = mse_prev - mse
            if improvement < tol_abs:
                # No meaningful improvement; revert selection
                selected.pop()
                break

            mse_prev = mse
            if mse < best_mse:
                best_mse = mse
                best_coef = coef.copy()
                best_selected = selected.copy()

            if mse < 1e-12:
                break

        if best_coef is None:
            # Fallback to intercept only
            best_coef = np.array([np.mean(y)])
            best_selected = []

        return best_coef, best_selected

    def _format_number(self, x):
        return f"{x:.12g}"

    def _build_expression(self, coef, exprs, selected, coeff_tol):
        # coef: [intercept, coeffs...]
        parts = []
        # Intercept
        c0 = float(coef[0])
        if abs(c0) > coeff_tol:
            parts.append(self._format_number(c0))

        # Terms
        for k, j in enumerate(selected):
            c = float(coef[k + 1])
            if abs(c) <= coeff_tol:
                continue
            term = exprs[j]
            c_abs = abs(c)
            # Determine coefficient string
            if abs(c_abs - 1.0) <= 1e-10:
                term_str = term
                sign = "-" if c < 0 else "+"
            else:
                c_str = self._format_number(c_abs)
                term_str = f"{c_str}*{term}"
                sign = "-" if c < 0 else "+"

            if not parts:
                # First part: include sign if negative
                if sign == "-":
                    parts.append(f"-{term_str}" if term_str[0] != "-" else term_str)
                else:
                    parts.append(term_str)
            else:
                parts.append(f" {sign} {term_str}")

        if not parts:
            # No terms; return zero
            return "0"
        return "".join(parts)

    def _compute_complexity(self, expr_str):
        try:
            expr = sympify(expr_str)
        except Exception:
            return None

        def count_ops(e):
            if e.is_Atom:
                return (0, 0)
            unary = 0
            binary = 0
            f = e.func
            if f in (sym_sin, sym_cos, sym_exp, sym_log):
                unary += 1
            elif f is Add:
                # n-1 binary ops for n-ary addition
                binary += max(len(e.args) - 1, 0)
            elif f is Mul:
                # n-1 binary ops for n-ary multiplication
                binary += max(len(e.args) - 1, 0)
            elif f is Pow:
                binary += 1
            # Recursively count in args
            for arg in e.args:
                b, u = count_ops(arg)
                binary += b
                unary += u
            return (binary, unary)

        b, u = count_ops(expr)
        return int(2 * b + u)

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        X = np.asarray(X, dtype=float)
        y = np.asarray(y, dtype=float).reshape(-1)
        if X.shape[1] < 2:
            # Pad with zeros if needed
            pad = np.zeros((X.shape[0], 2 - X.shape[1]))
            X = np.hstack([X, pad])

        x1 = X[:, 0]
        x2 = X[:, 1]

        # Special case: near-constant y
        if float(np.var(y)) < 1e-14:
            c = float(np.mean(y))
            expression = self._format_number(c)
            predictions = np.full_like(y, c)
            details = {"complexity": self._compute_complexity(expression)}
            return {"expression": expression, "predictions": predictions.tolist(), "details": details}

        F, exprs = self._build_features(x1, x2)
        coef, selected = self._omp_select(F, y, self.max_terms, self.tol_rel)

        # Prune very small coefficients
        coef_pruned = coef.copy()
        # intercept
        if abs(coef_pruned[0]) <= self.coeff_tol:
            coef_pruned[0] = 0.0
        # features
        kept_selected = []
        kept_coefs = [coef_pruned[0]]
        for k, j in enumerate(selected):
            if abs(coef_pruned[k + 1]) > self.coeff_tol:
                kept_selected.append(j)
                kept_coefs.append(coef_pruned[k + 1])

        # If everything got pruned except maybe intercept, refit with kept to ensure stable predictions
        A = np.ones((X.shape[0], 1))
        if kept_selected:
            A = np.column_stack([A, F[:, kept_selected]])
        # Refit to avoid drift due to pruning selection differences
        if kept_selected:
            coef_refit = np.linalg.lstsq(A, y, rcond=None)[0]
        else:
            coef_refit = np.array([np.mean(y)])

        expression = self._build_expression(coef_refit, exprs, kept_selected, self.coeff_tol)
        predictions = (A @ coef_refit)

        details = {"complexity": self._compute_complexity(expression)}

        return {
            "expression": expression,
            "predictions": predictions.tolist(),
            "details": details
        }
