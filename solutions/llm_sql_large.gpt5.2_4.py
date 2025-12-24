import numpy as np
import pandas as pd
from pandas.util import hash_pandas_object


class Solution:
    def _apply_col_merge(self, df: pd.DataFrame, col_merge):
        if not col_merge:
            return df

        df = df.copy()
        used = set()

        for group in col_merge:
            if not group:
                continue

            names = []
            for x in group:
                name = None
                if isinstance(x, (int, np.integer)):
                    xi = int(x)
                    if 0 <= xi < len(df.columns):
                        name = df.columns[xi]
                else:
                    try:
                        xs = str(x)
                    except Exception:
                        xs = None
                    if xs is not None and xs in df.columns:
                        name = xs

                if name is None or name in used or name not in df.columns:
                    continue
                names.append(name)

            if len(names) <= 1:
                continue

            for n in names:
                used.add(n)

            base_name = "+".join(names)
            new_name = base_name
            if new_name in df.columns:
                k = 1
                while f"{base_name}_{k}" in df.columns:
                    k += 1
                new_name = f"{base_name}_{k}"

            parts = [df[n].fillna("").astype(str) for n in names]
            merged = parts[0]
            for p in parts[1:]:
                merged = merged + p

            try:
                first_pos = min(df.columns.get_loc(n) for n in names if n in df.columns)
            except ValueError:
                first_pos = 0

            df.insert(first_pos, new_name, merged)
            df.drop(columns=[n for n in names if n in df.columns], inplace=True)

        return df

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
        df2 = self._apply_col_merge(df, col_merge)

        cols = list(df2.columns)
        m = len(cols)
        if m <= 1:
            return df2

        n = len(df2)
        S = int(min(n, 8000))
        if S <= 0:
            return df2

        rs = np.random.RandomState(0)
        if S < n:
            idx = rs.choice(n, size=S, replace=False)
            sdf = df2.iloc[idx]
        else:
            sdf = df2

        avg_len = {}
        distinct_ratio = {}
        base_score = {}
        col_hash = {}

        S_float = float(S)
        denom = S_float * S_float

        for c in cols:
            s = sdf[c].fillna("").astype(str)
            try:
                al = float(s.str.len().mean())
            except Exception:
                al = float(np.mean([len(x) for x in s.tolist()])) if S > 0 else 0.0

            codes, uniques = pd.factorize(s, sort=False)
            if codes.size == 0:
                dr = 1.0
                coll = 0.0
            else:
                cnt = np.bincount(codes.astype(np.int64, copy=False))
                coll = float(np.sum(cnt.astype(np.int64) * cnt.astype(np.int64))) / denom
                dr = float(len(uniques)) / S_float

            h = hash_pandas_object(s, index=False).values.astype(np.uint64, copy=False)

            avg_len[c] = al
            distinct_ratio[c] = dr
            col_hash[c] = h

            bs = (coll ** 1.3) * (al + 0.5)
            if dr >= distinct_value_threshold:
                bs *= 0.25
            base_score[c] = bs

        sorted_cols = sorted(cols, key=lambda x: base_score.get(x, 0.0), reverse=True)
        low_dist = [c for c in sorted_cols if distinct_ratio.get(c, 1.0) < distinct_value_threshold]
        high_dist = [c for c in sorted_cols if c not in low_dist]
        rest_order = low_dist + high_dist

        depth_limit = min(m, 10)
        if depth_limit <= 0:
            return df2[rest_order]

        beam_width = max(2, int(col_stop) if col_stop is not None else 2)
        expand_k = min(m, 14)
        decay = 0.95
        mult = np.uint64(1469598103934665603)  # FNV offset basis (used as multiplier in rolling hash)

        col_to_idx = {c: i for i, c in enumerate(cols)}
        col_bits = {c: (1 << col_to_idx[c]) for c in cols}

        def collision_prob(keys: np.ndarray) -> float:
            _, cnt = np.unique(keys, return_counts=True)
            cnt64 = cnt.astype(np.int64, copy=False)
            return float(np.sum(cnt64 * cnt64)) / denom

        beam = [(0.0, [], 0, np.zeros(S, dtype=np.uint64))]

        for depth in range(depth_limit):
            new_beam = []
            for score, seq, used_mask, keys in beam:
                tried = 0
                for c in rest_order:
                    bit = col_bits[c]
                    if used_mask & bit:
                        continue
                    tried += 1
                    if tried > expand_k:
                        break

                    new_keys = keys * mult + col_hash[c]
                    p = collision_prob(new_keys)
                    add = p * avg_len[c] * (decay ** depth)
                    new_beam.append((score + add, seq + [c], used_mask | bit, new_keys))

            if not new_beam:
                break
            new_beam.sort(key=lambda x: x[0], reverse=True)
            beam = new_beam[:beam_width]

        best_seq = beam[0][1] if beam else []
        used = set(best_seq)
        final_order = best_seq + [c for c in rest_order if c not in used]

        missing = [c for c in cols if c not in set(final_order)]
        if missing:
            final_order.extend(missing)

        return df2.loc[:, final_order]