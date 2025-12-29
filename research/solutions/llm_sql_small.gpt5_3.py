import pandas as pd
from collections import defaultdict
from typing import List, Tuple, Dict


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
        # Apply column merges if specified
        df_proc = self._apply_col_merge(df, col_merge)

        cols = list(df_proc.columns)
        M = len(cols)
        if M <= 1:
            return df_proc

        # Prepare per-column string values, ID mappings and lengths
        N = len(df_proc)
        col_values: List[List[str]] = []
        for c in cols:
            # Convert to string; keep as list for fast access
            col_values.append(df_proc[c].astype(str).tolist())

        # Build per-column value->id mapping and per-row ids, plus length per id
        id_data_by_col: List[List[int]] = []
        len_by_id_list: List[List[int]] = []
        unique_ratios: List[float] = []
        avg_len_list: List[float] = []

        for j in range(M):
            values = col_values[j]
            mapping: Dict[str, int] = {}
            id_data = [0] * N
            len_by_id: List[int] = []
            # Assign ids and lengths
            next_id = 0
            total_len = 0
            for i in range(N):
                v = values[i]
                idx = mapping.get(v)
                if idx is None:
                    idx = next_id
                    mapping[v] = idx
                    next_id += 1
                    len_by_id.append(len(v))
                id_data[i] = idx
                total_len += len_by_id[idx]
            id_data_by_col.append(id_data)
            len_by_id_list.append(len_by_id)
            unique_ratios.append(len(mapping) / float(N) if N > 0 else 0.0)
            avg_len_list.append(total_len / float(N) if N > 0 else 0.0)

        # Determine sample size R
        # Use early_stop to set an upper bound on rows processed, but clamp between [4000, 15000]
        # This keeps runtime low but robust
        R_upper = min(N, 15000)
        R_lower = min(N, 4000)
        if early_stop <= 0:
            R = R_upper
        else:
            R = max(R_lower, min(R_upper, early_stop))
        rows_range = range(R)

        # Beam size control
        beam_size = max(2, min(4, col_stop if isinstance(col_stop, int) else 2))

        # Initial scores for 1-column prefixes
        single_scores = []
        for j in range(M):
            score_j = self._score_single_col(id_data_by_col[j], len_by_id_list[j], rows_range)
            single_scores.append((score_j, j))

        # Tie-breaker: sort by score desc, then by unique ratio asc, then by avg_len desc, then column index
        single_scores.sort(key=lambda x: (-x[0], unique_ratios[x[1]], -avg_len_list[x[1]], x[1]))
        initial_cols = [j for _, j in single_scores[:beam_size]]

        # Build initial beam partials
        beam_partials = []
        for j in initial_cols:
            # Prepare per-row prefix keys and char lens
            ids_j = id_data_by_col[j]
            lens_by_id_j = len_by_id_list[j]
            keys_by_row = [(ids_j[i],) for i in rows_range]
            char_len_by_row = [lens_by_id_j[ids_j[i]] for i in rows_range]
            score1 = self._score_from_keys(keys_by_row, char_len_by_row)
            beam_partials.append({
                "order": (j,),
                "keys": keys_by_row,
                "lens": char_len_by_row,
                "score": score1
            })

        # Expand with beam search
        all_cols_idx = list(range(M))
        steps = M - 1
        for _ in range(steps):
            candidates = []
            for pidx, part in enumerate(beam_partials):
                used = set(part["order"])
                remaining = [c for c in all_cols_idx if c not in used]
                if not remaining:
                    continue
                for c in remaining:
                    score_c = self._score_expansion(part, c, id_data_by_col, len_by_id_list, rows_range)
                    candidates.append((score_c, pidx, c))

            if not candidates:
                break

            # Sort candidates by score desc, break ties with unique ratio asc and avg_len desc and column idx
            candidates.sort(key=lambda x: (-x[0], unique_ratios[x[2]], -avg_len_list[x[2]], x[2]))

            # Keep top beam_size expansions
            new_beam = []
            used_orders_set = set()
            for idx in range(min(beam_size, len(candidates))):
                score_c, base_idx, col_c = candidates[idx]
                base_part = beam_partials[base_idx]
                new_order = base_part["order"] + (col_c,)
                if new_order in used_orders_set:
                    continue
                # Build new prefix data for selected candidate
                keys2, lens2 = self._build_prefix_data(base_part, col_c, id_data_by_col, len_by_id_list, rows_range)
                new_beam.append({
                    "order": new_order,
                    "keys": keys2,
                    "lens": lens2,
                    "score": score_c
                })
                used_orders_set.add(new_order)
                if len(new_beam) >= beam_size:
                    break

            # If we didn't fill beam by expansions (rare), pad with previous partials extended by arbitrary remaining column
            if not new_beam:
                # Fallback: keep previous beam
                break
            beam_partials = new_beam

        # Choose best final order by last known score
        best_part = max(beam_partials, key=lambda p: p["score"])
        final_order = best_part["order"]

        # Return reordered DataFrame
        reordered_cols = [cols[i] for i in final_order]
        # Ensure all columns present (already are), but DataFrame should have exactly columns after merges
        return df_proc[reordered_cols]

    def _apply_col_merge(self, df: pd.DataFrame, col_merge: list) -> pd.DataFrame:
        if not col_merge:
            return df
        df2 = df.copy()
        existing = set(df2.columns)
        new_cols_order = [c for c in df2.columns]
        to_drop = set()
        merge_idx = 0
        for group in col_merge:
            valid = [c for c in group if c in existing and c not in to_drop]
            if not valid:
                continue
            # Create a unique new column name
            base_name = "MERGE_" + "_".join(valid)
            new_name = base_name
            while new_name in existing:
                merge_idx += 1
                new_name = f"{base_name}_{merge_idx}"
            # Concatenate without separators
            merged_series = df2[valid].astype(str).agg(''.join, axis=1)
            df2[new_name] = merged_series
            new_cols_order.append(new_name)
            existing.add(new_name)
            for c in valid:
                to_drop.add(c)
        if to_drop:
            remain = [c for c in df2.columns if c not in to_drop]
            # Keep merged columns at end order
            merged_only = [c for c in df2.columns if c not in remain]
            new_order = remain + merged_only
            # However, to strictly follow spec, we drop originals and keep merged columns
            df2 = df2.drop(columns=list(to_drop))
        return df2

    def _score_single_col(self, id_data: List[int], len_by_id: List[int], rows_range: range) -> int:
        counts: Dict[int, int] = {}
        for i in rows_range:
            vid = id_data[i]
            counts[vid] = counts.get(vid, 0) + 1
        score = 0
        for vid, ct in counts.items():
            if ct > 1:
                score += len_by_id[vid] * (ct - 1)
        return score

    def _score_from_keys(self, keys_by_row: List[Tuple[int, ...]], char_len_by_row: List[int]) -> int:
        counts: Dict[Tuple[int, ...], int] = {}
        first_len: Dict[Tuple[int, ...], int] = {}
        s = 0
        for i, key in enumerate(keys_by_row):
            cnt = counts.get(key)
            if cnt is None:
                counts[key] = 1
                first_len[key] = char_len_by_row[i]
            else:
                counts[key] = cnt + 1
        for key, ct in counts.items():
            if ct > 1:
                s += first_len[key] * (ct - 1)
        return s

    def _score_expansion(
        self,
        part: dict,
        col_c: int,
        id_data_by_col: List[List[int]],
        len_by_id_list: List[List[int]],
        rows_range: range
    ) -> int:
        # Compute score for prefix after adding column col_c
        ids_c = id_data_by_col[col_c]
        lens_by_id_c = len_by_id_list[col_c]
        counts: Dict[Tuple[int, ...], int] = {}
        first_len: Dict[Tuple[int, ...], int] = {}
        keys_by_row = part["keys"]
        char_len_by_row = part["lens"]
        # For each row, extend key and char length
        for i in rows_range:
            key2 = keys_by_row[i] + (ids_c[i],)
            cnt = counts.get(key2)
            if cnt is None:
                counts[key2] = 1
                first_len[key2] = char_len_by_row[i] + lens_by_id_c[ids_c[i]]
            else:
                counts[key2] = cnt + 1
        s = 0
        for key, ct in counts.items():
            if ct > 1:
                s += first_len[key] * (ct - 1)
        return s

    def _build_prefix_data(
        self,
        part: dict,
        col_c: int,
        id_data_by_col: List[List[int]],
        len_by_id_list: List[List[int]],
        rows_range: range
    ) -> Tuple[List[Tuple[int, ...]], List[int]]:
        keys_by_row_old = part["keys"]
        lens_by_row_old = part["lens"]
        ids_c = id_data_by_col[col_c]
        lens_by_id_c = len_by_id_list[col_c]
        keys2: List[Tuple[int, ...]] = []
        lens2: List[int] = []
        append_key = keys2.append
        append_len = lens2.append
        for i in rows_range:
            vid = ids_c[i]
            new_key = keys_by_row_old[i] + (vid,)
            append_key(new_key)
            append_len(lens_by_row_old[i] + lens_by_id_c[vid])
        return keys2, lens2