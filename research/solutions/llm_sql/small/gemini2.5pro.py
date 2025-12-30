import pandas as pd
from joblib import Parallel, delayed

class Solution:
    def _handle_merges(self, df: pd.DataFrame, col_merge: list) -> pd.DataFrame:
        if not col_merge:
            return df.copy()

        df_copy = df.copy()
        processed_cols = set()
        new_df_parts = []

        for group in col_merge:
            if not group:
                continue
            
            group = sorted(list(set(col for col in group if col in df_copy.columns)))
            if not group:
                continue

            merged_col_name = "__".join(group)
            merged_series = df_copy[group].astype(str).agg("".join, axis=1)
            merged_series.name = merged_col_name
            new_df_parts.append(merged_series)
            processed_cols.update(group)

        unmerged_cols = [col for col in df_copy.columns if col not in processed_cols]
        if unmerged_cols:
            new_df_parts.append(df_copy[unmerged_cols])

        if not new_df_parts:
            return pd.DataFrame(index=df.index)
            
        return pd.concat(new_df_parts, axis=1)

    @staticmethod
    def _calculate_score(col: str, df: pd.DataFrame, current_order: list) -> int:
        if not current_order:
            return df[col].nunique()
        else:
            subset_cols = current_order + [col]
            return df.drop_duplicates(subset=subset_cols).shape[0]

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
            df_proc = self._handle_merges(df, col_merge)
        else:
            df_proc = df.copy()

        if df_proc.shape[1] <= 1:
            return df_proc
            
        df_str = df_proc.astype(str)
        sample_df = df_str.head(min(early_stop, len(df_str)))
        
        all_cols = list(sample_df.columns)
        
        high_card_cols = []
        low_card_cols = []
        
        sample_len = len(sample_df)
        if sample_len > 0:
            for col in all_cols:
                nunique = sample_df[col].nunique()
                if nunique / sample_len > distinct_value_threshold:
                    high_card_cols.append(col)
                else:
                    low_card_cols.append(col)
        else:
            low_card_cols = all_cols

        final_order = []
        cols_to_search = low_card_cols.copy()
        
        num_greedy_steps = min(col_stop, len(cols_to_search))
        
        for _ in range(num_greedy_steps):
            if not cols_to_search:
                break

            if parallel:
                scores = Parallel(n_jobs=-1, prefer="threads")(
                    delayed(self._calculate_score)(
                        c, sample_df, final_order
                    ) for c in cols_to_search
                )
                scores_map = dict(zip(cols_to_search, scores))
            else:
                scores_map = {
                    c: self._calculate_score(c, sample_df, final_order)
                    for c in cols_to_search
                }
            
            best_col = min(scores_map, key=scores_map.get)
            
            final_order.append(best_col)
            cols_to_search.remove(best_col)
            
        remaining_cols = cols_to_search + high_card_cols
        
        if remaining_cols:
            if sample_len > 0:
                remaining_uniques = {
                    c: sample_df[c].nunique() for c in remaining_cols
                }
                sorted_remaining = sorted(remaining_cols, key=lambda c: remaining_uniques[c])
            else:
                sorted_remaining = sorted(remaining_cols)
            
            final_order.extend(sorted_remaining)
            
        return df_proc[final_order]