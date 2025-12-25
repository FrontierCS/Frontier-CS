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
        if col_merge is None:
            col_merge = []
        
        # Apply column merges
        new_df = df.copy()
        used_cols = set()
        new_column_order = []
        for group in col_merge:
            group = [str(c) for c in group]  # Ensure strings
            if len(group) == 1:
                col = group[0]
                if col in new_df.columns:
                    new_column_order.append(col)
                    used_cols.add(col)
                continue
            
            # Merge group
            merged_name = '_'.join(sorted(group))
            merged_values = []
            for idx in range(len(new_df)):
                vals = [str(new_df.iloc[idx][c]) for c in group if c in new_df.columns]
                merged_values.append(''.join(vals))
            new_df[merged_name] = merged_values
            new_column_order.append(merged_name)
            used_cols.update(group)
        
        # Add remaining columns
        for col in df.columns:
            if col not in used_cols:
                new_column_order.append(col)
        
        # Drop original columns that were merged (groups >1)
        for col in list(new_df.columns):
            if col in used_cols and col not in new_column_order:
                new_df = new_df.drop(columns=[col])
        
        # Reorder to new_column_order
        existing_cols = [c for c in new_column_order if c in new_df.columns]
        new_df = new_df[existing_cols]
        df = new_df
        
        N, M = df.shape
        if M <= 1:
            return df
        
        # Precompute string data
        data = df.astype(str).values
        
        # Compute scores for each column
        col_scores = []
        for c in range(M):
            seen = set()
            num_hits = 0
            col_len_sum = 0
            for i in range(N):
                val = data[i, c]
                col_len_sum += len(val)
                if i > 0 and val in seen:
                    num_hits += 1
                seen.add(val)
            avg_len = col_len_sum / N if N > 0 else 0
            hit_frac = num_hits / max(1, N - 1)
            score = hit_frac * avg_len
            col_scores.append(score)
        
        # Get permutation: sort by decreasing score
        sorted_cols = sorted(range(M), key=lambda c: col_scores[c], reverse=True)
        
        # Reorder DataFrame
        df = df.iloc[:, sorted_cols]
        
        return df
