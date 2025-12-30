import pandas as pd
import numpy as np
from bisect import bisect_left
from itertools import permutations


def _lcp_len(a: str, b: str) -> int:
    la = len(a)
    lb = len(b)
    n = la if la < lb else lb
    i = 0
    while i < n and a[i] == b[i]:
        i += 1
    return i


def _exact_online_lcp_score_for_strings(arr, n: int) -> int:
    if n <= 1:
        return 0
    lst = []
    score = 0
    for i in range(n):
        s = arr[i]
        if i == 0:
            lst.append(s)
            continue
        pos = bisect_left(lst, s)
        best = 0
        if pos > 0:
            best = _lcp_len(s, lst[pos - 1])
        if pos < len(lst):
            t = _lcp_len(s, lst[pos])
            if t > best:
                best = t
        score += best
        lst.insert(pos, s)
    return score


def _approx_online_prefix_tuple_score(perm, codes_lists, lens_lists, n: int) -> int:
    depth = len(perm)
    if depth == 0 or n <= 1:
        return 0

    # 64-bit rolling hash of prefix tuples (column-boundary approximation)
    mask = (1 << 64) - 1
    P = 1315423911
    offset = 1469598103934665603

    seen = [set() for _ in range(depth)]
    hs = [0] * depth

    code_arrs = [codes_lists[c] for c in perm]
    len_arrs = [lens_lists[c] for c in perm]

    score = 0
    for r in range(n):
        h = offset
        cum = 0
        best = 0
        for k in range(depth):
            h = (h * P + (code_arrs[k][r] + 2)) & mask
            hs[k] = h
            cum += len_arrs[k][r]
            if h in seen[k]:
                best = cum
        score += best
        for k in range(depth):
            seen[k].add(hs[k])
    return score


