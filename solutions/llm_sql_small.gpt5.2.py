import time
import math
import random
from typing import List, Any, Dict, Tuple, Optional

import numpy as np
import pandas as pd


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
        t0 = time.perf_counter()

        if df is None or df.shape[1] <= 1:
            return df

        df2 = df

        def _normalize_col(c):
            if isinstance(c, (int, np.integer)):
                if 0 <= int(c) < len(df2.columns):
                    return df2.columns[int(c)]
                return c
            return c

        def _unique_name(base: str) -> str:
            if base not in df2.columns:
                return base
            k = 2
            while f"{base}__{k}" in df2.columns:
                k += 1
            return f"{base}__{k}"

        # Apply column merges (robust to already-merged inputs)
        if col_merge:
            for grp in col_merge:
                if grp is None:
                    continue
                if not isinstance(grp, (list, tuple)) or len(grp) <= 1:
                    continue
                cols = [_normalize_col(c) for c in grp]
                cols_present = []
                seen = set()
                for c in cols:
                    if c in df2.columns and c not in seen:
                        cols_present.append(c)
                        seen.add(c)
                if len(cols_present) <= 1:
                    continue

                try:
                    pos = min(int(df2.columns.get_loc(c)) for c in cols_present)
                except Exception:
                    pos = 0

                merged = df2[cols_present[0]].astype(str)
                for c in cols_present[1:]:
                    merged = merged + df2[c].astype(str)

                new_name = _unique_name("+".join(map(str, cols_present)))
                df2.insert(pos, new_name, merged)
                df2.drop(columns=cols_present, inplace=True)

        cols = list(df2.columns)
        m = len(cols)
        if m <= 1:
            return df2

        n = len(df2)
        # Sample size for scoring
        sample_size = min(n, int(min(max(2000, n * 0.25), 6000, max(2000, early_stop))))
        if sample_size < 500:
            sample_size = min(n, 500)

        df_s = df2.iloc[:sample_size]

        # Tokenization: first T characters as 1-char tokens, then remainder as one token
        T = 3
        SHIFT = 32

        token_to_id: Dict[str, int] = {}
        next_tid = 1

        def _tok_id(tok: str) -> int:
            nonlocal next_tid
            tid = token_to_id.get(tok)
            if tid is None:
                tid = next_tid
                token_to_id[tok] = tid
                next_tid += 1
            return tid

        # Precompute per-column per-row token ids and token lengths
        tok_ids_by_col: List[List[Tuple[int, ...]]] = []
        tok_lens_by_col: List[List[Tuple[int, ...]]] = []

        # Heuristic stats
        nunique_list = []
        avg_len_list = []
        pref1_unique = []
        pref2_unique = []
        pref3_unique = []

        for c in cols:
            arr = df_s[c].astype(str).to_numpy()
            tok_ids_col: List[Tuple[int, ...]] = [()] * sample_size
            tok_lens_col: List[Tuple[int, ...]] = [()] * sample_size

            total_len = 0
            sset = set()
            p1 = set()
            p2 = set()
            p3 = set()

            for i in range(sample_size):
                v = arr[i]
                if v is None:
                    v = ""
                if not isinstance(v, str):
                    v = str(v)
                sset.add(v)
                lv = len(v)
                total_len += lv

                if lv >= 1:
                    p1.add(v[0])
                else:
                    p1.add("")
                if lv >= 2:
                    p2.add(v[:2])
                else:
                    p2.add(v)
                if lv >= 3:
                    p3.add(v[:3])
                else:
                    p3.add(v)

                if lv == 0:
                    tok_ids_col[i] = ()
                    tok_lens_col[i] = ()
                    continue

                # Build tokens
                ids = []
                lens = []
                k = min(T, lv)
                for j in range(k):
                    ids.append(_tok_id(v[j]))
                    lens.append(1)
                if lv > T:
                    rest = v[T:]
                    ids.append(_tok_id(rest))
                    lens.append(lv - T)

                tok_ids_col[i] = tuple(ids)
                tok_lens_col[i] = tuple(lens)

            tok_ids_by_col.append(tok_ids_col)
            tok_lens_by_col.append(tok_lens_col)

            nunique_list.append(len(sset))
            avg_len_list.append(total_len / max(1, sample_size))
            pref1_unique.append(len(p1))
            pref2_unique.append(len(p2))
            pref3_unique.append(len(p3))

        # Fast scoring using a single dict edge trie keyed by (node<<32)|token_id
        edges: Dict[int, int] = {}

        def score_perm(perm: List[int], nrows: int) -> int:
            edges.clear()
            next_node = 1
            total = 0

            tok_ids_cols = tok_ids_by_col
            tok_lens_cols = tok_lens_by_col
            edges_get = edges.get
            edges_set = edges.__setitem__

            for r in range(nrows):
                node = 0
                lcp = 0
                matched = True
                for ci in perm:
                    tlist = tok_ids_cols[ci][r]
                    llist = tok_lens_cols[ci][r]
                    lt = len(tlist)
                    for k in range(lt):
                        tok = tlist[k]
                        ln = llist[k]
                        key = (node << SHIFT) | tok
                        nxt = edges_get(key)
                        if matched and nxt is not None:
                            node = nxt
                            lcp += ln
                        else:
                            if matched:
                                matched = False
                            if nxt is None:
                                nxt = next_node
                                next_node += 1
                                edges_set(key, nxt)
                            node = nxt
                total += lcp
            return total

        # Heuristic initial order
        nunique_ratio = [nu / sample_size for nu in nunique_list]
        p1_ratio = [u / sample_size for u in pref1_unique]
        p2_ratio = [u / sample_size for u in pref2_unique]
        p3_ratio = [u / sample_size for u in pref3_unique]

        idxs = list(range(m))

        # Put very high-cardinality columns later
        low = [i for i in idxs if nunique_ratio[i] <= distinct_value_threshold]
        high = [i for i in idxs if nunique_ratio[i] > distinct_value_threshold]

        def _sort_key(i: int):
            # Lower diversity earlier, longer strings earlier within similar diversity
            return (nunique_ratio[i], p1_ratio[i], p2_ratio[i], p3_ratio[i], -avg_len_list[i])

        low.sort(key=_sort_key)
        high.sort(key=_sort_key)

        # Small tweak: if column name suggests ID and high cardinality, push to end
        def _is_id_name(name: str) -> bool:
            s = str(name).lower()
            return s == "id" or s.endswith("_id") or s.startswith("id_") or "uuid" in s

        ids = [i for i in idxs if _is_id_name(cols[i])]
        if ids:
            id_set = set(ids)
            base = [i for i in low if i not in id_set] + [i for i in high if i not in id_set] + ids
        else:
            base = low + high

        # Greedy build using smaller sample
        greedy_nrows = min(sample_size, 3000)
        greedy_perm: List[int] = []
        remaining = set(idxs)

        # Time budget (keep well under 10s average)
        time_budget = 2.4
        deadline = t0 + time_budget

        if time.perf_counter() < deadline and m <= 9 and greedy_nrows >= 500:
            while remaining and time.perf_counter() < deadline:
                best_c = None
                best_sc = -1
                prefix = greedy_perm
                for c in list(remaining):
                    sc = score_perm(prefix + [c], greedy_nrows)
                    if sc > best_sc:
                        best_sc = sc
                        best_c = c
                if best_c is None:
                    break
                greedy_perm.append(best_c)
                remaining.remove(best_c)
            if remaining:
                tail = list(remaining)
                tail.sort(key=_sort_key)
                greedy_perm.extend(tail)
        else:
            greedy_perm = base[:]

        # Candidate generation
        candidates: List[List[int]] = []
        candidates.append(base)
        candidates.append(greedy_perm)
        candidates.append(list(reversed(base)))

        # Adjacent swaps of base
        for i in range(m - 1):
            p = base[:]
            p[i], p[i + 1] = p[i + 1], p[i]
            candidates.append(p)

        # Random shuffles (stable seed from column names)
        seed = 1469598103934665603
        for name in cols:
            for ch in str(name):
                seed ^= ord(ch)
                seed *= 1099511628211
                seed &= (1 << 64) - 1
        rng = random.Random(seed)
        for _ in range(8):
            p = base[:]
            # shuffle mostly in the high-cardinality tail to keep structure
            split = max(0, m - max(2, min(4, m // 2)))
            head = p[:split]
            tail = p[split:]
            rng.shuffle(tail)
            candidates.append(head + tail)

        # Deduplicate candidates
        seen_c = set()
        uniq_candidates = []
        for p in candidates:
            tp = tuple(p)
            if tp not in seen_c:
                seen_c.add(tp)
                uniq_candidates.append(p)

        # Pick best candidate
        best_perm = base
        best_score = -1
        for p in uniq_candidates:
            if time.perf_counter() > deadline:
                break
            sc = score_perm(p, sample_size)
            if sc > best_score:
                best_score = sc
                best_perm = p

        # Local improvement: best pair swap hill-climb
        improvements = 0
        while improvements < 4 and time.perf_counter() < deadline:
            improved = False
            cur = best_perm
            cur_score = best_score
            best_local_perm = cur
            best_local_score = cur_score

            for i in range(m - 1):
                for j in range(i + 1, m):
                    if time.perf_counter() > deadline:
                        break
                    p = cur[:]
                    p[i], p[j] = p[j], p[i]
                    sc = score_perm(p, sample_size)
                    if sc > best_local_score:
                        best_local_score = sc
                        best_local_perm = p
                        improved = True
                if time.perf_counter() > deadline:
                    break

            if improved:
                best_perm = best_local_perm
                best_score = best_local_score
                improvements += 1
            else:
                break

        ordered_cols = [cols[i] for i in best_perm]
        return df2[ordered_cols]