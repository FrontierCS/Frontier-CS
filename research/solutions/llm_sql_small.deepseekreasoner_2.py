import pandas as pd
import random

class Solution:
    @staticmethod
    def evaluate_permutation(rows, perm):
        total_lcp = 0
        root = {}
        for row in rows:
            current = root
            lcp = 0
            matched = True
            for col_idx in perm:
                val = row[col_idx]
                if matched and val in current:
                    lcp += len(val)
                    current = current[val]
                else:
                    if matched:
                        matched = False
                    if val not in current:
                        current[val] = {}
                    current = current[val]
            total_lcp += lcp
        return total_lcp

    def solve(self, df, early_stop=100000, row_stop=4, col_stop=2, col_merge=None, one_way_dep=None, distinct_value_threshold=0.7, parallel=True):
        if col_merge is not None:
            new_data = {}
            cols_to_drop = set()
            for group in col_merge:
                new_col_name = '_'.join(group)
                merged_series = df[group[0]].astype(str)
                for col in group[1:]:
                    merged_series += df[col].astype(str)
                new_data[new_col_name] = merged_series
                cols_to_drop.update(group)
            for col in df.columns:
                if col not in cols_to_drop:
                    new_data[col] = df[col]
            df = pd.DataFrame(new_data)

        if len(df.columns) == 1:
            return df

        columns = list(df.columns)
        M = len(columns)

        rows = []
        for _, row in df.iterrows():
            rows.append([str(val) for val in row])

        eval_count = 0
        def evaluate(perm):
            nonlocal eval_count
            eval_count += 1
            return Solution.evaluate_permutation(rows, perm)

        remaining = list(range(M))
        perm = []
        for step in range(M):
            if eval_count >= early_stop:
                break
            best_col = None
            best_score = -1
            for col in remaining:
                candidate_perm = perm + [col]
                score = evaluate(candidate_perm)
                if score > best_score:
                    best_score = score
                    best_col = col
            if best_col is None:
                break
            perm.append(best_col)
            remaining.remove(best_col)

        if len(perm) < M:
            perm = perm + [c for c in range(M) if c not in perm]

        current_perm = perm
        current_score = evaluate(current_perm)

        improved = True
        while improved and eval_count < early_stop:
            improved = False
            swaps = [(i, j) for i in range(M) for j in range(i+1, M)]
            best_swap = None
            best_new_score = current_score

            for i, j in swaps:
                if eval_count >= early_stop:
                    break
                new_perm = current_perm.copy()
                new_perm[i], new_perm[j] = new_perm[j], new_perm[i]
                new_score = evaluate(new_perm)
                if new_score > best_new_score:
                    best_new_score = new_score
                    best_swap = (i, j)

            if best_new_score > current_score:
                i, j = best_swap
                current_perm[i], current_perm[j] = current_perm[j], current_perm[i]
                current_score = best_new_score
                improved = True

        max_restarts = 20
        for _ in range(max_restarts):
            if eval_count >= early_stop:
                break
            random_perm = list(range(M))
            random.shuffle(random_perm)
            random_score = evaluate(random_perm)
            if random_score > current_score:
                current_perm = random_perm
                current_score = random_score

        reordered_columns = [columns[i] for i in current_perm]
        result_df = df[reordered_columns]
        return result_df