import numpy as np
from itertools import combinations

class Solution:
    def __init__(self, **kwargs):
        self.kwargs = kwargs

    class _Feature:
        __slots__ = ("expr", "values", "unary", "binary")
        def __init__(self, expr: str, values: np.ndarray, unary: int, binary: int):
            self.expr = expr
            self.values = values
            self.unary = unary
            self.binary = binary

    @staticmethod
    def _fmt_float(x: float) -> str:
        if np.isnan(x):
            return "nan"
        if np.isposinf(x):
            return "inf"
        if np.isneginf(x):
            return "-inf"
        s = format(float(x), ".12g")
        if s == "-0":
            s = "0"
        return s

    @staticmethod
    def _safe_solve(G: np.ndarray, b: np.ndarray) -> np.ndarray:
        try:
            return np.linalg.solve(G, b)
        except np.linalg.LinAlgError:
            return np.linalg.lstsq(G, b, rcond=None)[0]

    @staticmethod
    def _mse_from_beta(beta: np.ndarray, G: np.ndarray, b: np.ndarray, yTy: float, n: int) -> float:
        Gb = G @ beta
        sse = yTy - 2.0 * float(beta @ b) + float(beta @ Gb)
        if sse < 0.0 and sse > -1e-9:
            sse = 0.0
        return float(sse) / float(n)

    def _build_features(self, x1: np.ndarray, x2: np.ndarray):
        feats = []

        def add(expr, vals, unary, binary):
            feats.append(self._Feature(expr, vals, unary, binary))

        # Linear terms
        add("x1", x1, unary=0, binary=0)
        add("x2", x2, unary=0, binary=0)

        # Trig terms: k in {1, 2, 0.5}
        for k in (1.0, 2.0, 0.5):
            if k == 1.0:
                add("sin(x1)", np.sin(x1), unary=1, binary=0)
                add("cos(x1)", np.cos(x1), unary=1, binary=0)
                add("sin(x2)", np.sin(x2), unary=1, binary=0)
                add("cos(x2)", np.cos(x2), unary=1, binary=0)
            else:
                ks = self._fmt_float(k)
                add(f"sin({ks}*x1)", np.sin(k * x1), unary=1, binary=1)
                add(f"cos({ks}*x1)", np.cos(k * x1), unary=1, binary=1)
                add(f"sin({ks}*x2)", np.sin(k * x2), unary=1, binary=1)
                add(f"cos({ks}*x2)", np.cos(k * x2), unary=1, binary=1)

        # Sum/diff trig
        x1px2 = x1 + x2
        x1mx2 = x1 - x2
        add("sin(x1 + x2)", np.sin(x1px2), unary=1, binary=1)
        add("cos(x1 + x2)", np.cos(x1px2), unary=1, binary=1)
        add("sin(x1 - x2)", np.sin(x1mx2), unary=1, binary=1)
        add("cos(x1 - x2)", np.cos(x1mx2), unary=1, binary=1)

        # Products
        sx1 = np.sin(x1)
        cx1 = np.cos(x1)
        sx2 = np.sin(x2)
        cx2 = np.cos(x2)
        add("sin(x1)*cos(x2)", sx1 * cx2, unary=2, binary=1)
        add("cos(x1)*sin(x2)", cx1 * sx2, unary=2, binary=1)
        add("sin(x1)*sin(x2)", sx1 * sx2, unary=2, binary=1)
        add("cos(x1)*cos(x2)", cx1 * cx2, unary=2, binary=1)

        return feats

    def _expression_and_complexity(self, subset, beta, features, intercept_idx):
        # subset: list of feature indices; beta aligned with subset + intercept at end
        coef_terms = []
        const = beta[-1]
        for j, fi in enumerate(subset):
            a = beta[j]
            if a == 0.0:
                continue
            coef_terms.append((fi, a))

        # Complexity estimation (C = 2*binary + unary)
        unary = 0
        binary = 0
        term_count = 0

        for fi, a in coef_terms:
            f = features[fi]
            unary += f.unary
            binary += f.binary
            if not (a == 1.0 or a == -1.0):
                binary += 1  # multiplication by coefficient
            term_count += 1

        if const != 0.0:
            term_count += 1

        if term_count >= 2:
            binary += (term_count - 1)  # additions/subtractions

        C = int(2 * binary + unary)

        # Build expression string
        parts = []

        def maybe_paren(e: str) -> str:
            if ("+" in e) or ("-" in e) or (" " in e):
                return f"({e})"
            return e

        def add_term(sign: str, term: str):
            if not parts:
                if sign == "-":
                    parts.append("-" + term)
                else:
                    parts.append(term)
            else:
                parts.append(f" {sign} {term}")

        for fi, a in coef_terms:
            expr = features[fi].expr
            if a < 0:
                sign = "-"
                aa = -a
            else:
                sign = "+"
                aa = a

            if aa == 1.0:
                term = maybe_paren(expr)
            else:
                term = f"{self._fmt_float(aa)}*{maybe_paren(expr)}"
            add_term(sign, term)

        if const != 0.0 or not parts:
            c = const
            if c < 0:
                sign = "-"
                cc = -c
            else:
                sign = "+"
                cc = c
            term = self._fmt_float(cc)
            add_term(sign, term)

        expression = "".join(parts).strip()
        if expression == "":
            expression = "0"

        return expression, C

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        X = np.asarray(X)
        y = np.asarray(y).reshape(-1)
        n = int(X.shape[0])
        if n == 0:
            return {"expression": "0", "predictions": [], "details": {"complexity": 0}}

        x1 = X[:, 0].astype(np.float64, copy=False)
        x2 = X[:, 1].astype(np.float64, copy=False)
        y = y.astype(np.float64, copy=False)

        features = self._build_features(x1, x2)
        m = len(features)
        intercept_idx = m

        F = np.column_stack([f.values for f in features]).astype(np.float64, copy=False)
        ones = np.ones((n, 1), dtype=np.float64)
        Z = np.hstack([F, ones])

        gram = Z.T @ Z
        Zy = Z.T @ y
        yTy = float(y @ y)

        # Evaluate all subsets up to size 3
        results = []
        sizes = (0, 1, 2, 3)
        for k in sizes:
            if k == 0:
                subset = ()
                idx = (intercept_idx,)
                G = gram[np.ix_(idx, idx)]
                b = Zy[list(idx)]
                beta = self._safe_solve(G, b)
                mse = self._mse_from_beta(beta, G, b, yTy, n)
                results.append((mse, subset, beta))
                continue

            for subset in combinations(range(m), k):
                idx = list(subset) + [intercept_idx]
                G = gram[np.ix_(idx, idx)]
                b = Zy[idx]
                beta = self._safe_solve(G, b)
                mse = self._mse_from_beta(beta, G, b, yTy, n)
                results.append((mse, subset, beta))

        results.sort(key=lambda t: t[0])
        top = results[:50] if len(results) > 50 else results

        y_scale = float(np.max(np.abs(y))) if n > 0 else 1.0
        coef_zero_tol = max(1e-12, 1e-10 * (y_scale + 1.0))
        snap_candidates = (0.0, 1.0, -1.0, 2.0, -2.0, 0.5, -0.5)

        best = None
        best_mse = None
        best_C = None
        best_subset = None
        best_beta = None

        for mse0, subset0, beta0 in top:
            subset = list(subset0)
            beta = beta0.copy()
            # Prune tiny coefficients then refit on reduced subset
            pruned_subset = []
            for j, fi in enumerate(subset):
                if abs(beta[j]) >= coef_zero_tol:
                    pruned_subset.append(fi)

            # Always keep intercept during refit; later may prune if near 0
            subset = pruned_subset
            idx = subset + [intercept_idx]
            G = gram[np.ix_(idx, idx)]
            b = Zy[idx]
            beta = self._safe_solve(G, b)
            mse = self._mse_from_beta(beta, G, b, yTy, n)

            # Snap coefficients conservatively
            mse_allow = mse * (1.0 + 1e-6) + 1e-12
            beta_snapped = beta.copy()
            for j in range(len(beta_snapped)):
                v = float(beta_snapped[j])
                best_v = v
                best_mse_local = mse
                for c in snap_candidates:
                    if c == v:
                        continue
                    # Only try if already close
                    if abs(v - c) > max(1e-7, 1e-6 * max(1.0, abs(v))):
                        continue
                    trial = beta_snapped.copy()
                    trial[j] = c
                    mse_trial = self._mse_from_beta(trial, G, b, yTy, n)
                    if mse_trial <= mse_allow and mse_trial <= best_mse_local + 1e-15:
                        best_mse_local = mse_trial
                        best_v = c
                beta_snapped[j] = best_v

            # Drop snapped zeros and refit again (without snapping) for best SSE
            subset2 = []
            for j, fi in enumerate(subset):
                if beta_snapped[j] != 0.0 and abs(beta_snapped[j]) >= coef_zero_tol:
                    subset2.append(fi)

            idx2 = subset2 + [intercept_idx]
            G2 = gram[np.ix_(idx2, idx2)]
            b2 = Zy[idx2]
            beta2 = self._safe_solve(G2, b2)
            mse2 = self._mse_from_beta(beta2, G2, b2, yTy, n)

            # Now attempt snapping on refit solution (final aesthetic), without refit
            beta_final = beta2.copy()
            mse_allow2 = mse2 * (1.0 + 1e-6) + 1e-12
            for j in range(len(beta_final)):
                v = float(beta_final[j])
                best_v = v
                best_mse_local = mse2
                for c in snap_candidates:
                    if c == v:
                        continue
                    if abs(v - c) > max(1e-7, 1e-6 * max(1.0, abs(v))):
                        continue
                    trial = beta_final.copy()
                    trial[j] = c
                    mse_trial = self._mse_from_beta(trial, G2, b2, yTy, n)
                    if mse_trial <= mse_allow2 and mse_trial <= best_mse_local + 1e-15:
                        best_mse_local = mse_trial
                        best_v = c
                beta_final[j] = best_v

            # Prune near-zero intercept if possible (after snapping)
            if abs(beta_final[-1]) < coef_zero_tol:
                beta_final[-1] = 0.0

            expr, C = self._expression_and_complexity(subset2, beta_final, features, intercept_idx)

            if best is None:
                best = expr
                best_mse = mse2
                best_C = C
                best_subset = subset2
                best_beta = beta_final
            else:
                # Prefer lower MSE; if similar, prefer lower complexity
                if mse2 < best_mse - 1e-12:
                    best = expr
                    best_mse = mse2
                    best_C = C
                    best_subset = subset2
                    best_beta = beta_final
                else:
                    if mse2 <= best_mse * (1.0 + 1e-7) + 1e-12:
                        if C < best_C:
                            best = expr
                            best_mse = mse2
                            best_C = C
                            best_subset = subset2
                            best_beta = beta_final

        # Compute predictions for best
        pred = np.full(n, float(best_beta[-1]), dtype=np.float64)
        for j, fi in enumerate(best_subset):
            pred += float(best_beta[j]) * features[fi].values

        return {
            "expression": best,
            "predictions": pred.tolist(),
            "details": {"complexity": int(best_C)}
        }