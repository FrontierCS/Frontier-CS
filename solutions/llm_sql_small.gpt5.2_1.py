import time
from typing import List, Any, Dict, Tuple, Optional

import numpy as np
import pandas as pd


class Solution:
    def _normalize_merge_group(self, group: list, columns: List[Any]) -> List[Any]:
        if not group:
            return []
        out = []
        for g in group:
            if isinstance(g, (int, np.integer)):
                if 0 <= int(g) < len(columns):
                    out.append(columns[int(g)])
            else:
                out.append(g)
        return out

    def _apply_col_merge(self, df: pd.DataFrame, col_merge: Optional[list]) -> pd.DataFrame:
        if not col_merge:
            return df
        df2 = df.copy()
        for group in col_merge:
            if not group:
                continue
            cur_cols = list(df2.columns)
            norm_group = self._normalize_merge_group(group, cur_cols)
            exist = [c for c in norm_group if c in df2.columns]
            if len(exist) <= 1:
                continue

            pos = min(int(df2.columns.get_loc(c)) for c in exist)
            merged = df2[exist[0]].astype(str)
            for c in exist[1:]:
                merged = merged + df2[c].astype(str)

            base_name = "MERGE_" + "+".join(str(c) for c in exist)
            new_name = base_name
            k = 1
            while new_name in df2.columns:
                k += 1
                new_name = f"{base_name}_{k}"

            df2 = df2.drop(columns=exist)
            df2.insert(pos, new_name, merged)
        return df2

    @staticmethod
    def _avg_len(arr_obj: np.ndarray) -> float:
        s = 0
        n = int(arr_obj.shape[0])
        for x in arr_obj:
            s += len(x)
        return s / n if n else 0.0

    @staticmethod
    def _build_prefix_arr(arr_obj: np.ndarray, L: int) -> np.ndarray:
        if L <= 0:
            return arr_obj
        out = np.empty(arr_obj.shape[0], dtype=object)
        i = 0
        for s in arr_obj:
            out[i] = s[:L]
            i += 1
        return out

    @staticmethod
    def _collision_sum(prefix_ids: np.ndarray, key_arr: np.ndarray) -> int:
        counts: Dict[Tuple[int, Any], int] = {}
        get = counts.get
        for pid, val in zip(prefix_ids, key_arr):
            k = (int(pid), val)
            counts[k] = get(k, 0) + 1
        tot = 0
        for c in counts.values():
            tot += c * c
        return tot

    @staticmethod
    def _update_prefix_ids(prefix_ids: np.ndarray, key_arr: np.ndarray) -> np.ndarray:
        mp: Dict[Tuple[int, Any], int] = {}
        get = mp.get
        next_ids = np.empty(prefix_ids.shape[0], dtype=np.int32)
        nid = 0
        i = 0
        for pid, val in zip(prefix_ids, key_arr):
            k = (int(pid), val)
            v = get(k)
            if v is None:
                v = nid
                mp[k] = v
                nid += 1
            next_ids[i] = v
            i += 1
        return next_ids

    @staticmethod
    def _lcp_trie_sum(strings: List[str]) -> int:
        root: Dict[str, dict] = {}
        total = 0
        for i, s in enumerate(strings):
            node = root
            l = 0
            matched = (i != 0)
            for ch in s:
                nxt = node.get(ch)
                if matched and nxt is not None:
                    l += 1
                    node = nxt
                else:
                    matched = False
                    if nxt is None:
                        nxt = {}
                        node[ch] = nxt
                    node = nxt
            total += l
        return total

    def _evaluate_perm(self, perm_idx: List[int], eval_cols_u: List[np.ndarray]) -> int:
        if not perm_idx:
            return 0
        res = eval_cols_u[perm_idx[0]].copy()
        for j in perm_idx[1:]:
            res = np.char.add(res, eval_cols_u[j])
        strings = res.tolist()
        return self._lcp_trie_sum(strings)

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
        t0 = time.time()

        df2 = self._apply_col_merge(df, col_merge)
        cols = list(df2.columns)
        m = len(cols)
        if m <= 1:
            return df2

        n = len(df2)
        if n <= 1:
            return df2

        K_greedy = int(min(n, 8000, early_stop if early_stop else n))
        K_eval = int(min(n, 2500, early_stop if early_stop else n))

        distinct_ratio: Dict[Any, float] = {}
        avg_len: Dict[Any, float] = {}

        for c in cols:
            try:
                distinct_ratio[c] = float(df2[c].nunique(dropna=False)) / float(n)
            except Exception:
                distinct_ratio[c] = 1.0

        full_obj: Dict[Any, np.ndarray] = {}
        pref_obj: Dict[Any, Dict[int, np.ndarray]] = {}
        prefix_lens = (2, 4, 8)

        head_g = df2[cols].head(K_greedy)
        for c in cols:
            arr = head_g[c].astype(str).to_numpy(dtype=object, copy=False)
            full_obj[c] = arr
            avg_len[c] = self._avg_len(arr)
            pdict: Dict[int, np.ndarray] = {}
            for L in prefix_lens:
                pdict[L] = self._build_prefix_arr(arr, L)
            pref_obj[c] = pdict

        remaining = cols[:]
        perm: List[Any] = []
        prefix_ids = np.zeros(K_greedy, dtype=np.int32)

        # Greedy build
        for pos in range(m):
            best_c = None
            best_metric = -1.0
            best_key_arr = None

            use_prefix = (pos < 2)

            for c in remaining:
                dr = distinct_ratio.get(c, 1.0)
                pen = 0.35 + 0.65 * max(0.0, 1.0 - dr)
                if dr >= 0.98:
                    pen *= 0.25
                if dr >= distinct_value_threshold:
                    pen *= 0.75

                if use_prefix:
                    # consider several prefix lengths and full
                    # metric approximates "prefix LCP gained" = collision * prefix_len
                    local_best_metric = -1.0
                    local_best_key = None

                    for L in prefix_lens:
                        key_arr = pref_obj[c][L]
                        coll = self._collision_sum(prefix_ids, key_arr)
                        metric = float(coll) * float(L) * pen
                        if metric > local_best_metric:
                            local_best_metric = metric
                            local_best_key = key_arr

                    # also consider full value match with average length
                    key_arr_full = full_obj[c]
                    coll_full = self._collision_sum(prefix_ids, key_arr_full)
                    metric_full = float(coll_full) * float(avg_len[c]) * pen
                    if metric_full > local_best_metric:
                        local_best_metric = metric_full
                        local_best_key = key_arr_full

                    metric = local_best_metric
                    key_arr = local_best_key
                else:
                    key_arr = full_obj[c]
                    coll = self._collision_sum(prefix_ids, key_arr)
                    metric = float(coll) * float(avg_len[c]) * pen

                if metric > best_metric:
                    best_metric = metric
                    best_c = c
                    best_key_arr = key_arr

            if best_c is None:
                break
            perm.append(best_c)
            remaining.remove(best_c)
            if best_key_arr is not None:
                prefix_ids = self._update_prefix_ids(prefix_ids, best_key_arr)

        if remaining:
            # push high-distinct to end, low-distinct earlier among remaining
            remaining.sort(key=lambda c: (distinct_ratio.get(c, 1.0), -avg_len.get(c, 0.0)))
            perm.extend(remaining)

        # Optional local refinement with small hill-climb using actual char-trie on K_eval
        head_e = df2[perm].head(K_eval)
        eval_cols_u: List[np.ndarray] = [head_e[c].astype(str).to_numpy(dtype=str, copy=False) for c in perm]

        perm_idx = list(range(len(perm)))
        best_score = self._evaluate_perm(perm_idx, eval_cols_u)
        best_perm_idx = perm_idx[:]

        max_iters = 3
        for _ in range(max_iters):
            improved = False
            for i in range(len(perm_idx) - 1):
                cand = best_perm_idx[:]
                cand[i], cand[i + 1] = cand[i + 1], cand[i]
                sc = self._evaluate_perm(cand, eval_cols_u)
                if sc > best_score:
                    best_score = sc
                    best_perm_idx = cand
                    improved = True
            if not improved:
                break
            if time.time() - t0 > 9.5:
                break

        final_perm = [perm[i] for i in best_perm_idx]
        return df2[final_perm]