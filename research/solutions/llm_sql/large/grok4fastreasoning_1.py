import pandas as pd
import numpy as np

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
        df = df.copy()
        col_set = set(df.columns)
        if col_merge is not None:
            for grp in col_merge:
                grp = [c for c in grp if c in col_set]
                if len(grp) > 1:
                    mname = 'merged_' + '_'.join(sorted(grp))
                    i = 0
                    while mname in col_set:
                        i += 1
                        mname = f'merged_{i}_' + '_'.join(sorted(grp))
                    df[mname] = df[grp].astype(str).apply(lambda x: ''.join(x), axis=1)
                    df = df.drop(columns=grp)
                    col_set.add(mname)
                    col_set.difference_update(grp)
        cols = list(df.columns)
        M = len(cols)
        if M <= 1:
            return df
        N = len(df)
        sample_size = row_stop * 1000
        sample_size = min(sample_size, N)
        if sample_size < N:
            idx = np.random.choice(N, sample_size, replace=False)
            idx.sort()
            df_s = df.iloc[idx].reset_index(drop=True)
        else:
            df_s = df
        ordered = []
        remaining = set(cols)
        max_steps = col_stop * 4
        max_steps = min(max_steps, M)
        for step in range(max_steps):
            if not remaining:
                break
            prev_cols = ordered[:]
            candidates = list(remaining)
            best_additional = -np.inf
            best_cand = None
            for cand in candidates:
                group_keys = prev_cols + [cand]
                g = df_s.groupby(group_keys, dropna=False)
                sizes = g.size()
                additional = 0.0
                if len(prev_cols) == 0:
                    for val, f in sizes.items():
                        if f >= 2:
                            additional += (f - 1) * len(str(val))
                else:
                    for idx, f in sizes.items():
                        if f >= 2:
                            val_cand = idx[-1]
                            additional += (f - 1) * len(str(val_cand))
                if additional > best_additional:
                    best_additional = additional
                    best_cand = cand
            if best_cand is None or best_additional <= 0:
                break
            ordered.append(best_cand)
            remaining.discard(best_cand)
        remain_cols = list(remaining)
        if remain_cols:
            scores = {}
            dist_counts = {}
            for c in remain_cols:
                str_series = df[c].astype(str)
                vc = str_series.value_counts()
                scores[c] = vc.max() / N if len(vc) > 0 else 0
                dist_counts[c] = len(str_series.unique()) / N
            low_dist = [c for c in remain_cols if dist_counts[c] <= distinct_value_threshold]
            high_dist = [c for c in remain_cols if dist_counts[c] > distinct_value_threshold]
            low_dist.sort(key=lambda c: -scores[c])
            high_dist.sort(key=lambda c: -scores[c])
            ordered += low_dist + high_dist
        return df[ordered]