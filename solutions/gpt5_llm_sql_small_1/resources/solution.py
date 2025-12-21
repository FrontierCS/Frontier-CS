import pandas as pd
from collections import defaultdict
from typing import List, Dict, Tuple, Any


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
        def apply_col_merge(df_in: pd.DataFrame, merges: List[List[Any]]) -> pd.DataFrame:
            if not merges:
                return df_in
            df_out = df_in.copy()
            to_drop = set()
            new_cols_added = []
            cols_list = list(df_out.columns)

            def name_from_group(group_names: List[str]) -> str:
                base = "MERGED_" + "||".join(group_names)
                base = base if len(base) <= 128 else f"MERGED_{hash(tuple(group_names)) & 0xffffffff:x}"
                candidate = base
                k = 1
                while candidate in df_out.columns or candidate in new_cols_added:
                    candidate = f"{base}_{k}"
                    k += 1
                return candidate

            for g in merges:
                if not g:
                    continue
                # Resolve names/indices
                resolved = []
                for item in g:
                    if isinstance(item, int):
                        if 0 <= item < len(cols_list):
                            resolved.append(cols_list[item])
                    else:
                        if item in df_out.columns:
                            resolved.append(item)
                if not resolved:
                    continue
                # Deduplicate while preserving order
                seen = set()
                ordered = []
                for c in resolved:
                    if c not in seen:
                        seen.add(c)
                        ordered.append(c)
                if not ordered:
                    continue
                # Build merged series with vectorized string concatenation
                s = df_out[ordered[0]].astype(str)
                for c in ordered[1:]:
                    s = s + df_out[c].astype(str)
                new_name = name_from_group(ordered)
                df_out[new_name] = s
                new_cols_added.append(new_name)
                to_drop.update(ordered)
            if to_drop:
                df_out = df_out.drop(columns=[c for c in to_drop if c in df_out.columns])
            return df_out

        df_work = apply_col_merge(df, col_merge)

        columns: List[str] = list(df_work.columns)
        N = len(df_work)
        M = len(columns)
        if M <= 1 or N <= 1:
            return df_work

        Lmax = int(col_stop) if isinstance(col_stop, int) and col_stop >= 0 else 2
        if Lmax > 8:
            Lmax = 8

        # Precompute per-column strings, lengths, and prefixes up to Lmax
        values_str_map: Dict[str, List[str]] = {}
        lens_map: Dict[str, List[int]] = {}
        prefix_map: Dict[str, Dict[int, List[str]]] = {}

        for c in columns:
            # Convert to string
            s = df_work[c].astype(str)
            arr = s.tolist()
            values_str_map[c] = arr
            lens_map[c] = [len(v) for v in arr]
            if Lmax > 0:
                pmap = {}
                for l in range(1, Lmax + 1):
                    pmap[l] = [v[:l] if len(v) >= l else v for v in arr]
                prefix_map[c] = pmap
            else:
                prefix_map[c] = {}

        # Greedy selection of column order
        def compute_incremental_gain(col: str, group_ids: List[int]) -> int:
            strings = values_str_map[col]
            lengths = lens_map[col]
            pmap = prefix_map[col]
            gain = 0
            seen_full_by_group: Dict[int, set] = {}
            if Lmax > 0:
                seen_prefix_by_l: List[Dict[int, set]] = [dict() for _ in range(Lmax)]
            else:
                seen_prefix_by_l = []

            for i in range(N):
                gid = group_ids[i]
                v = strings[i]
                lenc = lengths[i]
                sfull = seen_full_by_group.get(gid)
                if sfull is None:
                    sfull = set()
                    seen_full_by_group[gid] = sfull
                if v in sfull:
                    gain += lenc
                else:
                    if Lmax > 0 and lenc > 0:
                        ll = lenc if lenc < Lmax else Lmax
                        added = False
                        for l in range(ll, 0, -1):
                            sprefix_map = seen_prefix_by_l[l - 1]
                            sp = sprefix_map.get(gid)
                            if sp is not None:
                                pv = pmap[l][i]
                                if pv in sp:
                                    gain += l
                                    added = True
                                    break
                    # Update sets after scoring
                    sfull.add(v)
                    if Lmax > 0 and lenc > 0:
                        ll = lenc if lenc < Lmax else Lmax
                        for l in range(1, ll + 1):
                            sprefix_map = seen_prefix_by_l[l - 1]
                            sp = sprefix_map.get(gid)
                            if sp is None:
                                sp = set()
                                sprefix_map[gid] = sp
                            sp.add(pmap[l][i])
            return gain

        def update_group_ids(prev_group_ids: List[int], col: str) -> List[int]:
            strings = values_str_map[col]
            mapping: Dict[Tuple[int, str], int] = {}
            new_ids = [0] * N
            next_id = 0
            for i in range(N):
                key = (prev_group_ids[i], strings[i])
                gid = mapping.get(key)
                if gid is None:
                    gid = next_id
                    next_id += 1
                    mapping[key] = gid
                new_ids[i] = gid
            return new_ids

        remaining = columns[:]
        selected_order: List[str] = []
        group_ids = [0] * N

        while remaining:
            best_col = None
            best_score = -1
            # Evaluate each candidate
            for c in remaining:
                score = compute_incremental_gain(c, group_ids)
                if score > best_score:
                    best_score = score
                    best_col = c
            if best_col is None:
                # Fallback: append remaining in current order
                selected_order.extend(remaining)
                remaining.clear()
            else:
                selected_order.append(best_col)
                remaining.remove(best_col)
                group_ids = update_group_ids(group_ids, best_col)

        # Approximate evaluation for an order using prefix up to Lmax; used for local improvement
        def evaluate_order(order: List[str]) -> int:
            if not order:
                return 0
            steps = len(order)
            # For each step index, maintain seen_full and seen_prefix dicts keyed by group id
            seen_full_step: List[Dict[int, set]] = [dict() for _ in range(steps)]
            if Lmax > 0:
                seen_prefix_step: List[List[Dict[int, set]]] = [[dict() for _ in range(steps)] for _ in range(Lmax)]
            else:
                seen_prefix_step = []
            step_maps: List[Dict[Tuple[int, str], int]] = [dict() for _ in range(steps)]
            step_next_id: List[int] = [0 for _ in range(steps)]

            total = 0
            for i in range(N):
                gid = 0
                for t in range(steps):
                    col = order[t]
                    strings = values_str_map[col]
                    v = strings[i]
                    lenc = lens_map[col][i]
                    sfull_map = seen_full_step[t]
                    sfull = sfull_map.get(gid)
                    if sfull is None:
                        sfull = set()
                        sfull_map[gid] = sfull
                    if v in sfull:
                        total += lenc
                        # advance group id
                        smap = step_maps[t]
                        key = (gid, v)
                        gnext = smap.get(key)
                        if gnext is None:
                            gnext = step_next_id[t]
                            step_next_id[t] += 1
                            smap[key] = gnext
                        gid = gnext
                        continue
                    # compute partial prefix
                    p_len = 0
                    if Lmax > 0 and lenc > 0:
                        ll = lenc if lenc < Lmax else Lmax
                        pmap = prefix_map[col]
                        for l in range(ll, 0, -1):
                            sprefix_map = seen_prefix_step[l - 1][t]
                            sp = sprefix_map.get(gid)
                            if sp is not None:
                                pv = pmap[l][i]
                                if pv in sp:
                                    p_len = l
                                    break
                    total += p_len
                    # update sets and mapping for this column
                    sfull.add(v)
                    if Lmax > 0 and lenc > 0:
                        ll = lenc if lenc < Lmax else Lmax
                        pmap = prefix_map[col]
                        for l in range(1, ll + 1):
                            sprefix_map = seen_prefix_step[l - 1][t]
                            sp = sprefix_map.get(gid)
                            if sp is None:
                                sp = set()
                                sprefix_map[gid] = sp
                            sp.add(pmap[l][i])
                    smap = step_maps[t]
                    key = (gid, v)
                    gnext = smap.get(key)
                    if gnext is None:
                        gnext = step_next_id[t]
                        step_next_id[t] += 1
                        smap[key] = gnext
                    # LCP stops at first mismatch
                    break
            return total

        # Local adjacent swap improvement (single pass)
        if M >= 2:
            current_order = selected_order[:]
            current_score = evaluate_order(current_order)
            improved = True
            # Single pass of adjacent swaps with first-improvement strategy
            for i in range(len(current_order) - 1):
                new_order = current_order[:]
                new_order[i], new_order[i + 1] = new_order[i + 1], new_order[i]
                new_score = evaluate_order(new_order)
                if new_score > current_score:
                    current_order = new_order
                    current_score = new_score
            selected_order = current_order

        # Return DataFrame with reordered columns
        return df_work[selected_order]
