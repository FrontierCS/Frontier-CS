import pandas as pd
from collections import Counter
from itertools import permutations


class Solution:
    def _compute_hit_rate(self, str_cols, total_chars, perm):
        if not str_cols or total_chars <= 0:
            return 0.0

        num_rows = len(str_cols[0])
        if num_rows == 0:
            return 0.0

        root = {}
        total_lcp = 0
        perm_list = list(perm)
        sc = str_cols

        for i in range(num_rows):
            node = root
            mismatch = False
            lcp = 0
            for col_idx in perm_list:
                cell_s = sc[col_idx][i]
                for ch in cell_s:
                    child = node.get(ch)
                    if not mismatch and child is not None:
                        lcp += 1
                        node = child
                    else:
                        mismatch = True
                        if child is None:
                            child = {}
                            node[ch] = child
                        node = child
            total_lcp += lcp

        return total_lcp / float(total_chars) if total_chars > 0 else 0.0

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

        # Apply column merges if specified
        if col_merge:
            original_columns = list(df.columns)
            for merge_idx, group in enumerate(col_merge):
                if not group:
                    continue

                # Map group entries (names or indices) to actual column names
                col_names_group = []
                for g in group:
                    name = None
                    if isinstance(g, int):
                        if 0 <= g < len(original_columns):
                            name = original_columns[g]
                    else:
                        if g in original_columns:
                            name = g
                    if name is not None and name in df.columns and name not in col_names_group:
                        col_names_group.append(name)

                if len(col_names_group) <= 1:
                    continue

                base_name = f"__MERGED_{merge_idx}__"
                new_name = base_name
                suffix = 0
                while new_name in df.columns:
                    suffix += 1
                    new_name = f"{base_name}_{suffix}"

                df[new_name] = df[col_names_group].astype(str).agg(''.join, axis=1)
                df.drop(columns=col_names_group, inplace=True)

        num_rows, num_cols = df.shape
        if num_rows == 0 or num_cols <= 1:
            return df

        # Prepare string representations and statistics per column
        cols = list(df.columns)
        str_cols = []
        eq_probs = [0.0] * num_cols
        avg_lens = [0.0] * num_cols
        total_chars = 0

        for idx, col in enumerate(cols):
            col_list = df[col].astype(str).tolist()
            str_cols.append(col_list)

            cnt = Counter(col_list)
            n = float(num_rows)
            if n == 0:
                eq_prob = 0.0
            else:
                sum_sq = 0.0
                for f in cnt.values():
                    sum_sq += float(f) * float(f)
                eq_prob = sum_sq / (n * n)

            char_total = 0
            for v in col_list:
                char_total += len(v)

            eq_probs[idx] = eq_prob
            avg_lens[idx] = (char_total / n) if n > 0 else 0.0
            total_chars += char_total

        if total_chars == 0:
            return df

        # Approximate objective: enumerate permutations (num_cols is small)
        indices = list(range(num_cols))
        best_approx_perm = tuple(indices)
        best_approx_score = float('-inf')

        for perm in permutations(indices):
            prod = 1.0
            score = 0.0
            for idx in perm:
                prod *= eq_probs[idx]
                score += prod * avg_lens[idx]
            if score > best_approx_score:
                best_approx_score = score
                best_approx_perm = perm

        baseline_perm = tuple(range(num_cols))
        # Additional heuristic permutations
        eq_prob_desc_perm = tuple(
            sorted(range(num_cols), key=lambda i: eq_probs[i], reverse=True)
        )
        importance_perm = tuple(
            sorted(range(num_cols), key=lambda i: eq_probs[i] * avg_lens[i], reverse=True)
        )

        # Collect unique candidate permutations
        candidate_perms = []
        seen = set()
        for p in (baseline_perm, best_approx_perm, eq_prob_desc_perm, importance_perm):
            if p not in seen:
                seen.add(p)
                candidate_perms.append(p)

        # Evaluate candidates with exact trie-based hit rate
        best_perm_final = candidate_perms[0]
        best_hit = self._compute_hit_rate(str_cols, total_chars, best_perm_final)

        for perm in candidate_perms[1:]:
            hit = self._compute_hit_rate(str_cols, total_chars, perm)
            if hit > best_hit + 1e-12:
                best_hit = hit
                best_perm_final = perm

        ordered_cols = [cols[i] for i in best_perm_final]
        return df[ordered_cols]