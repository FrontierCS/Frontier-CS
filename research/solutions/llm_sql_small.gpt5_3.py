import pandas as pd
import time
from typing import List, Dict, Tuple


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
        SHIFT = 32

        def normalize_merge_groups(df_cols: List[str], col_merge) -> List[List[str]]:
            if not col_merge:
                return []
            cols = list(df_cols)
            groups = []
            for g in col_merge:
                names = []
                for x in g:
                    if isinstance(x, int):
                        if x < 0:
                            x = len(cols) + x
                        names.append(cols[x])
                    else:
                        names.append(str(x))
                groups.append([c for c in names if c in df_cols])
            # remove empty groups and duplicates
            res = []
            used = set()
            for g in groups:
                gg = [c for c in g if c not in used]
                if gg:
                    for c in gg:
                        used.add(c)
                    res.append(gg)
            return res

        def build_strings_for_columns(df: pd.DataFrame) -> Dict[str, List[str]]:
            res = {}
            for c in df.columns:
                col = df[c]
                # Convert to string in Python to keep consistency with str() behavior
                vals = col.tolist()
                svals = ["" if v is None else str(v) for v in vals]
                res[c] = svals
            return res

        def apply_merges(df: pd.DataFrame, merge_groups: List[List[str]]) -> Tuple[pd.DataFrame, List[str], Dict[str, List[str]]]:
            if not merge_groups:
                # No merges; return original df and string arrays
                s_map = build_strings_for_columns(df)
                return df.copy(), list(df.columns), s_map

            strings_map_orig = build_strings_for_columns(df)
            involved = set([c for g in merge_groups for c in g if c in df.columns])
            remaining_cols = [c for c in df.columns if c not in involved]
            new_cols = []
            new_strings_map = {}

            # Add remaining (unmerged) columns
            for c in remaining_cols:
                new_cols.append(c)
                new_strings_map[c] = strings_map_orig[c]

            # Add merged columns
            idx_merge = 0
            for g in merge_groups:
                cols_in_g = [c for c in g if c in df.columns]
                if not cols_in_g:
                    continue
                name = f"MERGE_{idx_merge}"
                idx_merge += 1
                arrs = [strings_map_orig[c] for c in cols_in_g]
                merged = ["".join(parts) for parts in zip(*arrs)]
                new_cols.append(name)
                new_strings_map[name] = merged

            # Build new df (preserve original types for remaining cols; merged as strings)
            data = {}
            for c in remaining_cols:
                data[c] = df[c]
            for c in new_cols:
                if c.startswith("MERGE_"):
                    data[c] = pd.Series(new_strings_map[c], index=df.index)
            new_df = pd.DataFrame(data)
            # Ensure column order
            new_df = new_df[new_cols]
            return new_df, new_cols, new_strings_map

        def precompute_column_meta(cols: List[str], strings_map: Dict[str, List[str]], Lmax: int):
            # For each column, compute:
            # - lengths
            # - value codes
            # - prefix codes for L=1..Lmax
            # - distinct ratio
            N = len(next(iter(strings_map.values()))) if strings_map else 0
            meta = {}
            for c in cols:
                arr = strings_map[c]
                lens = [len(s) for s in arr]
                # value code map
                code_map = {}
                val_codes = []
                next_code = 0
                for s in arr:
                    v = code_map.get(s)
                    if v is None:
                        v = next_code
                        code_map[s] = v
                        next_code += 1
                    val_codes.append(v)

                # prefix code maps
                pref_maps = []
                pref_codes = []
                for L in range(1, Lmax + 1):
                    pm = {}
                    pc = []
                    nc = 0
                    for s in arr:
                        p = s[:L] if len(s) >= L else s
                        v = pm.get(p)
                        if v is None:
                            v = nc
                            pm[p] = v
                            nc += 1
                        pc.append(v)
                    pref_maps.append(pm)
                    pref_codes.append(pc)

                distinct_ratio = len(code_map) / float(N) if N > 0 else 1.0
                avg_len = sum(lens) / float(N) if N > 0 else 0.0

                meta[c] = {
                    "lengths": lens,
                    "val_codes": val_codes,
                    "pref_codes": pref_codes,  # list of lists per L
                    "distinct_ratio": distinct_ratio,
                    "avg_len": avg_len,
                }
            return meta

        def evaluate_candidate(col: str, gids: List[int], meta, Lmax: int) -> int:
            m = meta[col]
            lens = m["lengths"]
            val_codes = m["val_codes"]
            pref_codes = m["pref_codes"]
            # global sets keyed by combined (gid, code)
            seen_full = set()
            seen_pref = [set() for _ in range(Lmax)]
            total = 0
            for i in range(len(gids)):
                g = gids[i]
                Ls = lens[i]
                code = val_codes[i]
                key = (g << SHIFT) | code
                if key in seen_full:
                    total += Ls
                else:
                    maxL = Lmax if Ls >= Lmax else Ls
                    found = False
                    for L in range(maxL, 0, -1):
                        pcode = pref_codes[L - 1][i]
                        pkey = (g << SHIFT) | pcode
                        if pkey in seen_pref[L - 1]:
                            total += L
                            found = True
                            break
                    # update sets
                    seen_full.add(key)
                    for L in range(1, maxL + 1):
                        pcode = pref_codes[L - 1][i]
                        seen_pref[L - 1].add((g << SHIFT) | pcode)
                    if not found:
                        # still need to have seen_full and prefixes updated; nothing more
                        pass
            return total

        def update_group_ids(gids: List[int], col: str, meta) -> List[int]:
            m = meta[col]
            val_codes = m["val_codes"]
            new_gids = [0] * len(gids)
            mapping = {}
            next_id = 0
            for i in range(len(gids)):
                key = (gids[i], val_codes[i])
                nid = mapping.get(key)
                if nid is None:
                    nid = next_id
                    mapping[key] = nid
                    next_id += 1
                new_gids[i] = nid
            return new_gids

        def greedy_order(cols: List[str], meta, Lmax: int) -> List[str]:
            # Start with all in remaining
            remaining = cols[:]
            N = len(meta[cols[0]]["lengths"]) if cols else 0
            gids = [0] * N
            order = []
            # Pre-evaluate first-column gains to pick a warm start quickly
            first_gains = {}
            for c in remaining:
                first_gains[c] = evaluate_candidate(c, gids, meta, Lmax)
            # Select first
            if not remaining:
                return order
            remaining.sort(key=lambda x: (-first_gains[x], meta[x]["distinct_ratio"], -meta[x]["avg_len"]))
            first = remaining.pop(0)
            order.append(first)
            gids = update_group_ids(gids, first, meta)

            while remaining:
                best_c = None
                best_gain = -1
                # Tie-breaker features
                best_tiebreak = None
                for c in remaining:
                    gain = evaluate_candidate(c, gids, meta, Lmax)
                    # tie breaker: prefer lower distinct ratio and higher avg length
                    tiebreak = (-(1.0 - meta[c]["distinct_ratio"]), -meta[c]["avg_len"])
                    if gain > best_gain or (gain == best_gain and (best_tiebreak is None or tiebreak < best_tiebreak)):
                        best_gain = gain
                        best_c = c
                        best_tiebreak = tiebreak
                order.append(best_c)
                remaining.remove(best_c)
                gids = update_group_ids(gids, best_c, meta)
            return order

        # Choose Lmax based on row count and parameter
        N = len(df)
        if N <= 0:
            return df
        # row_stop can influence Lmax
        try:
            candidate_Lmax = int(row_stop)
            if candidate_Lmax < 1:
                candidate_Lmax = 3
            Lmax = min(6, max(2, candidate_Lmax))
        except Exception:
            Lmax = 3
        if N > 24000 and Lmax > 4:
            Lmax = 4
        if N > 28000 and Lmax > 3:
            Lmax = 3

        # Apply merges
        merge_groups = normalize_merge_groups(list(df.columns), col_merge)
        df2, final_cols, strings_map = apply_merges(df, merge_groups)

        # Precompute meta
        meta = precompute_column_meta(final_cols, strings_map, Lmax)

        # Run greedy
        order = greedy_order(final_cols, meta, Lmax)

        # Return reordered df
        # Ensure order covers all final cols
        if set(order) != set(final_cols):
            # Fallback in case of any mismatch
            rem = [c for c in final_cols if c not in order]
            order = order + rem
        return df2[order]
