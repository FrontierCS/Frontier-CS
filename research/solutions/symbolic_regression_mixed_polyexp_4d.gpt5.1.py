import numpy as np

class Solution:
    def __init__(self, **kwargs):
        pass

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        X = np.asarray(X, dtype=float)
        y = np.asarray(y, dtype=float).ravel()

        expression, predictions, details = self._fit_polynomial_model(X, y, max_degree=5)

        return {
            "expression": expression,
            "predictions": predictions.tolist() if predictions is not None else None,
            "details": details,
        }

    def _fit_polynomial_model(self, X: np.ndarray, y: np.ndarray, max_degree: int):
        n, d = X.shape
        n_vars = 4  # we use the first 4 variables: x1, x2, x3, x4

        exponents_all = self._generate_exponents(n_vars, max_degree)
        exponents_all.sort(key=lambda e: (sum(e), e))

        if not exponents_all:
            # Fallback: simple mean model
            coef = float(np.mean(y))
            expression = self._format_float(coef)
            predictions = np.full_like(y, fill_value=coef, dtype=float)
            details = {
                "method": "polynomial_regression",
                "max_degree_considered": max_degree,
                "selected_degree": 0,
                "num_terms": 1,
            }
            return expression, predictions, details

        max_single_exp = max(max(e) for e in exponents_all)
        xs = [X[:, i] for i in range(n_vars)]
        x_powers = []
        for i in range(n_vars):
            xi = xs[i]
            powers = [np.ones_like(xi)]
            for p in range(1, max_single_exp + 1):
                powers.append(powers[-1] * xi)
            x_powers.append(powers)

        m_total = len(exponents_all)
        A_total = np.empty((n, m_total), dtype=float)
        for j, expo in enumerate(exponents_all):
            term = np.ones(n, dtype=float)
            for i_var, power in enumerate(expo):
                if power > 0:
                    term = term * x_powers[i_var][power]
            A_total[:, j] = term

        candidate_degrees = list(range(1, max_degree + 1))

        kfold = min(5, n)
        if kfold < 2:
            kfold = 1

        rng = np.random.RandomState(42)
        indices = np.arange(n)
        if kfold > 1:
            rng.shuffle(indices)
            splits = np.array_split(indices, kfold)
        else:
            splits = [indices]

        best_score = float("inf")
        best_degree = candidate_degrees[-1]
        best_idx_cols = None

        for D in candidate_degrees:
            idx_cols = [i for i, e in enumerate(exponents_all) if sum(e) <= D]
            Ad = A_total[:, idx_cols]

            if kfold == 1 or n < 2 * len(idx_cols):
                coeffs, _, _, _ = np.linalg.lstsq(Ad, y, rcond=None)
                pred_all = Ad.dot(coeffs)
                mse = float(np.mean((pred_all - y) ** 2))
                score_cv = mse + 1e-6 * len(idx_cols)
            else:
                mses = []
                for i in range(kfold):
                    val_idx = splits[i]
                    if val_idx.size == 0:
                        continue
                    train_idx = np.concatenate([splits[j] for j in range(kfold) if j != i])
                    A_train = Ad[train_idx]
                    y_train = y[train_idx]
                    A_val = Ad[val_idx]
                    y_val = y[val_idx]
                    coeffs, _, _, _ = np.linalg.lstsq(A_train, y_train, rcond=None)
                    pred_val = A_val.dot(coeffs)
                    mse_fold = float(np.mean((pred_val - y_val) ** 2))
                    mses.append(mse_fold)
                if not mses:
                    score_cv = float("inf")
                else:
                    score_cv = float(np.mean(mses)) + 1e-6 * len(idx_cols)

            if score_cv < best_score:
                best_score = score_cv
                best_degree = D
                best_idx_cols = idx_cols

        if best_idx_cols is None:
            best_idx_cols = list(range(m_total))

        A_best = A_total[:, best_idx_cols]
        coeffs_best, _, _, _ = np.linalg.lstsq(A_best, y, rcond=None)
        predictions = A_best.dot(coeffs_best)

        exponents_best = [exponents_all[i] for i in best_idx_cols]

        max_abs_coef = float(np.max(np.abs(coeffs_best))) if coeffs_best.size > 0 else 0.0
        coef_tol = 1e-6 * (max_abs_coef if max_abs_coef > 0.0 else 1.0)

        terms = []
        for coef, expo in zip(coeffs_best, exponents_best):
            if abs(coef) < coef_tol:
                continue
            coef_str = self._format_float(coef)
            mono_str = self._monomial_to_str(expo)
            if mono_str == "1":
                terms.append(f"({coef_str})")
            else:
                terms.append(f"({coef_str})*{mono_str}")

        if not terms:
            expression = "0.0"
        else:
            expression = " + ".join(terms)

        details = {
            "method": "polynomial_regression",
            "max_degree_considered": max_degree,
            "selected_degree": best_degree,
            "num_terms": len(terms),
        }
        return expression, predictions, details

    def _generate_exponents(self, n_vars: int, max_degree: int):
        exponents = []

        def recurse(var_idx, remaining_degree, current):
            if var_idx == n_vars:
                exponents.append(tuple(current))
                return
            for deg in range(remaining_degree + 1):
                current[var_idx] = deg
                recurse(var_idx + 1, remaining_degree - deg, current)

        recurse(0, max_degree, [0] * n_vars)
        return exponents

    def _monomial_to_str(self, exponents):
        var_names = ["x1", "x2", "x3", "x4"]
        factors = []
        for i, power in enumerate(exponents):
            if power == 0:
                continue
            name = var_names[i]
            if power == 1:
                factors.append(name)
            else:
                factors.append(f"{name}**{power}")
        if not factors:
            return "1"
        return "*".join(factors)

    def _format_float(self, x: float) -> str:
        val = float(x)
        if abs(val) < 1e-12:
            return "0.0"
        return f"{val:.12g}"