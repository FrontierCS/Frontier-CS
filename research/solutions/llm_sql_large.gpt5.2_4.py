import pandas as pd
import numpy as np
from array import array
from typing import List, Any, Dict, Tuple, Optional


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
        if df is None or df.shape[1] <= 1:
            return df

        df = df.copy()

        def _resolve_merge_cols(group: Any, columns: List[Any]) -> List[Any]:
            if group is None:
                return []
            resolved = []
            colset = set(columns)
            for x in group:
                if x in colset:
                    resolved.append(x)
                else:
                    try:
                        ix = int(x)
                        if 0 <= ix < len(columns):
                            resolved.append(columns[ix])
                    except Exception:
                        pass
            # preserve order, dedupe
            out = []
            seen = set()
            for c in resolved:
                if c not in seen:
                    seen.add(c)
                    out.append(c)
            return out

        def _make_unique_name(base: str, existing: set) -> str:
            if base not in existing:
                return base
            k = 1
            while True:
                name = f"{base}__m{k}"
                if name not in existing:
                    return name
                k += 1

        if col_merge:
            for grp in col_merge:
                cols_now = list(df.columns)
                cols = _resolve_merge_cols(grp, cols_now)
                if len(cols) <= 1:
                    continue
                idxs = [df.columns.get_loc(c) for c in cols]
                first_idx = min(idxs)
                name_base = "+".join([str(c) for c in cols])
                merged_name = _make_unique_name(name_base, set(df.columns))

                merged = df[cols[0]].astype(str)
                for c in cols[1:]:
                    merged = merged.str.cat(df[c].astype(str), na_rep="nan")

                df.insert(first_idx, merged_name, merged)
                df.drop(columns=cols, inplace=True, errors="ignore")

        cols = list(df.columns)
        m = len(cols)
        n = len(df)
        if m <= 1 or n <= 1:
            return df

        sample_n = max(1000, int(row_stop) * 1000) if row_stop and row_stop > 0 else 4000
        if sample_n > 8000:
            sample_n = 8000
        if sample_n > n:
            sample_n = n
        sample_df = df.iloc[:sample_n]

        MASK = (1 << 64) - 1
        P = 1099511628211  # FNV prime

        def _lcp_cap(a: str, b: str, cap: int = 8) -> int:
            la = len(a)
            lb = len(b)
            lim = la if la < lb else lb
            if lim > cap:
                lim = cap
            i = 0
            while i < lim and a[i] == b[i]:
                i += 1
            return i

        col_data: Dict[Any, Dict[str, Any]] = {}
        for c in cols:
            s = sample_df[c].astype(str).to_numpy(dtype=object, copy=False)
            lens = array("I", (len(x) for x in s))

            codes0, uniques = pd.factorize(s, sort=False)
            codes_full = array("I", (int(x) + 1 for x in codes0))
            uniq_cnt = int(len(uniques))
            distinct_ratio = float(uniq_cnt) / float(sample_n)

            if uniq_cnt > 0:
                bc = np.bincount(np.asarray(codes0, dtype=np.int64))
                top_freq = float(bc.max()) / float(sample_n)
            else:
                top_freq = 0.0

            total_len = 0
            for L in lens:
                total_len += int(L)
            avg_len = float(total_len) / float(sample_n)

            # prefix similarity on subset of unique values
            uvals = list(uniques.tolist()) if uniq_cnt > 0 else []
            if len(uvals) > 512:
                step = max(1, len(uvals) // 512)
                uvals = uvals[::step][:512]
            uvals.sort()
            if len(uvals) >= 2:
                tot = 0
                prev = uvals[0]
                for i in range(1, len(uvals)):
                    cur = uvals[i]
                    tot += _lcp_cap(prev, cur, 8)
                    prev = cur
                prefix_sim = float(tot) / float(len(uvals) - 1)
            else:
                prefix_sim = 0.0

            # prefix codes
            prefixes_1 = [x[:1] if x else "" for x in s]
            prefixes_2 = [x[:2] if len(x) >= 2 else x for x in s]
            prefixes_4 = [x[:4] if len(x) >= 4 else x for x in s]
            prefixes_8 = [x[:8] if len(x) >= 8 else x for x in s]

            c1, _ = pd.factorize(prefixes_1, sort=False)
            c2, _ = pd.factorize(prefixes_2, sort=False)
            c4, _ = pd.factorize(prefixes_4, sort=False)
            c8, _ = pd.factorize(prefixes_8, sort=False)
            codes_1 = array("I", (int(x) + 1 for x in c1))
            codes_2 = array("I", (int(x) + 1 for x in c2))
            codes_4 = array("I", (int(x) + 1 for x in c4))
            codes_8 = array("I", (int(x) + 1 for x in c8))

            col_data[c] = {
                "full": codes_full,
                "len": lens,
                "c1": codes_1,
                "c2": codes_2,
                "c4": codes_4,
                "c8": codes_8,
                "uniq_cnt": uniq_cnt,
                "distinct_ratio": distinct_ratio,
                "top_freq": top_freq,
                "avg_len": avg_len,
                "prefix_sim": prefix_sim,
            }

        S = sample_n

        def _gain_exact(ch: array, codes_full: array, lens: array) -> int:
            seen = set()
            gain = 0
            seen_add = seen.add
            P_local = P
            mask = MASK
            for i in range(S):
                nh = (((ch[i] * P_local) & mask) ^ codes_full[i])
                if nh in seen:
                    gain += lens[i]
                else:
                    seen_add(nh)
            return gain

        def _gain_partial(ch: array, d: Dict[str, Any]) -> int:
            seen_full = set()
            seen1 = set()
            seen2 = set()
            seen4 = set()
            seen8 = set()
            sf_add = seen_full.add
            s1_add = seen1.add
            s2_add = seen2.add
            s4_add = seen4.add
            s8_add = seen8.add

            cfull = d["full"]
            c1 = d["c1"]
            c2 = d["c2"]
            c4 = d["c4"]
            c8 = d["c8"]
            lens = d["len"]

            gain = 0
            P_local = P
            mask = MASK
            for i in range(S):
                l = lens[i]
                base = (ch[i] * P_local) & mask
                hfull = base ^ cfull[i]
                if hfull in seen_full:
                    gain += l
                else:
                    if l >= 8:
                        h8 = base ^ c8[i]
                        if h8 in seen8:
                            gain += 8
                        else:
                            if l >= 4:
                                h4 = base ^ c4[i]
                                if h4 in seen4:
                                    gain += 4
                                else:
                                    if l >= 2:
                                        h2 = base ^ c2[i]
                                        if h2 in seen2:
                                            gain += 2
                                        else:
                                            if l >= 1:
                                                h1 = base ^ c1[i]
                                                if h1 in seen1:
                                                    gain += 1
                                    else:
                                        if l >= 1:
                                            h1 = base ^ c1[i]
                                            if h1 in seen1:
                                                gain += 1
                            else:
                                if l >= 2:
                                    h2 = base ^ c2[i]
                                    if h2 in seen2:
                                        gain += 2
                                    else:
                                        if l >= 1:
                                            h1 = base ^ c1[i]
                                            if h1 in seen1:
                                                gain += 1
                                else:
                                    if l >= 1:
                                        h1 = base ^ c1[i]
                                        if h1 in seen1:
                                            gain += 1
                    else:
                        if l >= 4:
                            h4 = base ^ c4[i]
                            if h4 in seen4:
                                gain += 4
                            else:
                                if l >= 2:
                                    h2 = base ^ c2[i]
                                    if h2 in seen2:
                                        gain += 2
                                    else:
                                        if l >= 1:
                                            h1 = base ^ c1[i]
                                            if h1 in seen1:
                                                gain += 1
                                else:
                                    if l >= 1:
                                        h1 = base ^ c1[i]
                                        if h1 in seen1:
                                            gain += 1
                        else:
                            if l >= 2:
                                h2 = base ^ c2[i]
                                if h2 in seen2:
                                    gain += 2
                                else:
                                    if l >= 1:
                                        h1 = base ^ c1[i]
                                        if h1 in seen1:
                                            gain += 1
                            else:
                                if l >= 1:
                                    h1 = base ^ c1[i]
                                    if h1 in seen1:
                                        gain += 1

                sf_add(hfull)
                if l >= 8:
                    s8_add(base ^ c8[i])
                    s4_add(base ^ c4[i])
                    s2_add(base ^ c2[i])
                    if l >= 1:
                        s1_add(base ^ c1[i])
                elif l >= 4:
                    s4_add(base ^ c4[i])
                    s2_add(base ^ c2[i])
                    if l >= 1:
                        s1_add(base ^ c1[i])
                elif l >= 2:
                    s2_add(base ^ c2[i])
                    if l >= 1:
                        s1_add(base ^ c1[i])
                elif l >= 1:
                    s1_add(base ^ c1[i])
            return gain

        def _update_hash(ch: array, codes_full: array) -> None:
            P_local = P
            mask = MASK
            for i in range(S):
                ch[i] = (((ch[i] * P_local) & mask) ^ codes_full[i])

        remaining = cols[:]
        selected: List[Any] = []
        current_hash = array("Q", (0 for _ in range(S)))

        max_partial_steps = 6
        evals = 0
        zero_streak = 0

        while remaining:
            best_col = None
            best_gain = -1
            step = len(selected)

            use_partial = step < max_partial_steps

            # Pre-sort candidates slightly to improve early selection / ties
            if step == 0:
                remaining.sort(
                    key=lambda x: (
                        col_data[x]["distinct_ratio"],
                        -col_data[x]["avg_len"],
                        -col_data[x]["top_freq"],
                        -col_data[x]["prefix_sim"],
                    )
                )

            for c in remaining:
                evals += 1
                if evals > early_stop:
                    best_col = None
                    break

                d = col_data[c]
                if use_partial:
                    gain = _gain_partial(current_hash, d)
                else:
                    gain = _gain_exact(current_hash, d["full"], d["len"])

                if gain > best_gain:
                    best_gain = gain
                    best_col = c
                elif gain == best_gain and best_col is not None:
                    db = col_data[best_col]
                    # tiebreaker: prefer lower distinct, higher length, higher prefix similarity
                    if (
                        d["distinct_ratio"] < db["distinct_ratio"]
                        or (d["distinct_ratio"] == db["distinct_ratio"] and d["avg_len"] > db["avg_len"])
                        or (d["distinct_ratio"] == db["distinct_ratio"] and d["avg_len"] == db["avg_len"] and d["prefix_sim"] > db["prefix_sim"])
                    ):
                        best_col = c

            if best_col is None:
                break

            if best_gain <= 0:
                zero_streak += 1
                if zero_streak >= 3 and len(selected) >= 1:
                    break
            else:
                zero_streak = 0

            selected.append(best_col)
            _update_hash(current_hash, col_data[best_col]["full"])
            remaining.remove(best_col)

            if len(selected) >= m:
                break

        if remaining:
            remaining.sort(
                key=lambda x: (
                    col_data[x]["distinct_ratio"],
                    -col_data[x]["prefix_sim"],
                    -col_data[x]["avg_len"],
                    -col_data[x]["top_freq"],
                )
            )
            selected.extend(remaining)

        # Ensure all columns included, preserve any missing due to weird merge specs
        sel_set = set(selected)
        for c in cols:
            if c not in sel_set:
                selected.append(c)

        return df.loc[:, selected]