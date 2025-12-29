import pandas as pd
import numpy as np
from array import array
import random
from typing import List, Tuple, Dict, Optional, Iterable


class Solution:
    def _apply_col_merge(self, df: pd.DataFrame, col_merge: Optional[list]) -> pd.DataFrame:
        if not col_merge:
            return df
        df = df.copy()
        for group in col_merge:
            if not group:
                continue
            cols = []
            for g in group:
                if isinstance(g, int):
                    if 0 <= g < df.shape[1]:
                        cols.append(df.columns[g])
                else:
                    if g in df.columns:
                        cols.append(g)
            if len(cols) < 2:
                continue
            cols = [c for c in cols if c in df.columns]
            if len(cols) < 2:
                continue

            positions = []
            for c in cols:
                try:
                    positions.append(df.columns.get_loc(c))
                except Exception:
                    pass
            pos = min(positions) if positions else 0

            s = df[cols[0]].astype(str)
            for c in cols[1:]:
                s = s + df[c].astype(str)

            new_name = "+".join(str(c) for c in cols)
            if new_name in df.columns:
                base = new_name
                k = 1
                while new_name in df.columns:
                    new_name = f"{base}_{k}"
                    k += 1

            df = df.drop(columns=cols)
            pos = min(pos, len(df.columns))
            df.insert(pos, new_name, s)
        return df

    def _stable_toposort(self, order: List[int], prereq_mask: List[int]) -> Optional[Tuple[int, ...]]:
        m = len(order)
        all_mask = 0
        for x in order:
            all_mask |= 1 << x

        remaining = list(order)
        chosen = []
        chosen_mask = 0

        pos = {c: i for i, c in enumerate(order)}
        for _ in range(m):
            best = None
            best_pos = 10**9
            for c in remaining:
                if prereq_mask[c] & ~chosen_mask:
                    continue
                p = pos.get(c, 10**9)
                if p < best_pos:
                    best_pos = p
                    best = c
            if best is None:
                return None
            chosen.append(best)
            chosen_mask |= 1 << best
            remaining.remove(best)

        if chosen_mask != all_mask:
            return None
        return tuple(chosen)

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
        df = self._apply_col_merge(df, col_merge)
        df = df.copy()

        df = df.fillna("")
        for c in df.columns:
            if df[c].dtype != object:
                df[c] = df[c].astype(str)
            else:
                df[c] = df[c].astype(str)

        cols = list(df.columns)
        m = len(cols)
        if m <= 1:
            return df

        n = len(df)
        if n <= 1:
            return df

        col_index = {c: i for i, c in enumerate(cols)}

        prereq_mask = [0] * m
        if one_way_dep:
            for dep in one_way_dep:
                if not dep or len(dep) < 2:
                    continue
                a, b = dep[0], dep[1]
                if isinstance(a, int):
                    ai = a if 0 <= a < m else None
                else:
                    ai = col_index.get(a, None)
                if isinstance(b, int):
                    bi = b if 0 <= b < m else None
                else:
                    bi = col_index.get(b, None)
                if ai is None or bi is None or ai == bi:
                    continue
                prereq_mask[bi] |= 1 << ai

        full_hash = [None] * m
        pref_hash = [None] * m
        full_len = [None] * m
        pref_len = [None] * m
        distinct_ratio = np.zeros(m, dtype=np.float64)
        avg_len = np.zeros(m, dtype=np.float64)
        pref_cap = np.zeros(m, dtype=np.int32)

        for i, c in enumerate(cols):
            s = df[c]
            hv = pd.util.hash_pandas_object(s, index=False).to_numpy(dtype=np.uint64, copy=False)
            a_hv = array("Q")
            a_hv.frombytes(hv.tobytes())
            full_hash[i] = a_hv

            lnp = s.str.len().to_numpy(dtype=np.uint32, copy=False)
            a_ln = array("I")
            a_ln.frombytes(lnp.tobytes())
            full_len[i] = a_ln

            distinct_ratio[i] = float(s.nunique(dropna=False)) / float(n)
            avg_len[i] = float(lnp.mean()) if n > 0 else 0.0

            med = float(np.median(lnp)) if n > 0 else 1.0
            p = int(med * 0.5)
            if p < 1:
                p = 1
            if p > 6:
                p = 6
            pref_cap[i] = p

            sp = s.str.slice(0, p)
            hp = pd.util.hash_pandas_object(sp, index=False).to_numpy(dtype=np.uint64, copy=False)
            a_hp = array("Q")
            a_hp.frombytes(hp.tobytes())
            pref_hash[i] = a_hp

            plnp = np.minimum(lnp, np.uint32(p))
            a_pln = array("I")
            a_pln.frombytes(plnp.tobytes())
            pref_len[i] = a_pln

        mask64 = 0xFFFFFFFFFFFFFFFF
        mult = 11400714819323198485
        add_full = 0x9E3779B97F4A7C15
        add_pref = 0xC2B2AE3D27D4EB4F

        def score_fullmatch(order: Tuple[int, ...], n_rows: int) -> int:
            k = len(order)
            if k <= 0:
                return 0
            seen = [set() for _ in range(k)]
            fh = full_hash
            fl = full_len
            mm = mult
            af = add_full
            msk = mask64

            num = 0

            h = 0
            l = 0
            for t, ci in enumerate(order):
                h = (h * mm + fh[ci][0] + af) & msk
                l += fl[ci][0]
                seen[t].add(h)

            for irow in range(1, n_rows):
                h = 0
                l = 0
                best = 0
                for t, ci in enumerate(order):
                    h = (h * mm + fh[ci][irow] + af) & msk
                    l += fl[ci][irow]
                    st = seen[t]
                    if h in st:
                        best = l
                    st.add(h)
                num += best
            return num

        def score_within_prefix(order: Tuple[int, ...], n_rows: int) -> int:
            k = len(order)
            if k <= 0:
                return 0
            seen_p = [set() for _ in range(k)]
            seen_f = [set() for _ in range(k)]
            fh = full_hash
            ph = pref_hash
            fl = full_len
            pl = pref_len
            mm = mult
            af = add_full
            ap = add_pref
            msk = mask64

            num = 0

            h_prev = 0
            l_prev = 0
            for t, ci in enumerate(order):
                hpv = (h_prev * mm + ph[ci][0] + ap) & msk
                hfv = (h_prev * mm + fh[ci][0] + af) & msk
                seen_p[t].add(hpv)
                seen_f[t].add(hfv)
                h_prev = hfv
                l_prev += fl[ci][0]

            for irow in range(1, n_rows):
                h_prev = 0
                l_prev = 0
                best = 0
                for t, ci in enumerate(order):
                    hpv = (h_prev * mm + ph[ci][irow] + ap) & msk
                    lpv = l_prev + pl[ci][irow]
                    sp = seen_p[t]
                    if hpv in sp and lpv > best:
                        best = lpv

                    hfv = (h_prev * mm + fh[ci][irow] + af) & msk
                    lfv = l_prev + fl[ci][irow]
                    sf = seen_f[t]
                    if hfv in sf and lfv > best:
                        best = lfv

                    sp.add(hpv)
                    sf.add(hfv)

                    h_prev = hfv
                    l_prev = lfv
                num += best
            return num

        sample_n = min(n, 3000)
        beam_width = min(14, max(6, 2 * m))

        all_cols = tuple(range(m))

        def allowed_next(mask: int, c: int) -> bool:
            if mask & (1 << c):
                return False
            if prereq_mask[c] & ~mask:
                return False
            return True

        beam: List[Tuple[int, Tuple[int, ...], int]] = [(0, tuple(), 0)]
        eval_count = 0

        for step in range(m):
            new_states: List[Tuple[int, Tuple[int, ...], int]] = []
            for _, ord_t, mask in beam:
                for c in all_cols:
                    if not allowed_next(mask, c):
                        continue
                    ord2 = ord_t + (c,)
                    mask2 = mask | (1 << c)
                    sc = score_fullmatch(ord2, sample_n)
                    new_states.append((sc, ord2, mask2))
                    eval_count += 1
                    if eval_count >= early_stop:
                        break
                if eval_count >= early_stop:
                    break
            if not new_states:
                break
            new_states.sort(key=lambda x: x[0], reverse=True)
            beam = new_states[:beam_width]
            if eval_count >= early_stop:
                break

        beam_orders = [b[1] for b in beam if len(b[1]) == m]
        if not beam_orders:
            beam_orders = [tuple(range(m))]

        heur_orders = []
        heur_orders.append(tuple(range(m)))
        heur_orders.append(tuple(sorted(range(m), key=lambda i: distinct_ratio[i])))
        heur_orders.append(tuple(sorted(range(m), key=lambda i: (distinct_ratio[i], -avg_len[i]))))
        heur_orders.append(tuple(sorted(range(m), key=lambda i: (-(avg_len[i] * (1.0 - distinct_ratio[i])), distinct_ratio[i]))))
        heur_orders.append(tuple(sorted(range(m), key=lambda i: (-avg_len[i], distinct_ratio[i]))))
        heur_orders.append(tuple(reversed(range(m))))

        rng = random.Random(0)
        rand_orders = []
        tries = 0
        target_rand = min(5, 3 * m)
        while len(rand_orders) < target_rand and tries < 200:
            tries += 1
            perm = list(range(m))
            rng.shuffle(perm)
            rand_orders.append(tuple(perm))

        candidates_set = set()
        candidates = []

        def add_candidate(ord_t: Tuple[int, ...]):
            if len(ord_t) != m:
                return
            fixed = self._stable_toposort(list(ord_t), prereq_mask)
            if fixed is None:
                return
            if fixed in candidates_set:
                return
            candidates_set.add(fixed)
            candidates.append(fixed)

        for o in heur_orders:
            add_candidate(o)
        for o in beam_orders:
            add_candidate(o)
        for o in rand_orders:
            add_candidate(o)

        if len(candidates) > 25:
            candidates = candidates[:25]

        best_order = candidates[0]
        best_score = -1

        for o in candidates:
            sc = score_within_prefix(o, n)
            if sc > best_score:
                best_score = sc
                best_order = o

        out_cols = [cols[i] for i in best_order]
        return df[out_cols]