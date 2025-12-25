import pandas as pd
import numpy as np
from typing import List, Any, Dict, Tuple, Optional


class Solution:
    def _resolve_merge_group(self, df_cols: List[Any], group: Any) -> List[Any]:
        if group is None:
            return []
        if not isinstance(group, (list, tuple)):
            group = [group]
        resolved = []
        seen = set()
        n = len(df_cols)
        for g in group:
            col = None
            if g in df_cols:
                col = g
            elif isinstance(g, (int, np.integer)):
                gi = int(g)
                if 0 <= gi < n:
                    col = df_cols[gi]
                elif 1 <= gi <= n:
                    col = df_cols[gi - 1]
            if col is not None and col not in seen:
                seen.add(col)
                resolved.append(col)
        return resolved

    def _apply_col_merge(self, df: pd.DataFrame, col_merge: Optional[list]) -> pd.DataFrame:
        if not col_merge:
            return df

        df = df.copy()
        cols = list(df.columns)

        for group in col_merge:
            cols = list(df.columns)
            group_cols = self._resolve_merge_group(cols, group)
            if len(group_cols) <= 1:
                continue
            if not all(c in df.columns for c in group_cols):
                group_cols = [c for c in group_cols if c in df.columns]
                if len(group_cols) <= 1:
                    continue

            positions = [cols.index(c) for c in group_cols if c in cols]
            if not positions:
                continue
            insert_pos = min(positions)

            base_name = "+".join(str(c) for c in group_cols)
            new_name = base_name
            if new_name in df.columns:
                k = 1
                while f"{base_name}__m{k}" in df.columns:
                    k += 1
                new_name = f"{base_name}__m{k}"

            sub = df[group_cols].astype(str)
            arr = sub.to_numpy(dtype=object, copy=False)
            merged = pd.Series(("".join(row) for row in arr), index=df.index)

            df.drop(columns=group_cols, inplace=True)
            df.insert(insert_pos, new_name, merged)

        return df

    def _compute_stats(
        self,
        df: pd.DataFrame,
        sample_n: int,
        distinct_value_threshold: float,
    ) -> Tuple[Dict[Any, float], Dict[Any, float], Dict[Any, float], Dict[Any, float], Dict[Any, float]]:
        n = len(df)
        if n == 0:
            return {}, {}, {}, {}, {}
        if sample_n >= n:
            sample = df
        else:
            sample = df.sample(n=sample_n, random_state=0)

        s_sample = sample.astype(str)
        n_s = len(s_sample)

        cp_full: Dict[Any, float] = {}
        prefix_head: Dict[Any, float] = {}
        avg_len: Dict[Any, float] = {}
        distinct_ratio: Dict[Any, float] = {}
        score: Dict[Any, float] = {}

        n_sq = float(n_s * n_s)

        for c in s_sample.columns:
            s = s_sample[c]

            counts = s.value_counts(dropna=False).to_numpy()
            if counts.size:
                cp = float(np.dot(counts, counts)) / n_sq
                dr = float(counts.size) / float(n_s)
            else:
                cp = 0.0
                dr = 1.0
            cp_full[c] = cp
            distinct_ratio[c] = dr

            arr = s.to_numpy(dtype=object, copy=False)
            al = float(sum(len(x) for x in arr)) / float(n_s) if n_s else 0.0
            avg_len[c] = al

            ph = 0.0
            t_cnt = 0
            if n_s:
                p1 = s.str.slice(0, 1)
                c1 = p1.value_counts(dropna=False).to_numpy()
                if c1.size:
                    ph += float(np.dot(c1, c1)) / n_sq
                    t_cnt += 1
                if al >= 2.0:
                    p2 = s.str.slice(0, 2)
                    c2 = p2.value_counts(dropna=False).to_numpy()
                    if c2.size:
                        ph += float(np.dot(c2, c2)) / n_sq
                        t_cnt += 1
            ph = (ph / t_cnt) if t_cnt else cp
            prefix_head[c] = ph

            penalty = 0.0
            if distinct_value_threshold is not None:
                excess = dr - float(distinct_value_threshold)
                if excess > 0:
                    penalty = 0.55 * excess

            sc = (5.0 * cp) + (1.3 * ph) + (0.02 * np.log1p(min(al, 200.0))) - penalty
            score[c] = float(sc)

        return score, cp_full, prefix_head, avg_len, distinct_ratio

    def _trie_prefix_sum_from_rows(self, arr2d: np.ndarray) -> int:
        nodes = [{}]
        nodes_append = nodes.append
        total = 0

        for row in arr2d:
            s = "".join(row)
            node = 0
            matched = 0
            for pos in range(len(s)):
                ch = s[pos]
                d = nodes[node]
                nxt = d.get(ch)
                if nxt is None:
                    total += matched
                    new = len(nodes)
                    d[ch] = new
                    nodes_append({})
                    node = new
                    for k in range(pos + 1, len(s)):
                        ch2 = s[k]
                        d2 = nodes[node]
                        new2 = len(nodes)
                        d2[ch2] = new2
                        nodes_append({})
                        node = new2
                    break
                node = nxt
                matched += 1
            else:
                total += matched

        return total

    def _pick_best_order(self, df: pd.DataFrame, candidates: List[List[Any]], eval_n: int) -> List[Any]:
        if not candidates:
            return list(df.columns)
        candidates_unique = []
        seen = set()
        cols_set = set(df.columns)
        for cand in candidates:
            if not cand:
                continue
            if len(cand) != len(cols_set):
                continue
            if set(cand) != cols_set:
                continue
            tup = tuple(cand)
            if tup in seen:
                continue
            seen.add(tup)
            candidates_unique.append(cand)

        if not candidates_unique:
            return list(df.columns)

        eval_n = max(1, min(len(df), int(eval_n)))
        eval_df = df.iloc[:eval_n].astype(str)

        best_order = candidates_unique[0]
        best_val = -1

        for order in candidates_unique:
            arr = eval_df[order].to_numpy(dtype=object, copy=False)
            val = self._trie_prefix_sum_from_rows(arr)
            if val > best_val:
                best_val = val
                best_order = order

        return best_order

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
        if df is None or df.shape[1] <= 1:
            return df

        df2 = self._apply_col_merge(df, col_merge)
        cols = list(df2.columns)
        m = len(cols)
        n = len(df2)
        if m <= 1 or n == 0:
            return df2

        sample_n = min(n, 8000)
        if n <= 2000:
            sample_n = n
        elif m >= 60:
            sample_n = min(sample_n, 6000)

        score, cp_full, prefix_head, avg_len, distinct_ratio = self._compute_stats(
            df2, sample_n=sample_n, distinct_value_threshold=distinct_value_threshold
        )

        def key_score(c):
            return (score.get(c, 0.0), cp_full.get(c, 0.0), prefix_head.get(c, 0.0), avg_len.get(c, 0.0))

        def key_cp(c):
            return (cp_full.get(c, 0.0), prefix_head.get(c, 0.0), avg_len.get(c, 0.0))

        def key_distinct(c):
            return (-distinct_ratio.get(c, 1.0), cp_full.get(c, 0.0), prefix_head.get(c, 0.0), avg_len.get(c, 0.0))

        cand1 = sorted(cols, key=key_score, reverse=True)
        cand2 = sorted(cols, key=key_cp, reverse=True)
        cand3 = sorted(cols, key=key_distinct, reverse=True)
        cand4 = cols[:]

        eval_n = min(n, 1800 if m >= 25 else 2500)
        best_order = self._pick_best_order(df2, [cand1, cand2, cand3, cand4], eval_n=eval_n)

        return df2.loc[:, best_order]
