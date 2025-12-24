import numpy as np
import itertools

class Solution:
    def __init__(self, **kwargs):
        pass

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        X = np.asarray(X, dtype=float)
        y = np.asarray(y, dtype=float).ravel()
        n = X.shape[0]

        x1 = X[:, 0]
        x2 = X[:, 1]

        basis_expr_list = []
        basis_values_list = []
        unary_counts = []
        binary_counts = []

        def add_basis(expr, values, unary, binary):
            basis_expr_list.append(expr)
            basis_values_list.append(values)
            unary_counts.append(unary)
            binary_counts.append(binary)

        # Base trigonometric features
        add_basis("sin(x1)", np.sin(x1), 1, 0)
        add_basis("cos(x1)", np.cos(x1), 1, 0)
        add_basis("sin(2*x1)", np.sin(2 * x1), 1, 1)  # 2*x1
        add_basis("cos(2*x1)", np.cos(2 * x1), 1, 1)
        add_basis("sin(x2)", np.sin(x2), 1, 0)
        add_basis("cos(x2)", np.cos(x2), 1, 0)
        add_basis("sin(2*x2)", np.sin(2 * x2), 1, 1)
        add_basis("cos(2*x2)", np.cos(2 * x2), 1, 1)
        add_basis("sin(x1 + x2)", np.sin(x1 + x2), 1, 1)
        add_basis("cos(x1 + x2)", np.cos(x1 + x2), 1, 1)
        add_basis("sin(x1 - x2)", np.sin(x1 - x2), 1, 1)
        add_basis("cos(x1 - x2)", np.cos(x1 - x2), 1, 1)

        F = np.column_stack(basis_values_list)
        m = F.shape[1]
        ones = np.ones(n, dtype=float)

        drop_tol = 1e-8
        int_tol = 1e-4

        def simplify_value(v: float) -> float:
            if not np.isfinite(v):
                return 0.0
            if abs(v) < drop_tol:
                return 0.0
            nint = float(np.round(v))
            if nint != 0.0 and abs(v - nint) <= int_tol * max(1.0, abs(v)):
                return nint
            return float(v)

        def float_to_str(v: float) -> str:
            s = f"{v:.10g}"
            if "e" not in s and "E" not in s and "." in s:
                s = s.rstrip("0").rstrip(".")
            if s == "-0":
                s = "0"
            return s

        best_mse = np.inf
        best_complexity = np.inf
        best_expr = None
        best_pred = None

        max_nonconst_terms = min(3, m)

        for k in range(0, max_nonconst_terms + 1):
            for subset in itertools.combinations(range(m), k):
                cols = 1 + len(subset)
                A = np.empty((n, cols), dtype=float)
                A[:, 0] = ones
                for j, idx in enumerate(subset):
                    A[:, j + 1] = F[:, idx]

                coefs_raw, _, _, _ = np.linalg.lstsq(A, y, rcond=None)
                coefs_simpl = np.array([simplify_value(c) for c in coefs_raw], dtype=float)
                intercept = coefs_simpl[0]
                basis_coefs = coefs_simpl[1:]

                y_pred = np.full(n, intercept, dtype=float)
                for j, idx in enumerate(subset):
                    c = basis_coefs[j]
                    if c != 0.0:
                        y_pred += c * F[:, idx]

                residual = y - y_pred
                mse = float(np.mean(residual * residual))
                if not np.isfinite(mse):
                    continue

                basis_terms = []
                for j, idx in enumerate(subset):
                    c = basis_coefs[j]
                    if c != 0.0:
                        basis_terms.append((idx, c))

                has_intercept = intercept != 0.0

                if not has_intercept and not basis_terms:
                    expr = "0"
                    complexity = 0
                else:
                    n_unary = sum(unary_counts[idx] for idx, _ in basis_terms)
                    n_binary_inner = sum(binary_counts[idx] for idx, _ in basis_terms)
                    n_binary_mul = sum(1 for _, c in basis_terms if abs(c) != 1.0)
                    n_terms_total = (1 if has_intercept else 0) + len(basis_terms)
                    n_binary_plus = max(n_terms_total - 1, 0)
                    n_binary = n_binary_inner + n_binary_mul + n_binary_plus
                    complexity = 2 * n_binary + n_unary

                    parts = []
                    if has_intercept:
                        parts.append(float_to_str(intercept))
                    for idx, c in basis_terms:
                        expr_basis = basis_expr_list[idx]
                        sign = 1 if c >= 0 else -1
                        mag = abs(c)
                        if mag == 1.0:
                            coef_str = None
                        else:
                            coef_str = float_to_str(mag)

                        if not parts:
                            if sign < 0:
                                if coef_str is None:
                                    term = "-" + expr_basis
                                else:
                                    term = "-" + coef_str + "*" + expr_basis
                            else:
                                if coef_str is None:
                                    term = expr_basis
                                else:
                                    term = coef_str + "*" + expr_basis
                        else:
                            connector = " + " if sign > 0 else " - "
                            if coef_str is None:
                                term = connector + expr_basis
                            else:
                                term = connector + coef_str + "*" + expr_basis
                        parts.append(term)
                    expr = "".join(parts)

                if best_expr is None:
                    best_expr = expr
                    best_mse = mse
                    best_complexity = complexity
                    best_pred = y_pred.copy()
                else:
                    rel_tol = 1e-3
                    if mse < best_mse * (1 - rel_tol) - 1e-12:
                        best_expr = expr
                        best_mse = mse
                        best_complexity = complexity
                        best_pred = y_pred.copy()
                    elif abs(mse - best_mse) <= rel_tol * max(best_mse, 1e-12):
                        if complexity < best_complexity:
                            best_expr = expr
                            best_mse = mse
                            best_complexity = complexity
                            best_pred = y_pred.copy()

        if best_expr is None:
            best_expr = "0"
            best_pred = np.zeros_like(y)
            best_complexity = 0

        return {
            "expression": best_expr,
            "predictions": best_pred.tolist(),
            "details": {"complexity": int(best_complexity)},
        }
