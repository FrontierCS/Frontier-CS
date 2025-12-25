import numpy as np
from itertools import combinations
import heapq

class _Term:
    __slots__ = ("tid", "expr", "values", "unary", "bin")
    def __init__(self, tid, expr, values, unary, binops):
        self.tid = tid
        self.expr = expr
        self.values = values
        self.unary = int(unary)
        self.bin = int(binops)

class Solution:
    def __init__(self, **kwargs):
        self.kwargs = kwargs

    @staticmethod
    def _format_float(x: float) -> str:
        if not np.isfinite(x):
            if x > 0:
                return "1e308"
            if x < 0:
                return "-1e308"
            return "0"
        ax = abs(x)
        if ax < 1e-14:
            return "0"
        rx = round(x)
        if abs(x - rx) < 1e-10 and abs(rx) <= 10**12:
            return str(int(rx))
        s = "{:.12g}".format(float(x))
        if s == "-0":
            s = "0"
        return s

    @staticmethod
    def _snap(x: float) -> float:
        if not np.isfinite(x):
            return x
        snap_vals = (0.0, 1.0, -1.0, 0.5, -0.5, 2.0, -2.0, 3.0, -3.0)
        for v in snap_vals:
            if abs(x - v) <= 1e-6:
                return v
        rx = round(x)
        if abs(x - rx) <= 1e-8 and abs(rx) <= 10**6:
            return float(rx)
        return float(x)

    @staticmethod
    def _safe_solve(M, rhs):
        try:
            return np.linalg.solve(M, rhs)
        except np.linalg.LinAlgError:
            sol, *_ = np.linalg.lstsq(M, rhs, rcond=None)
            return sol

    @staticmethod
    def _subset_fit_stats_from_gram(G, g1, yF, y1, yTy, n, idx):
        k = len(idx)
        if k == 0:
            b = y1 / n
            sse = max(0.0, yTy - b * y1)
            mse = sse / n
            return np.zeros(0, dtype=float), float(b), float(mse)
        S = G[np.ix_(idx, idx)]
        s1 = g1[idx]
        M = np.empty((k + 1, k + 1), dtype=float)
        M[:k, :k] = S
        M[:k, k] = s1
        M[k, :k] = s1
        M[k, k] = float(n)
        rhs = np.empty(k + 1, dtype=float)
        rhs[:k] = yF[idx]
        rhs[k] = float(y1)
        beta = Solution._safe_solve(M, rhs)
        sse = float(yTy - float(beta.dot(rhs)))
        if sse < 0.0:
            sse = 0.0
        mse = sse / float(n)
        w = beta[:k]
        b = float(beta[k])
        return w, b, mse

    @staticmethod
    def _fit_lstsq(Fcols, y):
        n = y.shape[0]
        k = len(Fcols)
        if k == 0:
            b = float(np.mean(y)) if n else 0.0
            pred = np.full(n, b, dtype=float)
            mse = float(np.mean((y - pred) ** 2)) if n else 0.0
            return np.zeros(0, dtype=float), b, pred, mse
        A = np.empty((n, k + 1), dtype=float)
        for j, col in enumerate(Fcols):
            A[:, j] = col
        A[:, k] = 1.0
        coef, *_ = np.linalg.lstsq(A, y, rcond=None)
        w = coef[:k]
        b = float(coef[k])
        pred = A @ coef
        mse = float(np.mean((y - pred) ** 2)) if n else 0.0
        return w, b, pred, mse

    @staticmethod
    def _compute_complexity(term_ids, coef_map, intercept, term_by_id, drop_tol=0.0):
        used = []
        for tid in term_ids:
            c = coef_map.get(tid, 0.0)
            if abs(c) > drop_tol:
                used.append(tid)
        b = intercept
        if abs(b) > drop_tol:
            used_const = True
        else:
            used_const = False
        n_terms = len(used) + (1 if used_const else 0)
        if n_terms == 0:
            return 0
        unary = 0
        binops = 0
        for tid in used:
            t = term_by_id[tid]
            unary += t.unary
            binops += t.bin
            c = coef_map[tid]
            if abs(abs(c) - 1.0) > 1e-6:
                binops += 1
        if n_terms >= 2:
            binops += (n_terms - 1)
        return int(2 * binops + unary)

    @staticmethod
    def _build_expression(term_ids, coef_map, intercept, term_by_id, drop_tol):
        parts = []

        def add_part(sign, txt):
            if not parts:
                if sign < 0:
                    parts.append("-" + txt)
                else:
                    parts.append(txt)
            else:
                parts.append(("-" if sign < 0 else "+") + txt)

        for tid in term_ids:
            c = float(coef_map.get(tid, 0.0))
            if abs(c) <= drop_tol:
                continue
            t = term_by_id[tid]
            sign = -1 if c < 0 else 1
            mag = abs(c)
            if abs(mag - 1.0) <= 1e-6:
                txt = t.expr
            else:
                txt = Solution._format_float(mag) + "*" + t.expr
            add_part(sign, txt)

        b = float(intercept)
        if abs(b) > drop_tol:
            sign = -1 if b < 0 else 1
            mag = abs(b)
            txt = Solution._format_float(mag)
            add_part(sign, txt)

        if not parts:
            return "0"
        expr = "".join(parts)
        if expr == "":
            expr = "0"
        return expr

    @staticmethod
    def _simplify_trig_pairs(coef_map, prefer_angle_terms=True, rel_tol=2e-3, abs_tol=1e-8):
        c = dict(coef_map)

        def close(a, b):
            return abs(a - b) <= max(abs_tol, rel_tol * max(1.0, abs(a), abs(b)))

        def add_to(tid, val):
            if abs(val) <= abs_tol:
                return
            c[tid] = c.get(tid, 0.0) + val

        def pop(tid):
            return c.pop(tid, 0.0)

        if prefer_angle_terms:
            a = c.get("s1c2", 0.0)
            b = c.get("c1s2", 0.0)
            if abs(a) > abs_tol and abs(b) > abs_tol and ("sp" not in c and "sm" not in c):
                if close(a, b):
                    k = 0.5 * (a + b)
                    pop("s1c2")
                    pop("c1s2")
                    add_to("sp", k)
                elif close(a, -b):
                    k = 0.5 * (a - b)
                    pop("s1c2")
                    pop("c1s2")
                    add_to("sm", k)

            a = c.get("c1c2", 0.0)
            b = c.get("s1s2", 0.0)
            if abs(a) > abs_tol and abs(b) > abs_tol and ("cp" not in c and "cm" not in c):
                if close(a, -b):
                    k = 0.5 * (a - b)
                    pop("c1c2")
                    pop("s1s2")
                    add_to("cp", k)
                elif close(a, b):
                    k = 0.5 * (a + b)
                    pop("c1c2")
                    pop("s1s2")
                    add_to("cm", k)

        for k in list(c.keys()):
            if abs(c[k]) <= abs_tol:
                c.pop(k, None)
        return c

    def solve(self, X: np.ndarray, y: np.ndarray) -> dict:
        X = np.asarray(X, dtype=float)
        y = np.asarray(y, dtype=float).reshape(-1)
        n = y.shape[0]

        if n == 0 or X.size == 0:
            return {"expression": "0", "predictions": [], "details": {"complexity": 0}}

        x1 = X[:, 0]
        x2 = X[:, 1]

        s1 = np.sin(x1)
        c1 = np.cos(x1)
        s2 = np.sin(x2)
        c2 = np.cos(x2)

        xp = x1 + x2
        xm = x1 - x2
        sp = np.sin(xp)
        cp = np.cos(xp)
        sm = np.sin(xm)
        cm = np.cos(xm)

        s1c2 = s1 * c2
        c1s2 = c1 * s2
        s1s2 = s1 * s2
        c1c2 = c1 * c2

        s1_2 = np.sin(2.0 * x1)
        c1_2 = np.cos(2.0 * x1)
        s2_2 = np.sin(2.0 * x2)
        c2_2 = np.cos(2.0 * x2)

        term_by_id = {}
        all_terms = [
            _Term("s1", "sin(x1)", s1, 1, 0),
            _Term("c1", "cos(x1)", c1, 1, 0),
            _Term("s2", "sin(x2)", s2, 1, 0),
            _Term("c2", "cos(x2)", c2, 1, 0),

            _Term("sp", "sin(x1+x2)", sp, 1, 1),
            _Term("cp", "cos(x1+x2)", cp, 1, 1),
            _Term("sm", "sin(x1-x2)", sm, 1, 1),
            _Term("cm", "cos(x1-x2)", cm, 1, 1),

            _Term("s1c2", "sin(x1)*cos(x2)", s1c2, 2, 1),
            _Term("c1s2", "cos(x1)*sin(x2)", c1s2, 2, 1),
            _Term("s1s2", "sin(x1)*sin(x2)", s1s2, 2, 1),
            _Term("c1c2", "cos(x1)*cos(x2)", c1c2, 2, 1),

            _Term("x1", "x1", x1, 0, 0),
            _Term("x2", "x2", x2, 0, 0),

            _Term("s1_2", "sin(2*x1)", s1_2, 1, 1),
            _Term("c1_2", "cos(2*x1)", c1_2, 1, 1),
            _Term("s2_2", "sin(2*x2)", s2_2, 1, 1),
            _Term("c2_2", "cos(2*x2)", c2_2, 1, 1),
        ]
        for t in all_terms:
            term_by_id[t.tid] = t

        base_ids = ["s1", "c1", "s2", "c2", "sp", "cp", "sm", "cm", "s1c2", "c1s2", "s1s2", "c1c2"]
        base_terms = [term_by_id[tid] for tid in base_ids]
        baseF = np.column_stack([t.values for t in base_terms]).astype(float, copy=False)

        y1 = float(np.sum(y))
        yTy = float(y.dot(y))
        G = baseF.T @ baseF
        g1 = np.sum(baseF, axis=0)
        yF = baseF.T @ y

        max_terms = 4
        keep = 60
        heap = []
        seen = set()

        def push_candidate(idx_tuple, w, b, mse, source):
            if idx_tuple in seen:
                return
            seen.add(idx_tuple)
            item = (-float(mse), (idx_tuple, np.array(w, dtype=float, copy=True), float(b), float(mse), source))
            if len(heap) < keep:
                heapq.heappush(heap, item)
            else:
                if item[0] > heap[0][0]:
                    heapq.heapreplace(heap, item)

        p = len(base_ids)
        idx_all = list(range(p))
        for k in range(0, max_terms + 1):
            if k == 0:
                w, b, mse = self._subset_fit_stats_from_gram(G, g1, yF, y1, yTy, n, [])
                push_candidate(tuple(), w, b, mse, "exh0")
                continue
            for idx in combinations(idx_all, k):
                w, b, mse = self._subset_fit_stats_from_gram(G, g1, yF, y1, yTy, n, list(idx))
                push_candidate(tuple(idx), w, b, mse, f"exh{k}")

        ext_ids = [t.tid for t in all_terms]
        ext_terms = [term_by_id[tid] for tid in ext_ids]
        extF = np.column_stack([t.values for t in ext_terms]).astype(float, copy=False)

        def omp_candidates(kmax=4):
            selected = []
            remaining = set(range(extF.shape[1]))
            b0 = float(np.mean(y))
            pred = np.full(n, b0, dtype=float)
            resid = y - pred
            best_local = []
            best_mse = float(np.mean(resid * resid))
            best_local.append((tuple(), np.zeros(0, dtype=float), b0, best_mse, "omp0"))
            for k in range(1, kmax + 1):
                if not remaining:
                    break
                corr = extF.T @ resid
                for j in selected:
                    corr[j] = 0.0
                j = int(np.argmax(np.abs(corr)))
                if j not in remaining:
                    break
                selected.append(j)
                remaining.remove(j)
                cols = [extF[:, jj] for jj in selected]
                w, b, pred, mse = self._fit_lstsq(cols, y)
                resid = y - pred
                best_local.append((tuple(selected), w, b, mse, f"omp{k}"))
                if best_mse - mse < 1e-14 * max(1.0, best_mse):
                    break
                best_mse = mse
            return best_local

        for idx_tuple, w, b, mse, source in omp_candidates(kmax=4):
            push_candidate(("omp",) + idx_tuple, w, b, mse, source)

        candidates = [it[1] for it in heap]
        candidates.sort(key=lambda x: x[3])
        candidates = candidates[:40] if len(candidates) > 40 else candidates

        y_scale = float(np.std(y))
        drop_tol = max(1e-10, 1e-8 * max(1.0, y_scale))

        best = None
        best_mse = float("inf")
        best_complexity = None

        def postprocess_candidate(idx_tuple, w, b, source):
            if len(idx_tuple) > 0 and idx_tuple[0] == "omp":
                term_idxs = idx_tuple[1:]
                term_ids = [ext_ids[i] for i in term_idxs]
                w0 = np.array(w, dtype=float)
            else:
                term_idxs = idx_tuple
                term_ids = [base_ids[i] for i in term_idxs]
                w0 = np.array(w, dtype=float)

            coef_map = {}
            for tid, coef in zip(term_ids, w0):
                coef_map[tid] = float(coef)
            coef_map = self._simplify_trig_pairs(coef_map, prefer_angle_terms=True, rel_tol=2e-3, abs_tol=drop_tol)

            final_ids = [tid for tid in coef_map.keys() if tid in term_by_id]
            final_ids.sort()

            cols = [term_by_id[tid].values for tid in final_ids]
            w1, b1, pred1, mse1 = self._fit_lstsq(cols, y)

            coef_map2 = {}
            for tid, coef in zip(final_ids, w1):
                coef_map2[tid] = float(coef)

            kept_ids = [tid for tid in final_ids if abs(coef_map2.get(tid, 0.0)) > drop_tol]
            kept_ids.sort()
            if kept_ids != final_ids:
                cols2 = [term_by_id[tid].values for tid in kept_ids]
                w2, b2, pred2, mse2 = self._fit_lstsq(cols2, y)
                coef_map3 = {tid: float(coef) for tid, coef in zip(kept_ids, w2)}
                b3 = float(b2)
                pred3 = pred2
                mse3 = float(mse2)
                final_ids2 = kept_ids
            else:
                coef_map3 = coef_map2
                b3 = float(b1)
                pred3 = pred1
                mse3 = float(mse1)
                final_ids2 = final_ids

            for tid in list(coef_map3.keys()):
                coef_map3[tid] = self._snap(coef_map3[tid])
                if abs(coef_map3[tid]) <= drop_tol:
                    coef_map3.pop(tid, None)
            b3 = self._snap(b3)
            if abs(b3) <= drop_tol:
                b3 = 0.0

            final_ids3 = sorted(coef_map3.keys())
            expr = self._build_expression(final_ids3, coef_map3, b3, term_by_id, drop_tol=drop_tol)
            complexity = self._compute_complexity(final_ids3, coef_map3, b3, term_by_id, drop_tol=drop_tol)

            if final_ids3:
                pred = np.full(n, b3, dtype=float)
                for tid in final_ids3:
                    pred += coef_map3[tid] * term_by_id[tid].values
            else:
                pred = np.full(n, b3, dtype=float)

            mse = float(np.mean((y - pred) ** 2)) if n else 0.0
            return {
                "expression": expr,
                "predictions": pred,
                "mse": mse,
                "complexity": complexity,
                "source": source,
            }

        processed = []
        for idx_tuple, w, b, mse, source in candidates:
            processed.append(postprocess_candidate(idx_tuple, w, b, source))

        if not processed:
            b = float(np.mean(y))
            pred = np.full(n, b, dtype=float)
            expr = self._format_float(b)
            return {"expression": expr, "predictions": pred.tolist(), "details": {"complexity": 0}}

        best_mse = min(c["mse"] for c in processed)
        thresh = best_mse * (1.0 + 1e-2) + 1e-12

        feasible = [c for c in processed if c["mse"] <= thresh]
        feasible.sort(key=lambda c: (c["complexity"], c["mse"]))

        best = feasible[0] if feasible else min(processed, key=lambda c: (c["mse"], c["complexity"]))

        return {
            "expression": best["expression"],
            "predictions": best["predictions"].tolist(),
            "details": {"complexity": int(best["complexity"]), "mse": float(best["mse"]), "source": best["source"]},
        }