import time
from collections import Counter
import pandas as pd


def _lcp_len(a: str, b: str) -> int:
    la = len(a)
    lb = len(b)
    m = la if la < lb else lb
    i = 0
    while i < m and a[i] == b[i]:
        i += 1
    return i


def _build_sparse_table_min(arr):
    n = len(arr)
    if n <= 0:
        return None, None
    logs = [0] * (n + 1)
    for i in range(2, n + 1):
        logs[i] = logs[i >> 1] + 1
    st = [arr]
    k = 1
    length = 1
    while (length << 1) <= n:
        prev = st[-1]
        half = length
        length <<= 1
        size = n - length + 1
        cur = [0] * size
        for i in range(size):
            a = prev[i]
            b = prev[i + half]
            cur[i] = a if a < b else b
        st.append(cur)
        k += 1
    return st, logs


def _rmq_query_min(st, logs, l: int, r: int) -> int:
    # query on [l, r), assumes l < r
    length = r - l
    k = logs[length]
    a = st[k][l]
    b = st[k][r - (1 << k)]
    return a if a < b else b


def _fenwick_add(bit, idx0: int, delta: int):
    i = idx0 + 1
    n = len(bit) - 1
    while i <= n:
        bit[i] += delta
        i += i & -i


def _fenwick_sum_excl(bit, idx0_excl: int) -> int:
    # sum [0, idx0_excl)
    i = idx0_excl
    s = 0
    while i > 0:
        s += bit[i]
        i -= i & -i
    return s


def _fenwick_find_by_order(bit, n: int, k: int) -> int:
    # 1 <= k <= total, return 0-index idx such that prefix_sum(idx) >= k and minimal
    idx = 0
    bitmask = 1 << (n.bit_length() - 1)
    while bitmask:
        t = idx + bitmask
        if t <= n and bit[t] < k:
            idx = t
            k -= bit[t]
        bitmask >>= 1
    return idx  # already 0-index


def _eval_prefix_hits(strings):
    n = len(strings)
    if n <= 1:
        return 0

    u = sorted(set(strings))
    U = len(u)
    if U == 1:
        return (n - 1) * len(u[0])

    pos_map = {s: i for i, s in enumerate(u)}
    pos_list = [pos_map[s] for s in strings]
    lens = [len(s) for s in u]

    lcp_adj = [0] * (U - 1)
    for i in range(U - 1):
        lcp_adj[i] = _lcp_len(u[i], u[i + 1])

    st, logs = _build_sparse_table_min(lcp_adj)

    def lcp_between_indices(i, j):
        if i == j:
            return lens[i]
        if i > j:
            i, j = j, i
        return _rmq_query_min(st, logs, i, j)

    bit = [0] * (U + 1)
    freq = [0] * U

    total = 0
    # insert first
    p0 = pos_list[0]
    freq[p0] = 1
    _fenwick_add(bit, p0, 1)

    for i in range(1, n):
        p = pos_list[i]
        if freq[p] > 0:
            best = lens[p]
        else:
            left = _fenwick_sum_excl(bit, p)  # count of inserted indices < p
            best = 0
            if left > 0:
                pred_idx = _fenwick_find_by_order(bit, U, left)
                best = lcp_between_indices(pred_idx, p)
            if left < i:  # there exists inserted index > p
                succ_idx = _fenwick_find_by_order(bit, U, left + 1)
                l2 = lcp_between_indices(p, succ_idx)
                if l2 > best:
                    best = l2
        total += best
        freq[p] += 1
        _fenwick_add(bit, p, 1)

    return total


def _prefix_lcp_expectation(values, max_l=4):
    n = len(values)
    if n <= 1:
        return 0.0
    exp = 0.0
    for l in range(1, max_l + 1):
        cnt = Counter()
        for s in values:
            cnt[s[:l]] += 1
        inv = 1.0 / n
        p = 0.0
        for c in cnt.values():
            p += (c * inv) * (c * inv)
        exp += p
    return exp


def _build_strings_for_perm(col_vals, perm):
    cols_in_order = [col_vals[i] for i in perm]
    K = len(cols_in_order[0]) if cols_in_order else 0
    out = [None] * K
    for r in range(K):
        parts = []
        for c in cols_in_order:
            parts.append(c[r])
        out[r] = "".join(parts)
    return out


