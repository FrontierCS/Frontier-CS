import numpy as np
import itertools
import sympy as sp


class Solution:
    def __init__(self, **kwargs):
        self.random_state = int(kwargs.get("random_state", 0))
        self.max_nonconst_terms = int(kwargs.get("max_nonconst_terms", 5))
        self.search_sample_size = int(kwargs.get("search_sample_size", 5000))
        self.coef_prune_rel = float(kwargs.get("coef_prune_rel", 1e-10))
        self.coef_snap_rtol = float(kwargs.get("coef_snap_rtol", 1e-6))
        self.coef_snap_max_den = int(kwargs.get("coef_snap_max_den", 12))
        self.use_simplify = bool(kwargs.get("use_simplify", True))

    @staticmethod
    def _safe_sin(x):
        return np.sin(x)

    @staticmethod
    def _safe_cos(x):
        return np.cos(x)

    def _build_library(self, X):
        x1 = X[:, 0]
        x2 = X[:, 1]

        s1 = self._safe_sin(x1)
        c1 = self._safe_cos(x1)
        s2 = self._safe_sin(x2)
        c2 = self._safe_cos(x2)

        two_x1 = 2.0 * x1
        two_x2 = 2.0 * x2

        s1_2 = self._safe_sin(two_x1)
        c1_2 = self._safe_cos(two_x1)
        s2_2 = self._safe_sin(two_x2)
        c2_2 = self._safe_cos(two_x2)

        x1px2 = x1 + x2
        x1mx2 = x1 - x2
        sp12 = self._safe_sin(x1px2)
        cp12 = self._safe_cos(x1px2)
        sm12 = self._safe_sin(x1mx2)
        cm12 = self._safe_cos(x1mx2)

        Phi = np.column_stack(
            [
                np.ones_like(x1),  # 0
                x1,  # 1
                x2,  # 2
                s1,  # 3
                c1,  # 4
                s2,  # 5
                c2,  # 6
                s1_2,  # 7
                c1_2,  # 8
                s2_2,  # 9
                c2_2,  # 10
                sp12,  # 11
                cp12,  # 12
                sm12,  # 13
                cm12,  # 14
                s1 * s2,  # 15
                s1 * c2,  # 16
                c1 * s2,  # 17
                c1 * c2,  # 18
            ]
        ).astype(np.float64, copy=False)

        basis = [
            {"expr": "1", "unary": 0, "binary": 0},
            {"expr": "x1", "unary": 0, "binary": 0},
            {"expr": "x2", "unary": 0, "binary": 0},
            {"expr": "sin(x1)", "unary": 1, "binary": 0},
            {"expr": "cos(x1)", "unary": 1, "binary": 0},
            {"expr": "sin(x2)", "unary": 1, "binary": 0},
            {"expr": "cos(x2)", "unary": 1, "binary": 0},
            {"expr": "sin(2*x1)", "unary": 1, "binary": 1},
            {"expr": "cos(2*x1)", "unary": 1, "binary": 1},
            {"expr": "sin(2*x2)", "unary": 1, "binary": 1},
            {"expr": "cos(2*x2)", "unary": 1, "binary": 1},
            {"expr": "sin(x1 + x2)", "unary": 1, "binary": 1},
            {"expr": "cos(x1 + x2)", "unary": 1, "binary": 1},
            {"expr": "sin(x1 - x2)", "unary": 1, "binary": 1},
            {"expr": "cos(x1 - x2)", "unary": 1, "binary": 1},
            {"expr": "sin(x1)*sin(x2)", "unary": 2, "binary": 1},
            {"expr": "sin(x1)*cos(x2)", "unary": 2, "binary": 1},
            {"expr": "cos(x1)*sin(x2)", "unary": 2, "binary": 1},
            {"expr": "cos(x1)*cos(x2)", "unary": 2, "binary": 1},
        ]
        return Phi, basis

    def _snap_coef(self, a):
        if not np.isfinite(a):
            return 0.0
        if abs(a) < 1e-15:
            return 0.0

        near_int = np.round(a)
        if abs(a - near_int) <= self.coef_snap_rtol * max(1.0, abs(a)):
            return float(near_int)

        best = float(a)
        best_err = abs(a - best)
        for den in range(2, max(2, self.coef_snap_max_den) + 1):
            num = np.round(a * den)
            cand = float(num / den)
            err = abs(a - cand)
            if err < best_err and err <= self.coef_snap_rtol * max(1.0, abs(a)):
                best = cand
                best_err = err
        return float(best)

    def _subset_mse_from_gram(self, G, g, yTy, n, cols):
        GSS = G[np.ix_(cols, cols)]
        gS = g[cols]
        try:
            coef = np.linalg.solve(GSS, gS)
        except np.linalg.LinAlgError:
            coef, _, _, _ = np.linalg.lstsq(GSS, gS, rcond=None)
        mse = (yTy - 2.0 * float(coef @ gS) + float(coef @ (GSS @ coef))) / float(n)
        if mse < 0 and mse > -1e-12:
            mse = 0.0
        return float(mse), np.asarray(coef, dtype=np.float64)

    def _estimate_complexity(self, cols, coef, basis):
        if coef.size == 0:
            return 0

        max_abs = float(np.max(np.abs(coef))) if coef.size else 0.0
        thr = self.coef_prune_rel * max(1.0, max_abs)

        kept = []
        snapped = []
        for j, c in enumerate(coef):
            cs = self._snap_coef(float(c))
            if abs(cs) > thr:
                kept.append(j)
                snapped.append(cs)

        if not kept:
            return 0

        unary = 0
        binary = 0

        # additions between kept terms
        binary += max(0, len(kept) - 1)

        for jj, cs in zip(kept, snapped):
            idx = cols[jj]
            unary += int(basis[idx]["unary"])
            binary += int(basis[idx]["binary"])

            if idx != 0:
                if not (abs(cs - 1.0) <= self.coef_snap_rtol or abs(cs + 1.0) <= self.coef_snap_rtol):
                    binary += 1

        C = 2 * binary + unary
        return int(C)

    def _sympy_complexity(self, sym_expr):
        unary = 0
        binary = 0
        for node in sp.preorder_traversal(sym_expr):
            if isinstance(node, sp.Function):
                if node.func in (sp.sin, sp.cos, sp.exp, sp.log):
                    unary += 1
            elif isinstance(node, sp.Add) or isinstance(node, sp.Mul):
                nargs = len(node.args)
                if nargs >= 2:
                    binary += (nargs - 1)
            elif isinstance(node, sp.Pow):
                binary += 1
        return int(2 * binary + unary)

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        X = np.asarray(X, dtype=np.float64)
        y = np.asarray(y, dtype=np.float64).reshape(-1)
        n = X.shape[0]

        Phi, basis = self._build_library(X)
        m = Phi.shape[1]

        # Drop near-constant / invalid columns except intercept
        col_ok = np.ones(m, dtype=bool)
        col_ok[0] = True
        for j in range(1, m):
            col = Phi[:, j]
            if not np.all(np.isfinite(col)):
                col_ok[j] = False
                continue
            v = float(np.var(col))
            if v < 1e-16:
                col_ok[j] = False

        keep_indices = np.where(col_ok)[0].tolist()
        if 0 not in keep_indices:
            keep_indices = [0] + keep_indices
        keep_map = {old: new for new, old in enumerate(keep_indices)}
        Phi_k = Phi[:, keep_indices]
        basis_k = [basis[i] for i in keep_indices]
        m_k = Phi_k.shape[1]

        # Sample for search if large n
        if n > self.search_sample_size:
            rng = np.random.default_rng(self.random_state)
            idx = rng.choice(n, size=self.search_sample_size, replace=False)
            Phi_s = Phi_k[idx]
            y_s = y[idx]
        else:
            Phi_s = Phi_k
            y_s = y

        ns = Phi_s.shape[0]
        G = Phi_s.T @ Phi_s
        g = Phi_s.T @ y_s
        yTy = float(y_s @ y_s)

        candidate = list(range(1, m_k))
        max_k = max(0, min(self.max_nonconst_terms, len(candidate)))

        best_cols = (0,)
        best_mse = float("inf")
        best_C = 10**9

        # Always include intercept
        for k in range(0, max_k + 1):
            for subset in itertools.combinations(candidate, k):
                cols = (0,) + subset
                mse, coef = self._subset_mse_from_gram(G, g, yTy, ns, cols)
                C = self._estimate_complexity(cols, coef, basis_k)

                if mse < best_mse - 1e-12:
                    best_mse = mse
                    best_cols = cols
                    best_C = C
                elif abs(mse - best_mse) <= 1e-12:
                    if C < best_C:
                        best_cols = cols
                        best_C = C

        # Refit on full data
        A = Phi_k[:, best_cols]
        coef_full, _, _, _ = np.linalg.lstsq(A, y, rcond=None)
        coef_full = np.asarray(coef_full, dtype=np.float64)

        # Prune/snap
        max_abs = float(np.max(np.abs(coef_full))) if coef_full.size else 0.0
        thr = self.coef_prune_rel * max(1.0, max_abs)

        terms = []
        for j, idx in enumerate(best_cols):
            c = self._snap_coef(float(coef_full[j]))
            if abs(c) <= thr:
                continue
            expr = basis_k[idx]["expr"]
            terms.append((c, expr, idx))

        if not terms:
            final_expr_str = "0.0"
            predictions = np.zeros_like(y)
            details = {"complexity": 0}
            return {
                "expression": final_expr_str,
                "predictions": predictions.tolist(),
                "details": details,
            }

        # Build expression string
        parts = []
        for c, expr, idx in terms:
            if idx == 0:
                parts.append(repr(float(c)))
                continue

            if abs(c - 1.0) <= self.coef_snap_rtol:
                parts.append(f"({expr})")
            elif abs(c + 1.0) <= self.coef_snap_rtol:
                parts.append(f"(-({expr}))")
            else:
                cstr = repr(float(c))
                if expr in ("x1", "x2"):
                    parts.append(f"({cstr}*{expr})")
                else:
                    parts.append(f"({cstr}*({expr}))")

        expr_str = " + ".join(parts)

        x1s, x2s = sp.symbols("x1 x2")
        locals_map = {"x1": x1s, "x2": x2s, "sin": sp.sin, "cos": sp.cos, "exp": sp.exp, "log": sp.log}
        try:
            sym_expr = sp.sympify(expr_str, locals=locals_map)
            if self.use_simplify:
                sym_expr = sp.simplify(sym_expr)
            final_expr_str = str(sym_expr)
        except Exception:
            sym_expr = None
            final_expr_str = expr_str

        # Predictions from final expression to match exactly
        if sym_expr is not None:
            f = sp.lambdify((x1s, x2s), sym_expr, modules={"sin": np.sin, "cos": np.cos, "exp": np.exp, "log": np.log})
            predictions = np.asarray(f(X[:, 0], X[:, 1]), dtype=np.float64).reshape(-1)
        else:
            # Fallback: evaluate linear combo
            predictions = A @ coef_full

        # Complexity
        if sym_expr is not None:
            C_final = self._sympy_complexity(sym_expr)
        else:
            # Approx from the selected terms
            cols = best_cols
            C_final = self._estimate_complexity(cols, coef_full, basis_k)

        return {
            "expression": final_expr_str,
            "predictions": predictions.tolist(),
            "details": {"complexity": int(C_final)},
        }