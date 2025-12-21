import pandas as pd
import numpy as np
from joblib import Parallel, delayed
import itertools

class Solution:
    def _merge_columns(self, df: pd.DataFrame, col_merge: list) -> pd.DataFrame:
        df_copy = df.copy()
        merged_cols_names = set(itertools.chain.from_iterable(col_merge))
        
        new_cols_data = {}
        for i, group in enumerate(col_merge):
            new_col_name = f"_merged_{i}"
            valid_group = [c for c in group if c in df_copy.columns]
            if not valid_group: 
                continue
            
            new_cols_data[new_col_name] = df_copy[valid_group].astype(str).agg(''.join, axis=1)

        cols_to_drop = [c for c in merged_cols_names if c in df_copy.columns]
        if cols_to_drop:
            df_copy.drop(columns=cols_to_drop, inplace=True)
        
        for name, data in new_cols_data.items():
            df_copy[name] = data
            
        return df_copy
    
    def _calculate_score(self, col: str, df_str: pd.DataFrame, group_cols: list) -> float:
        if not group_cols:
            counts = df_str[col].value_counts()
            if counts.empty or counts.max() <= 1:
                return 0.0
            
            lengths = counts.index.str.len()
            score = np.sum((counts.values - 1) * lengths)
            return float(score)

        all_group_cols = group_cols + [col]
        try:
            # Using sort=False is faster but memory behavior can vary.
            # Using observed=True is a good practice with categoricals but here we have strings.
            counts = df_str.groupby(all_group_cols, sort=False).size()
        except Exception:
            return 0.0
        
        if counts.empty or counts.max() <= 1:
            return 0.0
        
        # `col` is the last column in `all_group_cols`, so its index is `len(group_cols)`.
        col_values_idx = counts.index.get_level_values(len(group_cols))
        
        unique_col_vals = col_values_idx.unique()
        len_map = {v: len(v) for v in unique_col_vals}
        lengths = col_values_idx.map(len_map)
        
        score = np.sum((counts.values - 1) * lengths.values)
        return float(score)

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
        
        if col_merge:
            df = self._merge_columns(df, col_merge)

        if df.shape[1] <= 1:
            return df

        if len(df) > early_stop:
            df_for_analysis = df.sample(n=early_stop, random_state=42)
        else:
            df_for_analysis = df

        df_str = df_for_analysis.astype(str)
        num_rows = len(df_str)
        
        if num_rows == 0:
            return df

        all_cols = list(df.columns)
        
        high_card_cols = []
        low_card_cols = []
        
        nunique = df_str.nunique()

        for col in all_cols:
            if nunique[col] / num_rows > distinct_value_threshold and nunique[col] > 10:
                high_card_cols.append(col)
            else:
                low_card_cols.append(col)

        ordered_cols = []
        group_cols = []
        
        remaining_low_card = low_card_cols.copy()
        
        num_greedy_steps = max(0, df.shape[1] - col_stop) if col_stop > 0 else df.shape[1]

        for _ in range(num_greedy_steps):
            if not remaining_low_card:
                break

            if group_cols:
                try:
                    num_groups = df_str.groupby(group_cols, sort=False).ngroups
                    avg_group_size = num_rows / num_groups if num_groups > 0 else num_rows
                    if avg_group_size < row_stop:
                        break
                except Exception:
                    pass

            candidate_cols = remaining_low_card
            
            if parallel and len(candidate_cols) > 1:
                scores = Parallel(n_jobs=-1, prefer="threads")(delayed(self._calculate_score)(c, df_str, group_cols) for c in candidate_cols)
            else:
                scores = [self._calculate_score(c, df_str, group_cols) for c in candidate_cols]

            if not scores or max(scores) <= 0:
                break
            
            best_idx = np.argmax(scores)
            best_col = candidate_cols[best_idx]
            
            ordered_cols.append(best_col)
            group_cols.append(best_col)
            remaining_low_card.remove(best_col)

        if remaining_low_card:
            remaining_scores = {c: self._calculate_score(c, df_str, []) for c in remaining_low_card}
            sorted_remaining_low = sorted(remaining_low_card, key=lambda c: remaining_scores[c], reverse=True)
            ordered_cols.extend(sorted_remaining_low)
            
        if high_card_cols:
            high_card_nunique = nunique[high_card_cols]
            sorted_high_card = high_card_nunique.sort_values(ascending=True).index.tolist()
            ordered_cols.extend(sorted_high_card)
            
        final_ordered_cols = ordered_cols
        if len(final_ordered_cols) < len(all_cols):
            missing_cols = [c for c in all_cols if c not in final_ordered_cols]
            if missing_cols:
                ordered_missing = sorted(missing_cols, key=lambda c: nunique[c])
                final_ordered_cols.extend(ordered_missing)

        return df[final_ordered_cols]