class Solution:
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
        start_time = time.time()
        time_budget = 9.2

        df2 = df.copy()

        # Apply column merges (if any)
        if col_merge:
            for group in col_merge:
                if not group or len(group) <= 1:
                    continue
                resolved = []
                for g in group:
                    if isinstance(g, int):
                        if 0 <= g < len(df2.columns):
                            resolved.append(df2.columns[g])
                    else:
                        resolved.append(g)
                existing = [c for c in resolved if c in df2.columns]
                if len(existing) <= 1:
                    continue
                new_name = "+".join(str(c) for c in existing)
                merged = df2[existing[0]].astype(str)
                for c in existing[1:]:
                    merged = merged + df2[c].astype(str)
                df2[new_name] = merged
                df2.drop(columns=existing, inplace=True)

        cols = list(df2.columns)
        M = len(cols)
        if M <= 1:
            return df2

        N = len(df2)
        if N <= 1:
            return df2

        # Choose sample size
        k_cap = 6000
        k_min = 2000
        K = min(N, int(early_stop) if early_stop is not None else N, k_cap)
        if N >= k_min:
            K = max(k_min, K)
        K = min(K, N)
        sample_df = df2.iloc[:K]

        # Precompute per-column sample strings
        col_vals = []
        for c in cols:
            col_vals.append(sample_df[c].astype(str).tolist())

        # Column metrics (use full N for nunique to be more stable)
        distinct_ratio = {}
        avg_len = {}
        prefix_exp = {}
        for idx, c in enumerate(cols):
            nunq = df2[c].nunique(dropna=False)
            distinct_ratio[idx] = float(nunq) / float(N) if N else 1.0
            vals = col_vals[idx]
            if vals:
                avg_len[idx] = sum(len(s) for s in vals) / float(len(vals))
                prefix_exp[idx] = _prefix_lcp_expectation(vals, max_l=4)
            else:
                avg_len[idx] = 0.0
                prefix_exp[idx] = 0.0

        def eval_perm(perm):
            strings = _build_strings_for_perm(col_vals, perm)
            return _eval_prefix_hits(strings)

        # Candidate initial permutations
        candidates = []
        candidates.append(list(range(M)))

        candidates.append(sorted(range(M), key=lambda i: (distinct_ratio[i], -avg_len[i])))
        candidates.append(sorted(range(M), key=lambda i: (-prefix_exp[i], distinct_ratio[i], -avg_len[i])))
        candidates.append(sorted(range(M), key=lambda i: (distinct_ratio[i] > distinct_value_threshold, distinct_ratio[i], -prefix_exp[i])))
        candidates.append(sorted(range(M), key=lambda i: (-(prefix_exp[i] * avg_len[i]), distinct_ratio[i])))

        # Deduplicate candidates
        seen = set()
        uniq_candidates = []
        for p in candidates:
            t = tuple(p)
            if t not in seen:
                seen.add(t)
                uniq_candidates.append(p)
        candidates = uniq_candidates[:8]

        best_perm = candidates[0]
        best_score = -1

        for p in candidates:
            if time.time() - start_time > time_budget:
                break
            sc = eval_perm(p)
            if sc > best_score:
                best_score = sc
                best_perm = p

        # Greedy forward selection optimizing prefix hits on growing prefix strings
        if time.time() - start_time <= time_budget:
            remaining = list(range(M))
            prefix = [""] * K
            greedy_perm = []
            greedy_score = -1
            for step in range(M):
                if time.time() - start_time > time_budget:
                    break
                best_c = None
                best_c_score = -1
                best_c_strings = None

                for c in remaining:
                    if time.time() - start_time > time_budget:
                        break
                    cv = col_vals[c]
                    cand_strings = [prefix[i] + cv[i] for i in range(K)]
                    sc = _eval_prefix_hits(cand_strings)
                    if sc > best_c_score:
                        best_c_score = sc
                        best_c = c
                        best_c_strings = cand_strings

                if best_c is None:
                    break

                greedy_perm.append(best_c)
                remaining.remove(best_c)
                prefix = best_c_strings
                greedy_score = best_c_score

            if len(greedy_perm) < M:
                remaining_sorted = sorted(remaining, key=lambda i: (distinct_ratio[i], -prefix_exp[i], -avg_len[i]))
                greedy_perm.extend(remaining_sorted)

            # Evaluate full greedy if not already full
            if len(greedy_perm) == M:
                sc = eval_perm(greedy_perm)
                if sc > best_score:
                    best_score = sc
                    best_perm = greedy_perm

        # Hill-climb with swaps on full permutation
        max_iter = max(1, int(col_stop) + 1)
        cur_perm = best_perm[:]
        cur_score = best_score

        for _ in range(max_iter):
            if time.time() - start_time > time_budget:
                break
            improved = False
            best_local_perm = cur_perm
            best_local_score = cur_score

            for i in range(M - 1):
                if time.time() - start_time > time_budget:
                    break
                for j in range(i + 1, M):
                    if time.time() - start_time > time_budget:
                        break
                    p2 = cur_perm[:]
                    p2[i], p2[j] = p2[j], p2[i]
                    sc = eval_perm(p2)
                    if sc > best_local_score:
                        best_local_score = sc
                        best_local_perm = p2
                        improved = True

            if improved:
                cur_perm = best_local_perm
                cur_score = best_local_score
            else:
                break

        final_perm = cur_perm

        ordered_cols = [cols[i] for i in final_perm]
        return df2.loc[:, ordered_cols]