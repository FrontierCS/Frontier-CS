import numpy as np
import itertools
import sympy as sp

class Solution:
    def __init__(self, **kwargs):
        self.kwargs = kwargs

    @staticmethod
    def _safe_eval_expr(expr: str, x1: np.ndarray, x2: np.ndarray) -> np.ndarray:
        local_dict = {
            "x1": x1,
            "x2": x2,
            "sin": np.sin,
            "cos": np.cos,
            "exp": np.exp,
            "log": np.log,
            "np": None,
        }
        return eval(expr, {"__builtins__": {}}, local_dict)

    @staticmethod
    def _snap_value(v: float) -> float:
        if not np.isfinite(v):
            return v
        av = abs(v)
        if av < 1e-10:
            return 0.0
        candidates = [0.0, 1.0, -1.0, 2.0, -2.0, 0.5, -0.5, 3.0, -3.0, 4.0, -4.0]
        tol = 1e-3
        for c in candidates:
            if abs(v - c) <= tol * max(1.0, av):
                return float(c)
        v_round = float(np.round(v, 12))
        if abs(v - v_round) <= 1e-12 * max(1.0, av):
            return v_round
        return float(v)

    @staticmethod
    def _format_number(v: float) -> str:
        if v == 0.0:
            return "0"
        if v == 1.0:
            return "1"
        if v == -1.0:
            return "-1"
        s = f"{v:.12g}"
        if "e" in s or "E" in s:
            s = f"{v:.16g}"
        return s

    @classmethod
    def _build_expression(cls, term_names, coeffs, intercept) -> str:
        terms = []
        for name, c in zip(term_names, coeffs):
            c = cls._snap_value(float(c))
            if c == 0.0:
                continue
            if c == 1.0:
                terms.append(("+", name))
            elif c == -1.0:
                terms.append(("-", name))
            else:
                coef_str = cls._format_number(abs(c))
                terms.append(("+" if c > 0 else "-", f"{coef_str}*{name}"))

        intercept = cls._snap_value(float(intercept))
        if intercept != 0.0:
            ival = abs(intercept)
            istr = cls._format_number(ival)
            terms.append(("+" if intercept > 0 else "-", istr))

        if not terms:
            return "0"

        sign0, part0 = terms[0]
        expr = part0 if sign0 == "+" else f"-{part0}"
        for sgn, part in terms[1:]:
            expr += f" {'+' if sgn == '+' else '-'} {part}"
        return expr

    @staticmethod
    def _complexity(expression: str) -> int:
        x1s, x2s = sp.symbols("x1 x2")
        locals_map = {
            "x1": x1s,
            "x2": x2s,
            "sin": sp.sin,
            "cos": sp.cos,
            "exp": sp.exp,
            "log": sp.log,
        }
        try:
            e = sp.sympify(expression, locals=locals_map)
        except Exception:
            return 10**9

        unary_funcs = (sp.sin, sp.cos, sp.exp, sp.log)

        def rec(node):
            unary = 0
            binary = 0
            if getattr(node, "func", None) in unary_funcs:
                unary += 1
            if isinstance(node, sp.Add) or isinstance(node, sp.Mul):
                n = len(node.args)
                if n > 1:
                    binary += n - 1
            elif isinstance(node, sp.Pow):
                binary += 1
            for a in getattr(node, "args", ()):
                u, b = rec(a)
                unary += u
                binary += b
            return unary, binary

        u, b = rec(e)
        return int(2 * b + u)

    @staticmethod
    def _select_better(a, b) -> bool:
        # Each is (mse, complexity, expression, extra_dict)
        if a is None:
            return True
        mse_a, comp_a = a[0], a[1]
        mse_b, comp_b = b[0], b[1]
        if mse_b < mse_a * (1.0 - 1e-12):
            return True
        if mse_a < mse_b * (1.0 - 1e-12):
            return False
        if mse_b <= mse_a * (1.0 + 1e-4) and comp_b < comp_a:
            return True
        return False

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        X = np.asarray(X, dtype=np.float64)
        y = np.asarray(y, dtype=np.float64).reshape(-1)
        n = y.size
        if n == 0:
            return {"expression": "0", "predictions": [], "details": {"complexity": 0, "mse": None}}

        x1 = X[:, 0]
        x2 = X[:, 1]

        def mse_of_expr(expr: str):
            try:
                pred = self._safe_eval_expr(expr, x1, x2)
                if pred.shape != y.shape:
                    pred = np.asarray(pred).reshape(y.shape)
                if not np.all(np.isfinite(pred)):
                    return np.inf
                d = pred - y
                return float(np.mean(d * d))
            except Exception:
                return np.inf

        fixed_exprs = [
            "sin(x1) + cos(x2)",
            "sin(x1) - cos(x2)",
            "sin(x1) * cos(x2)",
            "cos(x1) * sin(x2)",
            "sin(x1) + sin(x2)",
            "cos(x1) + cos(x2)",
            "sin(x1) * sin(x2)",
            "cos(x1) * cos(x2)",
            "sin(x1 + x2)",
            "cos(x1 + x2)",
            "sin(x1 - x2)",
            "cos(x1 - x2)",
            "sin(2*x1) + cos(2*x2)",
            "sin(2*x1) + cos(x2)",
            "sin(x1) + cos(2*x2)",
            "sin(2*x1) * cos(2*x2)",
            "sin(2*x1)",
            "cos(2*x2)",
            "sin(x1)",
            "cos(x2)",
        ]

        best = None

        for expr in fixed_exprs:
            mse = mse_of_expr(expr)
            if not np.isfinite(mse):
                continue
            comp = self._complexity(expr)
            cand = (mse, comp, expr, {"method": "fixed"})
            if self._select_better(best, cand):
                best = cand

        # Build term library for small subset linear models
        term_specs = [
            ("sin(x1)", np.sin(x1)),
            ("cos(x1)", np.cos(x1)),
            ("sin(x2)", np.sin(x2)),
            ("cos(x2)", np.cos(x2)),
            ("sin(2*x1)", np.sin(2.0 * x1)),
            ("cos(2*x1)", np.cos(2.0 * x1)),
            ("sin(2*x2)", np.sin(2.0 * x2)),
            ("cos(2*x2)", np.cos(2.0 * x2)),
            ("sin(x1 + x2)", np.sin(x1 + x2)),
            ("cos(x1 + x2)", np.cos(x1 + x2)),
            ("sin(x1 - x2)", np.sin(x1 - x2)),
            ("cos(x1 - x2)", np.cos(x1 - x2)),
            ("sin(x1)*cos(x2)", np.sin(x1) * np.cos(x2)),
            ("cos(x1)*sin(x2)", np.cos(x1) * np.sin(x2)),
            ("sin(x1)*sin(x2)", np.sin(x1) * np.sin(x2)),
            ("cos(x1)*cos(x2)", np.cos(x1) * np.cos(x2)),
        ]
        m = len(term_specs)
        T = np.empty((n, m), dtype=np.float64)
        term_names = []
        for j, (name, arr) in enumerate(term_specs):
            term_names.append(name)
            T[:, j] = np.asarray(arr, dtype=np.float64)

        ones = np.ones(n, dtype=np.float64)
        yTy = float(y @ y)
        onesy = float(ones @ y)
        ones2 = float(n)
        G = T.T @ T  # m x m
        g1 = T.T @ ones  # m
        v = T.T @ y  # m

        ridge = 1e-12

        def fit_subset(idx_tuple):
            idx = np.array(idx_tuple, dtype=np.int32)
            k = idx.size
            Gram = np.empty((k + 1, k + 1), dtype=np.float64)
            rhs = np.empty((k + 1,), dtype=np.float64)

            if k > 0:
                Gss = G[np.ix_(idx, idx)]
                Gram[:k, :k] = Gss
                Gram[:k, k] = g1[idx]
                Gram[k, :k] = g1[idx]
                rhs[:k] = v[idx]
            Gram[k, k] = ones2
            rhs[k] = onesy

            Gram_reg = Gram.copy()
            Gram_reg.flat[:: (k + 2)] += ridge

            try:
                beta = np.linalg.solve(Gram_reg, rhs)
            except np.linalg.LinAlgError:
                beta = np.linalg.lstsq(Gram_reg, rhs, rcond=None)[0]

            SSE = yTy - 2.0 * float(beta @ rhs) + float(beta @ (Gram @ beta))
            if SSE < 0.0 and SSE > -1e-8:
                SSE = 0.0
            mse = SSE / n
            return beta, mse, Gram, rhs

        # Also consider intercept-only
        mse_intercept = float(np.mean((y - y.mean()) ** 2))
        expr_intercept = self._format_number(float(self._snap_value(float(y.mean()))))
        cand = (mse_intercept, self._complexity(expr_intercept), expr_intercept, {"method": "intercept"})
        if self._select_better(best, cand):
            best = cand

        max_k = 3
        for k in range(1, max_k + 1):
            for comb in itertools.combinations(range(m), k):
                beta, mse, Gram, rhs = fit_subset(comb)

                coeffs = beta[:-1].copy()
                intercept = float(beta[-1])

                # Snap coefficients & recompute mse cheaply
                coeffs_s = np.array([self._snap_value(float(c)) for c in coeffs], dtype=np.float64)
                intercept_s = float(self._snap_value(intercept))
                beta_s = np.concatenate([coeffs_s, np.array([intercept_s], dtype=np.float64)])
                SSE_s = yTy - 2.0 * float(beta_s @ rhs) + float(beta_s @ (Gram @ beta_s))
                if SSE_s < 0.0 and SSE_s > -1e-8:
                    SSE_s = 0.0
                mse_s = SSE_s / n
                if not np.isfinite(mse_s):
                    continue

                names = [term_names[i] for i in comb]
                expr = self._build_expression(names, coeffs_s, intercept_s)

                # Guard: must be valid and finite
                comp = self._complexity(expr)
                cand = (float(mse_s), int(comp), expr, {"method": "subset_linear", "k": k})
                if self._select_better(best, cand):
                    best = cand

        expression = best[2] if best is not None else "0"
        try:
            predictions = self._safe_eval_expr(expression, x1, x2)
            predictions = np.asarray(predictions, dtype=np.float64).reshape(-1)
            if predictions.shape[0] != n or not np.all(np.isfinite(predictions)):
                predictions = None
        except Exception:
            predictions = None

        out = {
            "expression": expression,
            "predictions": None if predictions is None else predictions.tolist(),
            "details": {
                "complexity": None if best is None else int(best[1]),
                "mse": None if best is None else float(best[0]),
            },
        }
        if best is not None and isinstance(best[3], dict):
            out["details"].update(best[3])
        return out