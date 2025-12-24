import pandas as pd
import numpy as np
from collections import Counter

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
        def apply_col_merge(df_in: pd.DataFrame, merges):
            if not merges:
                return df_in
            df_work = df_in.copy()
            used_cols = set()
            merge_count = 0
            for group in merges:
                if not group:
                    continue
                # Resolve group into column names
                names = []
                for x in group:
                    if isinstance(x, int):
                        if 0 <= x < len(df_work.columns):
                            names.append(df_work.columns[x])
                    else:
                        if x in df_work.columns:
                            names.append(x)
                if not names:
                    continue
                # Deduplicate, keep order
                seen = set()
                names = [c for c in names if not (c in seen or seen.add(c))]
                if not names:
                    continue
                new_col_name = f"MERGED_{merge_count}"
                merge_count += 1
                # Create merged column as concatenation of string representations
                merged_series = df_work[names].astype(str).agg(''.join, axis=1)
                # Ensure unique name
                temp_name = new_col_name
                idx = 1
                while temp_name in df_work.columns:
                    temp_name = f"{new_col_name}_{idx}"
                    idx += 1
                df_work[temp_name] = merged_series
                used_cols.update(names)
            if used_cols:
                # Drop original merged columns
                remaining = [c for c in df_work.columns if c not in used_cols]
                df_work = df_work[remaining]
            return df_work

        def compute_column_stats(str_df: pd.DataFrame):
            N = len(str_df)
            cols = list(str_df.columns)
            distinct_ratio = {}
            change_ratio = {}
            top_ratio = {}
            avg_len = {}
            max_avg_len = 0.0

            for c in cols:
                col_values = str_df[c].values
                # Distinct ratio
                try:
                    uniq = pd.Series(col_values).nunique(dropna=False)
                except Exception:
                    uniq = len(set(col_values.tolist()))
                distinct_ratio[c] = uniq / max(N, 1)
                # Change ratio
                changes = 0
                last = None
                first = True
                for v in col_values:
                    if first:
                        last = v
                        first = False
                    else:
                        if v != last:
                            changes += 1
                            last = v
                change_ratio[c] = changes / max(N - 1, 1)
                # Top ratio
                cnt = Counter(col_values)
                most_common_count = cnt.most_common(1)[0][1] if cnt else 0
                top_ratio[c] = most_common_count / max(N, 1)
                # Avg length
                total_len = 0
                for v in col_values:
                    total_len += len(v)
                avg = total_len / max(N, 1)
                avg_len[c] = avg
                if avg > max_avg_len:
                    max_avg_len = avg

            # Build priority scores per column
            scores = {}
            for c in cols:
                dr = distinct_ratio[c]
                cr = change_ratio[c]
                tr = top_ratio[c]
                al = avg_len[c] / (max_avg_len + 1e-9) if max_avg_len > 0 else 0.0
                score = 0.6 * dr + 0.3 * cr - 0.2 * tr - 0.15 * al
                if dr > distinct_value_threshold:
                    score += 0.05
                scores[c] = score
            return scores

        def prepare_arrays(str_df: pd.DataFrame, sample_n: int):
            cols = list(str_df.columns)
            M = len(cols)
            # Arrays (sample)
            arrays_sample = []
            lengths_sample = []
            hashes_sample = []
            sum_len_cols = []
            mask = (1 << 64) - 1

            for i, c in enumerate(cols):
                arr = str_df.iloc[:sample_n, i].values
                arrays_sample.append(arr)
                # Precompute lengths
                lens = np.fromiter((len(x) for x in arr), dtype=np.int32, count=sample_n)
                lengths_sample.append(lens)
                sum_len_cols.append(int(lens.sum()))
                # Precompute 64-bit hashes of values
                hlist = [hash(x) & mask for x in arr]
                hashes_sample.append(hlist)

            return arrays_sample, lengths_sample, hashes_sample, sum_len_cols

        def approx_evaluate_order(order_idx, hashes_by_col, lengths_by_col, sum_len_cols, sample_n):
            # Approximate using prefix equality on column boundaries with hashed prefixes
            if not order_idx:
                return 0.0
            depth = len(order_idx)
            sets_by_depth = [set() for _ in range(depth)]
            mask = (1 << 64) - 1
            FNV_OFFSET = 1469598103934665603
            FNV_PRIME = 1099511628211

            sum_lcp = 0
            for i in range(sample_n):
                # Find longest prefix present among previous rows
                prev = FNV_OFFSET
                tmax = 0
                for d in range(depth):
                    col = order_idx[d]
                    hv = hashes_by_col[col][i]
                    prev ^= hv
                    prev = (prev * FNV_PRIME) & mask
                    if prev in sets_by_depth[d]:
                        tmax = d + 1
                    else:
                        break
                if tmax > 0:
                    # Sum lengths of first tmax columns for this row
                    lsum = 0
                    for d in range(tmax):
                        col = order_idx[d]
                        lsum += int(lengths_by_col[col][i])
                    sum_lcp += lsum
                # Insert all prefixes for this row
                prev = FNV_OFFSET
                for d in range(depth):
                    col = order_idx[d]
                    hv = hashes_by_col[col][i]
                    prev ^= hv
                    prev = (prev * FNV_PRIME) & mask
                    sets_by_depth[d].add(prev)

            total_len = 0
            for col in order_idx:
                total_len += sum_len_cols[col]
            if total_len <= 0:
                return 0.0
            return float(sum_lcp) / float(total_len)

        def beam_search(str_df: pd.DataFrame, scores: dict, sample_n: int, row_stop: int, col_stop: int):
            cols = list(str_df.columns)
            M = len(cols)
            if M <= 1:
                return list(range(M))
            arrays_sample, lengths_sample, hashes_sample, sum_len_cols = prepare_arrays(str_df, sample_n)
            col_index = {c: i for i, c in enumerate(cols)}
            score_list = [scores[c] for c in cols]

            # Initial beam: empty order
            beams = [([], 0.0)]
            # Map for caching eval to avoid recomputing identical orders
            cache = {}

            for step in range(M):
                new_beams = []
                for order, _ in beams:
                    remaining = [i for i in range(M) if i not in order]
                    # select top-k candidates by heuristic scores
                    remaining_sorted = sorted(remaining, key=lambda x: score_list[x])
                    candidates = remaining_sorted[: max(1, min(col_stop, len(remaining_sorted)))]
                    for cidx in candidates:
                        new_order = tuple(order + [cidx])
                        if new_order in cache:
                            ratio = cache[new_order]
                        else:
                            ratio = approx_evaluate_order(list(new_order), hashes_sample, lengths_sample, sum_len_cols, sample_n)
                            cache[new_order] = ratio
                        new_beams.append((list(new_order), ratio))
                # Keep top row_stop beams by ratio
                if not new_beams:
                    break
                new_beams.sort(key=lambda x: (-x[1], len(x[0])))
                beams = new_beams[: max(1, min(row_stop, len(new_beams)))]
            # choose best final
            best_order = max(beams, key=lambda x: x[1])[0]
            # Local adjacent swap improvement (single pass)
            improved = True
            while improved:
                improved = False
                for i in range(len(best_order) - 1):
                    candidate = best_order[:]
                    candidate[i], candidate[i + 1] = candidate[i + 1], candidate[i]
                    cand_t = tuple(candidate)
                    if cand_t in cache:
                        cand_ratio = cache[cand_t]
                    else:
                        cand_ratio = approx_evaluate_order(candidate, hashes_sample, lengths_sample, sum_len_cols, sample_n)
                        cache[cand_t] = cand_ratio
                    if cand_ratio > cache.get(tuple(best_order), -1.0):
                        best_order = candidate
                        improved = True
                        break
            return best_order

        # Apply merges
        df_work = apply_col_merge(df, col_merge)
        if df_work.shape[1] <= 1:
            return df_work

        # String DataFrame for analysis
        str_df = df_work.astype(str)

        # Compute heuristic scores
        scores = compute_column_stats(str_df)

        # Determine sample size
        N = len(df_work)
        sample_n = int(min(max(1000, 1), N))  # ensure at least 1000 if possible
        sample_n = int(min(early_stop, N))  # use early_stop cap
        if sample_n <= 0:
            sample_n = N

        # Beam search to find a good order
        best_order_idx = beam_search(str_df, scores, sample_n, row_stop=row_stop, col_stop=col_stop)
        # Reorder columns
        cols = list(df_work.columns)
        ordered_cols = [cols[i] for i in best_order_idx]
        # Return reordered DataFrame
        return df_work[ordered_cols]
