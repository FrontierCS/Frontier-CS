import pandas as pd
from collections import Counter
from array import array
import time


class _TreapNode:
    __slots__ = ("key", "prio", "left", "right", "count")

    def __init__(self, key: str, prio: int):
        self.key = key
        self.prio = prio
        self.left = None
        self.right = None
        self.count = 1


class _XorShift32:
    __slots__ = ("state",)

    def __init__(self, seed: int = 2463534242):
        self.state = seed & 0xFFFFFFFF

    def next(self) -> int:
        x = self.state
        x ^= (x << 13) & 0xFFFFFFFF
        x ^= (x >> 17) & 0xFFFFFFFF
        x ^= (x << 5) & 0xFFFFFFFF
        self.state = x & 0xFFFFFFFF
        return self.state


def _lcp_len(a: str, b: str) -> int:
    n = len(a)
    m = len(b)
    lim = n if n < m else m
    i = 0
    while i < lim and a[i] == b[i]:
        i += 1
    return i


def _treap_split(root: _TreapNode, key: str):
    if root is None:
        return None, None
    if key <= root.key:
        left, right = _treap_split(root.left, key)
        root.left = right
        return left, root
    else:
        left, right = _treap_split(root.right, key)
        root.right = left
        return root, right


def _treap_merge(a: _TreapNode, b: _TreapNode):
    if a is None:
        return b
    if b is None:
        return a
    if a.prio < b.prio:
        a.right = _treap_merge(a.right, b)
        return a
    else:
        b.left = _treap_merge(a, b.left)
        return b


def _treap_insert(root: _TreapNode, node: _TreapNode):
    if root is None:
        return node
    if node.prio < root.prio:
        left, right = _treap_split(root, node.key)
        node.left = left
        node.right = right
        return node
    if node.key < root.key:
        root.left = _treap_insert(root.left, node)
    else:
        root.right = _treap_insert(root.right, node)
    return root


def _treap_add(root: _TreapNode, key: str, rng: _XorShift32):
    if root is None:
        return _TreapNode(key, rng.next())
    cur = root
    while cur is not None:
        if key == cur.key:
            cur.count += 1
            return root
        if key < cur.key:
            if cur.left is None:
                break
            cur = cur.left
        else:
            if cur.right is None:
                break
            cur = cur.right
    node = _TreapNode(key, rng.next())
    return _treap_insert(root, node)


def _treap_best_lcp(root: _TreapNode, key: str) -> int:
    cur = root
    pred = None
    succ = None
    while cur is not None:
        ck = cur.key
        if key == ck:
            return len(key)
        if key < ck:
            succ = ck
            cur = cur.left
        else:
            pred = ck
            cur = cur.right
    best = 0
    if pred is not None:
        x = _lcp_len(key, pred)
        if x > best:
            best = x
    if succ is not None:
        x = _lcp_len(key, succ)
        if x > best:
            best = x
    return best


