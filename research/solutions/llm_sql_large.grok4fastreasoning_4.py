import pandas as pd

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
        df = df.copy()
        if col_merge is not None:
            for group in col_merge:
                if group:
                    new_col = '_'.join(group)
                    df[new_col] = df.apply(lambda r: ''.join(str(r[c]) for c in group), axis=1)
                    df.drop(columns=group, inplace=True)
        current_cols = list(df.columns)
        M = len(current_cols)
        if M == 0:
            return df
        str_rows = [[str(cell) for cell in row] for row in df.values]
        N = len(df)
        sample_size = row_stop * 50
        sample_size = min(sample_size, N)
        if N <= sample_size:
            sample_indices = list(range(N))
        else:
            step = max(1, N // sample_size)
            sample_indices = list(range(0, N, step))[:sample_size]
        sample_str_rows = [str_rows[i] for i in sample_indices]
        def compute_partial_score(perm, sample_str_rows):
            K = len(sample_str_rows)
            root = {}
            total_sum = 0.0
            total_len = 0
            for si in range(K):
                row = sample_str_rows[si]
                row_len = sum(len(row[p]) for p in perm)
                total_len += row_len
                if si > 0:
                    node = root
                    k = 0
                    broke = False
                    for p in perm:
                        for char in row[p]:
                            if char not in node:
                                broke = True
                                break
                            node = node[char]
                            k += 1
                        if broke:
                            break
                    total_sum += k
                node = root
                for p in perm:
                    for char in row[p]:
                        node = node.setdefault(char, {})
            return total_sum / total_len if total_len > 0 else 0.0
        candidates = []
        for col in range(M):
            score = compute_partial_score([col], sample_str_rows)
            candidates.append((score, [col]))
        candidates.sort(key=lambda x: x[0], reverse=True)
        beam = candidates[:col_stop]
        evals = M
        for depth in range(1, M):
            new_candidates = []
            for score, perm in beam:
                used = set(perm)
                remaining = [c for c in range(M) if c not in used]
                for next_col in remaining:
                    new_perm = perm[:] + [next_col]
                    new_score = compute_partial_score(new_perm, sample_str_rows)
                    new_candidates.append((new_score, new_perm))
                    evals += 1
                    if evals > early_stop:
                        new_candidates.sort(key=lambda x: x[0], reverse=True)
                        if new_candidates:
                            best = new_candidates[0][1]
                            used = set(best)
                            remaining = [c for c in range(M) if c not in used]
                            best += sorted(remaining)
                            reordered_cols = [current_cols[i] for i in best]
                            return df[reordered_cols]
            new_candidates.sort(key=lambda x: x[0], reverse=True)
            beam = new_candidates[:col_stop]
        if beam:
            beam.sort(key=lambda x: x[0], reverse=True)
            best_perm = beam[0][1]
        else:
            best_perm = list(range(M))
        reordered_cols = [current_cols[i] for i in best_perm]
        return df[reordered_cols]