class Solution:
    def _apply_col_merges(self, df: pd.DataFrame, col_merge):
        if not col_merge:
            return df

        df_work = df.copy()
        orig_cols = list(df.columns)

        def resolve_name(x):
            if isinstance(x, (int, np.integer)):
                ix = int(x)
                if -len(orig_cols) <= ix < len(orig_cols):
                    return orig_cols[ix]
                return None
            return x

        for g in col_merge:
            if not g:
                continue
            names = []
            for x in g:
                nm = resolve_name(x)
                if nm is None:
                    continue
                if nm in df_work.columns:
                    names.append(nm)
            if len(names) <= 1:
                continue

            positions = [df_work.columns.get_loc(c) for c in names]
            pos = min(positions)

            base = "m__" + "__".join(str(c) for c in names)
            new_name = base
            suffix = 1
            while new_name in df_work.columns:
                new_name = f"{base}__{suffix}"
                suffix += 1

            s = df_work[names[0]].astype(str)
            for c in names[1:]:
                s = s + df_work[c].astype(str)

            df_work.insert(pos, new_name, s)
            df_work.drop(columns=names, inplace=True)

        return df_work

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
        df_work = self._apply_col_merges(df, col_merge)

        cols = list(df_work.columns)
        m = len(cols)
        n = len(df_work)
        if m <= 1 or n <= 1:
            return df_work

        # Sampling sizes for optimization (kept small for speed)
        n_beam = min(n, max(2000, min(int(early_stop) if early_stop else n, 8000)))
        n_refine = min(n, max(n_beam, min(int(early_stop) if early_stop else n, 15000)))
        n_exact = min(n, 4000)
        n_single = min(n, 2000)

        # Precompute string arrays, lengths, codes (as Python lists for fast loops)
        str_arrays = [None] * m
        lens_lists = [None] * m
        codes_lists = [None] * m
        distinct_ratio = [0.0] * m
        avg_len = [0.0] * m
        single_quality = [0.0] * m

        for i, c in enumerate(cols):
            arr = df_work[c].astype(str).to_numpy(dtype=object, copy=False)
            str_arrays[i] = arr

            lens = [len(x) for x in arr]
            lens_lists[i] = lens
            s_l = sum(lens)
            avg_len[i] = (s_l / n) if n else 0.0

            codes, uniques = pd.factorize(arr, sort=False)
            codes_lists[i] = codes.tolist()
            nu = len(uniques)
            distinct_ratio[i] = (nu / n) if n else 1.0

        # Column-level "prefix friendliness" (captures within-column shared prefixes even if distinct)
        for i in range(m):
            sc = _exact_online_lcp_score_for_strings(str_arrays[i], n_single)
            denom = sum(lens_lists[i][:n_single]) or 1
            single_quality[i] = sc / denom

        # Rank columns for exploration
        def col_rank_key(i):
            high = 1 if distinct_ratio[i] > distinct_value_threshold else 0
            return (high, distinct_ratio[i], -single_quality[i], -avg_len[i])

        ranked_cols = sorted(range(m), key=col_rank_key)

        # Helper for exact score of a permutation on sample rows
        def exact_score_perm(perm, n_rows):
            if n_rows <= 1:
                return 0
            arrs = [str_arrays[i] for i in perm]
            lst = []
            score = 0
            for r in range(n_rows):
                parts = [a[r] for a in arrs]
                s = "".join(parts)
                if r == 0:
                    lst.append(s)
                    continue
                pos = bisect_left(lst, s)
                best = 0
                if pos > 0:
                    best = _lcp_len(s, lst[pos - 1])
                if pos < len(lst):
                    t = _lcp_len(s, lst[pos])
                    if t > best:
                        best = t
                score += best
                lst.insert(pos, s)
            return score

        # Candidate generation
        candidates = []

        # Base heuristic permutation
        stats_perm = tuple(ranked_cols)
        candidates.append(stats_perm)

        beam_width = max(12, min(40, 10 * int(col_stop) + 10))
        local_iters = max(1, min(3, int(row_stop) // 2 if row_stop is not None else 2))

        # If small enough, brute-force approximate score
        if m <= 6:
            scored = []
            for perm in permutations(range(m)):
                sc = _approx_online_prefix_tuple_score(perm, codes_lists, lens_lists, n_beam)
                # tie-break using single_quality for early positions
                tie = 0.0
                w = 1.0
                for j in range(m):
                    tie += single_quality[perm[j]] * w
                    w *= 0.6
                scored.append((sc, tie, perm))
            scored.sort(key=lambda x: (x[0], x[1]), reverse=True)
            top = scored[: min(30, len(scored))]
            for _, _, perm in top:
                candidates.append(perm)
        else:
            # Beam search over approximate objective
            weights = [1.0 / (i + 1) for i in range(m)]
            beam = [(0, 0.0, tuple(), 0)]  # (score, tie, perm, mask)
            for depth in range(m):
                next_beam = []
                for sc0, tie0, perm0, mask0 in beam:
                    for c in ranked_cols:
                        bit = 1 << c
                        if mask0 & bit:
                            continue
                        perm1 = perm0 + (c,)
                        sc1 = _approx_online_prefix_tuple_score(perm1, codes_lists, lens_lists, n_beam)
                        tie1 = tie0 + single_quality[c] * weights[depth]
                        next_beam.append((sc1, tie1, perm1, mask0 | bit))
                next_beam.sort(key=lambda x: (x[0], x[1]), reverse=True)
                beam = next_beam[:beam_width]
            for sc, tie, perm, mask in beam[: min(12, len(beam))]:
                candidates.append(perm)

        # Deduplicate candidates
        uniq = []
        seen = set()
        for p in candidates:
            if p not in seen:
                seen.add(p)
                uniq.append(p)
        candidates = uniq

        # Local refinement on best approximate candidate
        def approx_score(perm, n_rows):
            return _approx_online_prefix_tuple_score(perm, codes_lists, lens_lists, n_rows)

        best_perm = max(candidates, key=lambda p: approx_score(p, n_refine))
        best_sc = approx_score(best_perm, n_refine)

        for _ in range(local_iters):
            improved = False
            cur = best_perm
            cur_sc = best_sc
            best_neighbor = cur
            best_neighbor_sc = cur_sc
            cur_list = list(cur)
            for i in range(m - 1):
                for j in range(i + 1, m):
                    nl = cur_list[:]
                    nl[i], nl[j] = nl[j], nl[i]
                    np_ = tuple(nl)
                    sc = approx_score(np_, n_refine)
                    if sc > best_neighbor_sc:
                        best_neighbor_sc = sc
                        best_neighbor = np_
            if best_neighbor_sc > best_sc:
                best_perm = best_neighbor
                best_sc = best_neighbor_sc
                improved = True
            if not improved:
                break

        # Add refined perm and neighbors for exact evaluation
        more = [best_perm]
        bp = list(best_perm)
        for i in range(m - 1):
            nl = bp[:]
            nl[i], nl[i + 1] = nl[i + 1], nl[i]
            more.append(tuple(nl))

        for p in more:
            if p not in seen:
                seen.add(p)
                candidates.append(p)

        # Final selection using exact online LCP on a smaller sample
        best_final = None
        best_final_sc = -1
        for p in candidates[: min(20, len(candidates))]:
            sc = exact_score_perm(p, n_exact)
            if sc > best_final_sc:
                best_final_sc = sc
                best_final = p

        if best_final is None:
            best_final = best_perm

        final_cols = [cols[i] for i in best_final]
        return df_work.loc[:, final_cols]