class Solution:
    def _apply_col_merge(self, df: pd.DataFrame, col_merge):
        if not col_merge:
            return df
        df = df.copy()
        orig_cols = list(df.columns)
        merge_counter = 0

        for group in col_merge:
            if not group or len(group) <= 1:
                continue

            names = []
            for g in group:
                name = None
                if isinstance(g, int):
                    if 0 <= g < len(orig_cols):
                        name = orig_cols[g]
                    elif 0 <= g < len(df.columns):
                        name = df.columns[g]
                else:
                    name = g
                if name in df.columns:
                    names.append(name)

            seen = set()
            names2 = []
            for n in names:
                if n not in seen:
                    names2.append(n)
                    seen.add(n)
            names = names2

            if len(names) <= 1:
                continue

            pos = min(int(df.columns.get_loc(n)) for n in names)
            merged = df[names[0]].astype(str)
            for n in names[1:]:
                merged = merged + df[n].astype(str)

            base_name = "__".join(str(n) for n in names)
            new_name = base_name
            while new_name in df.columns:
                merge_counter += 1
                new_name = f"{base_name}__m{merge_counter}"

            df[new_name] = merged
            df = df.drop(columns=names)
            cols = list(df.columns)
            cols.remove(new_name)
            cols.insert(pos, new_name)
            df = df.loc[:, cols]

        return df

    def _approx_firstcol_total(self, vals, L=8):
        n = len(vals)
        if n <= 1:
            return 0
        seen_vals = set()
        prefix_sets = [set() for _ in range(L)]
        total = 0

        v0 = vals[0]
        seen_vals.add(v0)
        lim0 = len(v0)
        if lim0 > L:
            lim0 = L
        for l in range(1, lim0 + 1):
            prefix_sets[l - 1].add(v0[:l])

        for i in range(1, n):
            v = vals[i]
            if v in seen_vals:
                total += len(v)
            else:
                mx = 0
                lim = len(v)
                if lim > L:
                    lim = L
                for l in range(lim, 0, -1):
                    if v[:l] in prefix_sets[l - 1]:
                        mx = l
                        break
                total += mx

            if v not in seen_vals:
                seen_vals.add(v)
                lim = len(v)
                if lim > L:
                    lim = L
                for l in range(1, lim + 1):
                    prefix_sets[l - 1].add(v[:l])
            else:
                # already present; still add prefixes (no-op for sets)
                lim = len(v)
                if lim > L:
                    lim = L
                for l in range(1, lim + 1):
                    prefix_sets[l - 1].add(v[:l])

        return total

    def _compute_score_hash(self, order, hv_cols, len_cols, K, P, mask):
        t = len(order)
        if t == 0 or K <= 1:
            return 0
        if t == 1:
            # caller should use firstcol_total
            return 0

        seen = [set() for _ in range(t)]
        total = 0
        for r in range(K):
            h = 0
            pref = 0
            best = 0
            for k, ci in enumerate(order):
                h = (h * P + hv_cols[ci][r]) & mask
                pref += len_cols[ci][r]
                sk = seen[k]
                if h in sk:
                    best = pref
                sk.add(h)
            if r:
                total += best
        return total

    def _beam_search(
        self,
        M,
        hv_cols,
        len_cols,
        desirability,
        firstcol_total,
        K,
        beam_width,
        expand_limit,
        early_stop,
        distinct_ratio,
        distinct_value_threshold,
        time_limit_s,
    ):
        start = time.perf_counter()
        P = 1469598103934665603  # FNV offset basis-ish; used as multiplier here
        mask = (1 << 64) - 1

        col_all = list(range(M))
        beam = [(tuple(), 0)]

        eval_count = 0
        for step in range(M):
            if time.perf_counter() - start > time_limit_s:
                break
            new_states = []
            for order, _score in beam:
                used = set(order)
                rem = [c for c in col_all if c not in used]
                # prioritize remaining by desirability
                rem.sort(key=lambda x: desirability[x], reverse=True)

                # enforce threshold bias for early columns: postpone high-distinct cols
                if step <= 1 and distinct_value_threshold is not None:
                    low = [c for c in rem if distinct_ratio[c] < distinct_value_threshold]
                    high = [c for c in rem if distinct_ratio[c] >= distinct_value_threshold]
                    rem = low + high

                rem = rem[:expand_limit]
                for c in rem:
                    order2 = order + (c,)
                    if len(order2) == 1:
                        score2 = firstcol_total[c]
                    else:
                        score2 = self._compute_score_hash(order2, hv_cols, len_cols, K, P, mask)
                    new_states.append((order2, score2))
                    eval_count += 1
                    if eval_count >= early_stop:
                        break
                if eval_count >= early_stop:
                    break
            if not new_states:
                break
            new_states.sort(key=lambda x: x[1], reverse=True)
            beam = new_states[:beam_width]

        # if incomplete, fill greedily
        results = []
        for order, sc in beam:
            used = set(order)
            rem = [c for c in range(M) if c not in used]
            rem.sort(key=lambda x: desirability[x], reverse=True)
            full = list(order) + rem
            results.append((tuple(full[:M]), sc))
        # dedup preserving best approx score
        best_for = {}
        for o, sc in results:
            prev = best_for.get(o)
            if prev is None or sc > prev:
                best_for[o] = sc
        outs = [(o, sc) for o, sc in best_for.items()]
        outs.sort(key=lambda x: x[1], reverse=True)
        return outs

    def _exact_score_treap(self, order, col_vals):
        K = len(col_vals[0])
        cols = [col_vals[i] for i in order]
        root = None
        rng = _XorShift32(123456789)
        total = 0
        if K <= 1:
            return 0

        for i in range(K):
            s = cols[0][i]
            for c in cols[1:]:
                s += c[i]
            if i:
                total += _treap_best_lcp(root, s)
            root = _treap_add(root, s, rng)
        return total

    def solve(
        self,
        df: pd.DataFrame,
        early_stop: int = 100000,
        row_stop: int = 4,
        col_stop: int = 2,
        col_merge: list = None,
        one_way_dep: list = None,
        distinct_value_threshold: float = 0.7,
        parallel: bool = True,
    ) -> pd.DataFrame:
        start = time.perf_counter()

        df2 = df.copy()
        df2 = self._apply_col_merge(df2, col_merge)

        cols = list(df2.columns)
        M = len(cols)
        if M <= 1:
            return df2

        N = len(df2)
        if N <= 1:
            return df2

        # sample size
        K = row_stop * 2000
        if K < 2000:
            K = 2000
        if K > 12000:
            K = 12000
        if K > N:
            K = N

        sample = df2.iloc[:K]

        mask = (1 << 64) - 1
        hv_cols = []
        len_cols = []
        col_vals = []
        desirability = [0.0] * M
        distinct_ratio = [1.0] * M
        firstcol_total = [0] * M

        for j, c in enumerate(cols):
            vals = sample[c].astype(str).tolist()
            col_vals.append(vals)

            lens = array("H", (len(x) for x in vals))
            hvs = array("Q", ((hash(x) & mask) for x in vals))

            len_cols.append(lens)
            hv_cols.append(hvs)

            cnt = Counter(vals)
            dr = (len(cnt) / K) if K else 1.0
            distinct_ratio[j] = dr
            top_freq = (max(cnt.values()) / K) if K else 0.0
            avg_len = (sum(lens) / K) if K else 0.0

            # intrinsic approx for first column (captures common prefixes + duplicates)
            fc_total = self._approx_firstcol_total(vals, L=8)
            firstcol_total[j] = fc_total
            intrinsic_avg = (fc_total / (K - 1)) if K > 1 else 0.0

            # desirability heuristic
            # emphasize early cache benefit: repeated/full matches, plus intrinsic partial matches
            desirability[j] = (1.0 - dr) * avg_len * 1.5 + intrinsic_avg * 1.8 + top_freq * avg_len * 0.6

        # quick fallback if time budget already tight
        if time.perf_counter() - start > 7.0:
            order = list(range(M))
            order.sort(key=lambda x: desirability[x], reverse=True)
            return df2.loc[:, [cols[i] for i in order]]

        beam_width = col_stop * 4
        if beam_width < 3:
            beam_width = 3
        if beam_width > 12:
            beam_width = 12

        expand_limit = col_stop * 3
        if expand_limit < 2:
            expand_limit = 2
        if expand_limit > M:
            expand_limit = M

        time_limit_s = 8.8  # overall per dataset target < 10s; reserve headroom

        candidates = self._beam_search(
            M=M,
            hv_cols=hv_cols,
            len_cols=len_cols,
            desirability=desirability,
            firstcol_total=firstcol_total,
            K=K,
            beam_width=beam_width,
            expand_limit=expand_limit,
            early_stop=early_stop,
            distinct_ratio=distinct_ratio,
            distinct_value_threshold=distinct_value_threshold,
            time_limit_s=max(1.0, time_limit_s - (time.perf_counter() - start)),
        )

        # If beam search yielded nothing, use desirability sorting
        if not candidates:
            order = list(range(M))
            order.sort(key=lambda x: desirability[x], reverse=True)
        else:
            # Exact evaluation on top candidates (treap)
            topk = candidates[: min(len(candidates), beam_width)]
            best_order = topk[0][0]
            best_score = -1

            for o, _sc in topk:
                if time.perf_counter() - start > time_limit_s:
                    break
                s = self._exact_score_treap(o, col_vals)
                if s > best_score:
                    best_score = s
                    best_order = o
            order = list(best_order)

        # Apply one-way dependencies if provided (best-effort)
        if one_way_dep:
            pos = {cols[i]: idx for idx, i in enumerate(order)}
            # normalize deps as column names if possible
            deps = []
            for a, b in one_way_dep:
                an = a
                bn = b
                if isinstance(a, int) and 0 <= a < len(cols):
                    an = cols[a]
                if isinstance(b, int) and 0 <= b < len(cols):
                    bn = cols[b]
                if an in pos and bn in pos:
                    deps.append((an, bn))
            # iterative fix
            for _ in range(M * 2):
                changed = False
                pos = {cols[i]: idx for idx, i in enumerate(order)}
                for an, bn in deps:
                    ia = pos[an]
                    ib = pos[bn]
                    if ia > ib:
                        a_idx = order.pop(ia)
                        # insert before b's current position
                        ib = pos[bn]
                        order.insert(ib, a_idx)
                        changed = True
                        break
                if not changed:
                    break

        out_cols = [cols[i] for i in order]
        return df2.loc[:, out_cols]