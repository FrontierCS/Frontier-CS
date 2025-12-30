import os
import pandas as pd


class Solution:
    def _apply_col_merge(self, df: pd.DataFrame, col_merge):
        if not col_merge:
            return df

        df = df.copy()
        used_columns = set()
        new_columns = []

        if not isinstance(col_merge, (list, tuple)):
            return df

        for idx, group in enumerate(col_merge):
            if not group:
                continue
            if not isinstance(group, (list, tuple)):
                group = [group]

            resolved = []
            cols = list(df.columns)
            n_cols = len(cols)

            for item in group:
                if isinstance(item, int):
                    if 0 <= item < n_cols:
                        name = cols[item]
                        if name not in resolved:
                            resolved.append(name)
                else:
                    if item in df.columns and item not in resolved:
                        resolved.append(item)

            if not resolved:
                continue

            names = [c for c in resolved if c not in used_columns]
            if not names:
                continue

            used_columns.update(names)

            base_name = f"MERGE_{idx}"
            new_name = base_name
            suffix = 1
            while new_name in df.columns or new_name in new_columns:
                new_name = f"{base_name}_{suffix}"
                suffix += 1

            s = df[names[0]].astype(str)
            for nm in names[1:]:
                s = s + df[nm].astype(str)
            df[new_name] = s
            new_columns.append(new_name)

        if used_columns:
            df = df.drop(columns=list(used_columns))

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
        df = self._apply_col_merge(df, col_merge)

        n_rows, n_cols = df.shape
        if n_cols <= 1 or n_rows <= 1:
            return df

        col_names = list(df.columns)
        cp = os.path.commonprefix

        # Precompute per-column string values, lengths, and statistics
        str_cols = []
        len_cols = []
        char_adj_scores = []
        dup_ratios = []
        eq_scores = []
        total_len_col = []

        for name in col_names:
            series = df[name].astype(str)
            vals = series.tolist()
            str_cols.append(vals)

            lens = [len(s) for s in vals]
            len_cols.append(lens)
            total_len = sum(lens)
            total_len_col.append(total_len)

            # Character-level adjacency prefix score within column
            if n_rows >= 2:
                prev = vals[0]
                lcp_sum_adj = 0
                for i in range(1, n_rows):
                    curr = vals[i]
                    lcp_sum_adj += len(cp([prev, curr]))
                    prev = curr
                char_adj_scores.append(lcp_sum_adj)
            else:
                char_adj_scores.append(0)

            # Duplicate ratio and equality-based score for this column alone
            seen = {}
            eq_sum = 0
            for s, l in zip(vals, lens):
                if s in seen:
                    eq_sum += l
                    seen[s] += 1
                else:
                    seen[s] = 1
            unique_count = len(seen)
            distinct_ratio = unique_count / float(n_rows) if n_rows > 0 else 0.0
            dup_ratio = 1.0 - distinct_ratio
            dup_ratios.append(dup_ratio)
            eq_scores.append(eq_sum)

        col_indices = list(range(n_cols))

        # Equality-based multi-column score using column-level prefix trie
        def equality_score(order):
            root = {}
            total_lcp = 0
            scols = str_cols
            lcols = len_cols
            for i in range(n_rows):
                node = root
                row_lcp = 0
                new_branch = False
                for c in order:
                    v = scols[c][i]
                    if not new_branch:
                        child = node.get(v)
                        if child is not None:
                            row_lcp += lcols[c][i]
                            node = child
                            continue
                        new_branch = True
                    child = {}
                    node[v] = child
                    node = child
                total_lcp += row_lcp
            return total_lcp

        # Greedy construction of order based on equality_score
        remaining = col_indices[:]
        eq_greedy_order = []
        while remaining:
            best_col = remaining[0]
            best_score = None
            for c in remaining:
                cand_order = eq_greedy_order + [c]
                sc_val = equality_score(cand_order)
                if best_score is None or sc_val > best_score:
                    best_score = sc_val
                    best_col = c
            eq_greedy_order.append(best_col)
            remaining.remove(best_col)

        # Normalized character adjacency scores
        char_adj_norm = []
        for c in range(n_cols):
            denom = total_len_col[c] if total_len_col[c] > 0 else 1.0
            char_adj_norm.append(char_adj_scores[c] / denom)

        # Candidate orders
        candidate_orders = []
        seen_orders = set()

        def add_order(order):
            t = tuple(order)
            if t not in seen_orders:
                seen_orders.add(t)
                candidate_orders.append(order)

        baseline_order = list(range(n_cols))
        add_order(baseline_order)
        add_order(eq_greedy_order)
        add_order(eq_greedy_order[::-1])

        # Order by character-based metric
        add_order(sorted(range(n_cols), key=lambda c: (-char_adj_norm[c], -dup_ratios[c], c)))

        # Order by duplicate ratio
        add_order(sorted(range(n_cols), key=lambda c: (-dup_ratios[c], -char_adj_norm[c], c)))

        # Mixed importance score
        weight_dup = 0.7
        weight_char = 0.3
        mix_scores = [
            weight_dup * dup_ratios[c] + weight_char * char_adj_norm[c]
            for c in range(n_cols)
        ]
        add_order(sorted(range(n_cols), key=lambda c: (-mix_scores[c], -total_len_col[c], c)))

        # Variations emphasizing best character-based column
        best_char_col = max(range(n_cols), key=lambda c: char_adj_norm[c])
        add_order([best_char_col] + [c for c in eq_greedy_order if c != best_char_col])
        add_order([c for c in eq_greedy_order if c != best_char_col] + [best_char_col])

        # Char-level adjacency-based scoring for candidate orders
        if isinstance(early_stop, int) and early_stop > 0:
            row_limit = min(n_rows, early_stop)
        else:
            row_limit = n_rows

        def char_order_score(order):
            scols = str_cols
            idxs = order
            n_use = row_limit
            if n_use <= 1:
                return 0
            rows = ["".join(scols[c][i] for c in idxs) for i in range(n_use)]
            total = 0
            prev = rows[0]
            local_cp = cp
            for j in range(1, n_use):
                curr = rows[j]
                total += len(local_cp([prev, curr]))
                prev = curr
            return total

        best_order = None
        best_score = None
        for order in candidate_orders:
            score_val = char_order_score(order)
            if best_score is None or score_val > best_score:
                best_score = score_val
                best_order = order

        if best_order is None:
            best_order = baseline_order

        best_col_names = [col_names[i] for i in best_order]
        return df[best_col_names]