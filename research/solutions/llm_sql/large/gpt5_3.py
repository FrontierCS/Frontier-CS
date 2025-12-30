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
        # Apply column merges first
        def unique_name(base, existing):
            if base not in existing:
                return base
            k = 1
            while True:
                cand = f"{base}__{k}"
                if cand not in existing:
                    return cand
                k += 1

        df_work = df.copy()
        if col_merge:
            existing_cols = set(df_work.columns)
            for idx, group in enumerate(col_merge):
                if not group:
                    continue
                group = [c for c in group if c in df_work.columns]
                if len(group) <= 1:
                    continue
                merge_name_base = f"__MERGED__{idx}"
                new_name = unique_name(merge_name_base, existing_cols)
                # Concatenate values as strings without separator
                new_series = df_work[group].astype(str).agg(''.join, axis=1)
                df_work[new_name] = new_series
                df_work.drop(columns=group, inplace=True)
                existing_cols.add(new_name)

        col_names = list(df_work.columns)
        M = len(col_names)
        if M <= 1:
            return df_work

        N = len(df_work)
        # Determine sample size
        target_sample = max(1000, int(row_stop) * 2000)
        sample_n = min(N, min(target_sample, max(1, int(early_stop))))
        if sample_n >= N:
            sample_idx = np.arange(N, dtype=np.int64)
        else:
            # Evenly spaced indices
            if sample_n <= 1:
                sample_idx = np.array([0], dtype=np.int64)
            else:
                step = (N - 1) / (sample_n - 1)
                idx_float = np.round(np.arange(sample_n) * step).astype(np.int64)
                # Ensure within bounds
                idx_float[idx_float < 0] = 0
                idx_float[idx_float >= N] = N - 1
                sample_idx = idx_float

        # Precompute codes and lengths for each column on sample
        col_codes = {}
        col_lens = {}
        col_total_len = {}
        base_score = {}

        # Helper to convert to strings for sample
        for name in col_names:
            # Extract sample values
            vals = df_work[name].to_numpy()
            sample_vals = vals[sample_idx]
            # Convert to string explicitly
            s_str = [str(x) for x in sample_vals]
            lens = np.fromiter((len(x) for x in s_str), dtype=np.int32, count=len(s_str))
            codes, _ = pd.factorize(s_str, sort=False)
            codes = codes.astype(np.int64, copy=False)
            col_codes[name] = codes
            col_lens[name] = lens
            total_len = lens.sum(dtype=np.int64)
            col_total_len[name] = float(total_len)

            # Base score when no grouping
            if codes.size > 0:
                counts = np.bincount(codes)
                sums = np.bincount(codes, weights=lens.astype(np.float64), minlength=len(counts))
                # Avoid division by zero, though counts should be >=1 for present codes
                with np.errstate(divide='ignore', invalid='ignore'):
                    penalty = np.sum(sums / counts)
                base_score[name] = col_total_len[name] - penalty
            else:
                base_score[name] = 0.0

        # Greedy ordering with group-aware scoring
        remaining = col_names.copy()
        selected = []
        n = sample_idx.shape[0]
        g_id = np.zeros(n, dtype=np.int64)

        # Determine candidate evaluation count per step
        topk_const = max(6, int(col_stop) * 6)

        while remaining:
            # Select top-k candidates by base_score as a fast prefilter
            rem_sorted = sorted(remaining, key=lambda c: (base_score.get(c, 0.0), col_total_len.get(c, 0.0)), reverse=True)
            k = min(len(remaining), topk_const)
            candidates = rem_sorted[:k]

            best_name = None
            best_val = -1e300

            # Evaluate exact incremental contribution for candidates under current grouping
            for c in candidates:
                codes = col_codes[c]
                lens = col_lens[c].astype(np.float64, copy=False)
                total_len = col_total_len[c]
                pair = (g_id.astype(np.int64) << 32) | codes.astype(np.int64, copy=False)
                uniq, inv, cnt = np.unique(pair, return_inverse=True, return_counts=True)
                sum_len = np.bincount(inv, weights=lens, minlength=len(uniq))
                with np.errstate(divide='ignore', invalid='ignore'):
                    penalty = np.sum(sum_len / cnt)
                score = float(total_len) - float(penalty)
                if score > best_val:
                    best_val = score
                    best_name = c

            if best_name is None:
                best_name = rem_sorted[0]

            selected.append(best_name)
            remaining.remove(best_name)

            # Update grouping with selected column
            codes_sel = col_codes[best_name]
            pair = (g_id.astype(np.int64) << 32) | codes_sel.astype(np.int64, copy=False)
            _, new_gid = np.unique(pair, return_inverse=True)
            g_id = new_gid.astype(np.int64, copy=False)

        # Return DataFrame with reordered columns
        return df_work.loc[:, selected]