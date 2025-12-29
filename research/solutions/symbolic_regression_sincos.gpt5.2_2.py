import numpy as np
import sympy as sp
from itertools import combinations

class Solution:
    def __init__(self, **kwargs):
        self.max_terms = int(kwargs.get("max_terms", 4))
        self.coef_tol = float(kwargs.get("coef_tol", 1e-10))
        self.combine_sincos = bool(kwargs.get("combine_sincos", True))

    @staticmethod
    def _fmt_float(x: float) -> str:
        if not np.isfinite(x):
            return "0.0"
        if abs(x) < 1e-15:
            return "0.0"
        s = f"{x:.12g}"
        if s == "-0":
            s = "0"
        return s

    @staticmethod
    def _safe_eval_expr(expr: str, x1: np.ndarray, x2: np.ndarray) -> np.ndarray:
        env = {
            "__builtins__": {},
            "x1": x1,
            "x2": x2,
            "sin": np.sin,
            "cos": np.cos,
            "exp": np.exp,
            "log": np.log,
        }
        out = eval(expr, env, {})
        if np.isscalar(out):
            return np.full_like(x1, float(out), dtype=np.float64)
        return np.asarray(out, dtype=np.float64)

    @staticmethod
    def _complexity(expr_str: str) -> int:
        locals_map = {"sin": sp.sin, "cos": sp.cos, "exp": sp.exp, "log": sp.log}
        try:
            expr = sp.sympify(expr_str, locals=locals_map)
        except Exception:
            return 10**9

        unary = 0
        binary = 0
        for node in sp.preorder_traversal(expr):
            if isinstance(node, sp.Function) and node.func in (sp.sin, sp.cos, sp.exp, sp.log):
                unary += 1
            if isinstance(node, sp.Add):
                binary += max(0, len(node.args) - 1)
            elif isinstance(node, sp.Mul):
                binary += max(0, len(node.args) - 1)
            elif isinstance(node, sp.Pow):
                binary += 1
        return int(2 * binary + unary)

    def _build_library(self, x1: np.ndarray, x2: np.ndarray):
        n = x1.shape[0]
        cols = []
        meta = []  # dicts: name, kind, arg, can_combine
        cols.append(x1)
        meta.append({"name": "x1", "kind": "lin", "arg": None, "can_combine": False})
        cols.append(x2)
        meta.append({"name": "x2", "kind": "lin", "arg": None, "can_combine": False})

        muls = [1.0, 2.0, 3.0, float(np.pi), float(2.0 * np.pi)]
        mul_strs = []
        for m in muls:
            if abs(m - round(m)) < 1e-12:
                mul_strs.append(str(int(round(m))))
            else:
                mul_strs.append(self._fmt_float(m))

        trig_cache = {}  # (m, var, func) -> array
        def trig(m, var, func):
            key = (m, var, func)
            if key in trig_cache:
                return trig_cache[key]
            arr = np.sin(m * (x1 if var == "x1" else x2)) if func == "sin" else np.cos(m * (x1 if var == "x1" else x2))
            trig_cache[key] = arr
            return arr

        def arg_expr(mstr, var):
            if mstr == "1":
                return var
            return f"{mstr}*{var}"

        for m, mstr in zip(muls, mul_strs):
            a1 = arg_expr(mstr, "x1")
            a2 = arg_expr(mstr, "x2")

            cols.append(trig(m, "x1", "sin"))
            meta.append({"name": f"sin({a1})", "kind": "sin", "arg": a1, "can_combine": True})

            cols.append(trig(m, "x1", "cos"))
            meta.append({"name": f"cos({a1})", "kind": "cos", "arg": a1, "can_combine": True})

            cols.append(trig(m, "x2", "sin"))
            meta.append({"name": f"sin({a2})", "kind": "sin", "arg": a2, "can_combine": True})

            cols.append(trig(m, "x2", "cos"))
            meta.append({"name": f"cos({a2})", "kind": "cos", "arg": a2, "can_combine": True})

        # Cross terms for m=1 and m=2*pi
        cross_muls = [(1.0, "1"), (float(2.0 * np.pi), self._fmt_float(float(2.0 * np.pi)))]
        for m, mstr in cross_muls:
            if mstr == "1":
                argp = "x1+x2"
                argm = "x1-x2"
            else:
                argp = f"{mstr}*(x1+x2)"
                argm = f"{mstr}*(x1-x2)"
            cols.append(np.sin(m * (x1 + x2)))
            meta.append({"name": f"sin({argp})", "kind": "sin", "arg": argp, "can_combine": True})
            cols.append(np.cos(m * (x1 + x2)))
            meta.append({"name": f"cos({argp})", "kind": "cos", "arg": argp, "can_combine": True})
            cols.append(np.sin(m * (x1 - x2)))
            meta.append({"name": f"sin({argm})", "kind": "sin", "arg": argm, "can_combine": True})
            cols.append(np.cos(m * (x1 - x2)))
            meta.append({"name": f"cos({argm})", "kind": "cos", "arg": argm, "can_combine": True})

        # Product terms for m=1 and m=2*pi
        for m, mstr in cross_muls:
            a1 = "x1" if mstr == "1" else f"{mstr}*x1"
            a2 = "x2" if mstr == "1" else f"{mstr}*x2"
            s1 = np.sin(m * x1)
            c1 = np.cos(m * x1)
            s2 = np.sin(m * x2)
            c2 = np.cos(m * x2)

            cols.append(s1 * s2)
            meta.append({"name": f"sin({a1})*sin({a2})", "kind": "prod", "arg": None, "can_combine": False})
            cols.append(s1 * c2)
            meta.append({"name": f"sin({a1})*cos({a2})", "kind": "prod", "arg": None, "can_combine": False})
            cols.append(c1 * s2)
            meta.append({"name": f"cos({a1})*sin({a2})", "kind": "prod", "arg": None, "can_combine": False})
            cols.append(c1 * c2)
            meta.append({"name": f"cos({a1})*cos({a2})", "kind": "prod", "arg": None, "can_combine": False})

        Phi = np.column_stack(cols).astype(np.float64, copy=False)
        A = np.column_stack([np.ones(n, dtype=np.float64), Phi])
        return A, meta

    @staticmethod
    def _mse_from_gram(G: np.ndarray, b: np.ndarray, yTy: float, inds) -> float:
        idx = np.fromiter(inds, dtype=np.int64)
        Gs = G[np.ix_(idx, idx)]
        bs = b[idx]

        try:
            beta = np.linalg.solve(Gs, bs)
        except np.linalg.LinAlgError:
            beta = np.linalg.lstsq(Gs, bs, rcond=None)[0]

        sse = yTy - 2.0 * float(beta @ bs) + float(beta @ (Gs @ beta))
        if sse < 0.0 and sse > -1e-10:
            sse = 0.0
        return float(sse) / max(1, int(G.shape[0] * 0 + 1))  # placeholder, overwritten below

    def _select_subset(self, A: np.ndarray, y: np.ndarray, max_terms: int):
        n = y.shape[0]
        G = A.T @ A
        b = A.T @ y
        yTy = float(y @ y)

        candidates = list(range(1, A.shape[1]))
        best_inds = (0,)
        best_mse = float(np.mean((y - y.mean()) ** 2)) if n > 0 else 0.0

        def mse_for(inds):
            idx = np.fromiter(inds, dtype=np.int64)
            Gs = G[np.ix_(idx, idx)]
            bs = b[idx]
            try:
                beta = np.linalg.solve(Gs, bs)
            except np.linalg.LinAlgError:
                beta = np.linalg.lstsq(Gs, bs, rcond=None)[0]
            sse = yTy - 2.0 * float(beta @ bs) + float(beta @ (Gs @ beta))
            if sse < 0.0 and sse > -1e-8:
                sse = 0.0
            return float(sse) / float(n)

        for k in range(0, max_terms + 1):
            if k == 0:
                inds = (0,)
                mse = mse_for(inds)
                best_inds, best_mse = inds, mse
                continue
            for comb in combinations(candidates, k):
                inds = (0,) + comb
                mse = mse_for(inds)
                if mse < best_mse - 1e-14:
                    best_mse = mse
                    best_inds = inds
                elif abs(mse - best_mse) <= 1e-14 and len(inds) < len(best_inds):
                    best_inds = inds

        return best_inds

    def _fit_and_prune(self, A: np.ndarray, y: np.ndarray, inds):
        inds = list(inds)
        Xs = A[:, inds]
        beta = np.linalg.lstsq(Xs, y, rcond=None)[0]

        # prune small coefficients (excluding intercept at position 0)
        keep = [True] * len(inds)
        for i in range(1, len(inds)):
            if abs(beta[i]) < self.coef_tol:
                keep[i] = False
        if not all(keep):
            inds = [j for j, k in zip(inds, keep) if k]
            Xs = A[:, inds]
            beta = np.linalg.lstsq(Xs, y, rcond=None)[0]

        # attempt greedy removal if it doesn't hurt
        improved = True
        while improved and len(inds) > 1:
            improved = False
            base_pred = Xs @ beta
            base_mse = float(np.mean((y - base_pred) ** 2))
            best_mse = base_mse
            best_remove = None
            for pos in range(1, len(inds)):
                test_inds = inds[:pos] + inds[pos + 1 :]
                Xt = A[:, test_inds]
                bt = np.linalg.lstsq(Xt, y, rcond=None)[0]
                predt = Xt @ bt
                mset = float(np.mean((y - predt) ** 2))
                if mset <= best_mse * (1.0 + 1e-10):
                    if mset < best_mse - 1e-14 or best_remove is None:
                        best_mse = mset
                        best_remove = pos
                        best_bt = bt
                        best_Xt = Xt
                        best_test_inds = test_inds
            if best_remove is not None:
                inds = best_test_inds
                beta = best_bt
                Xs = best_Xt
                improved = True

        return inds, beta

    def _combine_sin_cos_terms(self, inds, beta, meta):
        # inds includes 0 for intercept; meta corresponds to A columns excluding intercept:
        # meta[i-1] is for column i.
        intercept = float(beta[0])
        terms = []
        for j, c in zip(inds[1:], beta[1:]):
            m = meta[j - 1]
            terms.append({"col": j, "coef": float(c), "meta": m})

        if not self.combine_sincos:
            return intercept, terms, []

        # group by arg for combinable sin/cos
        by_arg = {}
        others = []
        for t in terms:
            m = t["meta"]
            if m.get("can_combine", False) and m["kind"] in ("sin", "cos") and m.get("arg") is not None:
                key = m["arg"]
                if key not in by_arg:
                    by_arg[key] = {"sin": None, "cos": None}
                by_arg[key][m["kind"]] = t
            else:
                others.append(t)

        combined = []
        for arg, pair in by_arg.items():
            ts = pair["sin"]
            tc = pair["cos"]
            if ts is None and tc is None:
                continue
            if ts is None:
                others.append(tc)
                continue
            if tc is None:
                others.append(ts)
                continue

            A = float(ts["coef"])
            B = float(tc["coef"])
            R = float(np.hypot(A, B))
            if R < self.coef_tol:
                continue
            theta = float(np.arctan2(B, A))

            # build sin(arg + theta)
            if abs(theta) < 1e-12:
                inside = arg
            elif theta > 0:
                inside = f"{arg}+{self._fmt_float(theta)}"
            else:
                inside = f"{arg}-{self._fmt_float(abs(theta))}"
            name = f"sin({inside})"
            combined.append({"col": None, "coef": R, "meta": {"name": name, "kind": "sin", "arg": inside, "can_combine": False}})

        # If combining made expression longer (rare), keep original; but without computing exact complexity, accept.
        return intercept, others + combined, combined

    def _build_expression(self, intercept: float, terms):
        parts = []
        have_nonconst = any(abs(t["coef"]) >= self.coef_tol for t in terms)

        if abs(intercept) >= self.coef_tol or not have_nonconst:
            parts.append(self._fmt_float(intercept))

        for t in terms:
            c = float(t["coef"])
            if abs(c) < self.coef_tol:
                continue
            name = t["meta"]["name"]
            if not parts:
                if abs(abs(c) - 1.0) < 1e-10:
                    parts.append(f"-{name}" if c < 0 else name)
                else:
                    parts.append(f"{self._fmt_float(c)}*{name}")
            else:
                if c >= 0:
                    if abs(c - 1.0) < 1e-10:
                        parts.append(f"+{name}")
                    else:
                        parts.append(f"+{self._fmt_float(c)}*{name}")
                else:
                    mag = -c
                    if abs(mag - 1.0) < 1e-10:
                        parts.append(f"-{name}")
                    else:
                        parts.append(f"-{self._fmt_float(mag)}*{name}")

        expr = "".join(parts) if parts else "0.0"
        expr = expr.replace("+-", "-")
        return expr

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        X = np.asarray(X)
        y = np.asarray(y).reshape(-1)
        if X.ndim != 2 or X.shape[1] != 2:
            raise ValueError("X must have shape (n, 2)")

        x1 = np.asarray(X[:, 0], dtype=np.float64)
        x2 = np.asarray(X[:, 1], dtype=np.float64)
        y = np.asarray(y, dtype=np.float64)

        A, meta = self._build_library(x1, x2)

        best_inds = self._select_subset(A, y, max_terms=self.max_terms)
        inds, beta = self._fit_and_prune(A, y, best_inds)

        # Combine sin/cos pairs into phase-shifted sin
        intercept, term_objs, _ = self._combine_sin_cos_terms(inds, beta, meta)
        expression = self._build_expression(intercept, term_objs)

        preds = self._safe_eval_expr(expression, x1, x2)
        mse = float(np.mean((y - preds) ** 2))

        details = {
            "mse": mse,
            "complexity": self._complexity(expression),
        }

        return {
            "expression": expression,
            "predictions": preds.tolist(),
            "details": details,
        }