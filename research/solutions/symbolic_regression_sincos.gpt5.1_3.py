import numpy as np
from itertools import combinations


class Solution:
    def __init__(self, **kwargs):
        # Allow overriding thresholds if desired
        self.coef_tol = float(kwargs.get("coef_tol", 1e-8))

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        X = np.asarray(X, dtype=float)
        y = np.asarray(y, dtype=float).ravel()

        if X.ndim != 2 or X.shape[1] < 2:
            raise ValueError("X must be of shape (n_samples, 2)")

        n_samples = X.shape[0]
        if n_samples == 0:
            # Degenerate case: no data
            expression = "0.0"
            return {
                "expression": expression,
                "predictions": [],
                "details": {"complexity": 0},
            }

        x1 = X[:, 0]
        x2 = X[:, 1]

        # Precompute basis functions
        ones = np.ones(n_samples, dtype=float)

        s1 = np.sin(x1)
        c1 = np.cos(x1)
        s2 = np.sin(x2)
        c2 = np.cos(x2)

        s1c2 = s1 * c2
        c1s2 = c1 * s2
        s1s2 = s1 * s2
        c1c2 = c1 * c2

        s1p2 = np.sin(x1 + x2)
        c1p2 = np.cos(x1 + x2)
        s1m2 = np.sin(x1 - x2)
        c1m2 = np.cos(x1 - x2)

        # Basis definitions: name, values, unary_count, binary_count_inside_term
        basis = [
            {"name": "1", "values": ones, "unary": 0, "binary": 0},  # constant
            {"name": "x1", "values": x1, "unary": 0, "binary": 1},
            {"name": "x2", "values": x2, "unary": 0, "binary": 1},
            {"name": "sin(x1)", "values": s1, "unary": 1, "binary": 1},
            {"name": "cos(x1)", "values": c1, "unary": 1, "binary": 1},
            {"name": "sin(x2)", "values": s2, "unary": 1, "binary": 1},
            {"name": "cos(x2)", "values": c2, "unary": 1, "binary": 1},
            {"name": "sin(x1)*cos(x2)", "values": s1c2, "unary": 2, "binary": 2},
            {"name": "cos(x1)*sin(x2)", "values": c1s2, "unary": 2, "binary": 2},
            {"name": "sin(x1)*sin(x2)", "values": s1s2, "unary": 2, "binary": 2},
            {"name": "cos(x1)*cos(x2)", "values": c1c2, "unary": 2, "binary": 2},
            {"name": "sin(x1 + x2)", "values": s1p2, "unary": 1, "binary": 2},
            {"name": "cos(x1 + x2)", "values": c1p2, "unary": 1, "binary": 2},
            {"name": "sin(x1 - x2)", "values": s1m2, "unary": 1, "binary": 2},
            {"name": "cos(x1 - x2)", "values": c1m2, "unary": 1, "binary": 2},
        ]

        # Design matrix with all basis functions
        F_all = np.column_stack([b["values"] for b in basis])

        n_basis = len(basis)  # includes constant at index 0
        indices_main = list(range(1, n_basis))  # exclude constant for subset enumeration

        # Choose max terms (non-constant) adaptively based on dataset size
        if n_samples <= 2000:
            max_terms = 4
        elif n_samples <= 10000:
            max_terms = 3
        else:
            max_terms = 2
        max_terms = min(max_terms, len(indices_main))

        coef_tol = self.coef_tol

        best_mse = np.inf
        best_complexity = np.inf
        best_features_idx = None
        best_coefs = None
        best_predictions = None

        # Enumerate subsets of basis functions (excluding constant), up to max_terms
        for s in range(0, max_terms + 1):
            for subset in combinations(indices_main, s):
                features_idx = (0,) + subset  # always include constant
                G = F_all[:, features_idx]

                coefs_sub, _, _, _ = np.linalg.lstsq(G, y, rcond=None)
                yhat = G @ coefs_sub
                residuals = y - yhat
                mse = float(np.mean(residuals * residuals))

                # Determine which coefficients are effectively non-zero
                nonzero_indices = [j for j, c in enumerate(coefs_sub) if abs(c) > coef_tol]

                if not nonzero_indices:
                    # All coefficients effectively zero: model is y ≈ 0
                    complexity = 0
                else:
                    unary_total = 0
                    binary_mult_total = 0
                    term_count = 0
                    for j in nonzero_indices:
                        basis_idx = features_idx[j]
                        binfo = basis[basis_idx]
                        term_count += 1
                        unary_total += binfo["unary"]
                        binary_mult_total += binfo["binary"]
                    plus_ops = max(term_count - 1, 0)
                    complexity = 2 * (binary_mult_total + plus_ops) + unary_total

                # Select best model: prioritize lower MSE, break ties with lower complexity
                if mse < best_mse - 1e-12:
                    best_mse = mse
                    best_complexity = complexity
                    best_features_idx = features_idx
                    best_coefs = coefs_sub
                    best_predictions = yhat
                elif abs(mse - best_mse) <= 1e-8 * max(1.0, best_mse):
                    if complexity < best_complexity - 1e-9:
                        best_mse = mse
                        best_complexity = complexity
                        best_features_idx = features_idx
                        best_coefs = coefs_sub
                        best_predictions = yhat

        # Fallback in the unlikely event nothing was selected
        if best_features_idx is None or best_coefs is None:
            mean_y = float(np.mean(y))
            expression = f"{mean_y:.12g}"
            predictions = np.full_like(y, mean_y, dtype=float)
            complexity_out = 0
            return {
                "expression": expression,
                "predictions": predictions.tolist(),
                "details": {"complexity": int(complexity_out)},
            }

        # Build final expression from best coefficients, dropping tiny terms
        terms = []
        final_indices = []
        final_coefs = []

        for j, basis_idx in enumerate(best_features_idx):
            coef = best_coefs[j]
            if abs(coef) <= coef_tol:
                continue
            name = basis[basis_idx]["name"]
            if basis_idx == 0:  # constant term
                term_str = f"{coef:.12g}"
            else:
                term_str = f"({coef:.12g})*{name}"
            terms.append(term_str)
            final_indices.append(basis_idx)
            final_coefs.append(coef)

        if not terms:
            # All coefficients below threshold: use mean of y as constant model
            mean_y = float(np.mean(y))
            expression = f"{mean_y:.12g}"
            predictions = np.full_like(y, mean_y, dtype=float)
            complexity_out = 0
        else:
            expression = " + ".join(terms)
            # Compute predictions consistent with the final expression
            predictions = np.zeros_like(y, dtype=float)
            for idx, coef in zip(final_indices, final_coefs):
                predictions += coef * basis[idx]["values"]

            # Recompute complexity for the final, pruned expression
            unary_total = 0
            binary_mult_total = 0
            term_count = len(final_indices)
            for idx in final_indices:
                binfo = basis[idx]
                unary_total += binfo["unary"]
                binary_mult_total += binfo["binary"]
            plus_ops = max(term_count - 1, 0)
            complexity_out = 2 * (binary_mult_total + plus_ops) + unary_total

        return {
            "expression": expression,
            "predictions": predictions.tolist(),
            "details": {"complexity": int(complexity_out)},
        }