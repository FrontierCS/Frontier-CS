import pandas as pd
import numpy as np
from joblib import Parallel, delayed

class Solution:
    @staticmethod
    def _calculate_score_groupby(col: str, selected_cols: list, df_sample: pd.DataFrame) -> int:
        """
        Calculates the number of unique groups formed by adding a new column.
        This static method is designed to be picklable for parallel processing.
        """
        return df_sample.groupby(by=selected_cols + [col], sort=False).ngroups

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
        if df.empty:
            return df

        df_processed = df.copy()

        if col_merge:
            cols_to_drop = set()
            for group in col_merge:
                if not group:
                    continue
                
                valid_group = [c for c in group if c in df_processed.columns]
                if len(valid_group) < 1:
                    continue

                new_col_name = '_'.join(map(str, valid_group))
                df_processed[new_col_name] = df_processed[valid_group].astype(str).apply(''.join, axis=1)
                cols_to_drop.update(valid_group)
            
            if cols_to_drop:
                df_processed = df_processed.drop(columns=list(cols_to_drop))

        if len(df_processed.columns) <= 1:
            return df_processed
        
        num_rows, num_cols = df_processed.shape
        
        sample_size = min(num_rows, early_stop)
        df_sample = df_processed.head(sample_size)

        selected_cols = []
        remaining_cols = list(df_processed.columns)
        
        effective_col_stop = min(col_stop, num_cols)
        
        for _ in range(effective_col_stop):
            if not remaining_cols:
                break
            
            if selected_cols and sample_size > 0:
                num_groups = df_sample.groupby(by=selected_cols, sort=False).ngroups
                if sample_size > row_stop and num_groups >= sample_size - row_stop:
                    break
            
            if parallel:
                scores = Parallel(n_jobs=-1, prefer='threads')(
                    delayed(self._calculate_score_groupby)(col, selected_cols, df_sample)
                    for col in remaining_cols
                )
            else:
                scores = [
                    self._calculate_score_groupby(col, selected_cols, df_sample)
                    for col in remaining_cols
                ]
            
            if not scores:
                break

            best_col_idx = np.argmin(scores)
            best_col = remaining_cols.pop(best_col_idx)
            selected_cols.append(best_col)
            
        if remaining_cols:
            if sample_size > 0:
                nunique_cache = {
                    c: df_sample[c].nunique() for c in remaining_cols
                }
                
                threshold = sample_size * distinct_value_threshold
                
                high_card_cols = [c for c in remaining_cols if nunique_cache[c] > threshold]
                low_card_cols = [c for c in remaining_cols if nunique_cache[c] <= threshold]

                low_card_cols.sort(key=lambda c: nunique_cache[c])
                high_card_cols.sort(key=lambda c: nunique_cache[c])
                
                selected_cols.extend(low_card_cols)
                selected_cols.extend(high_card_cols)
            else:
                selected_cols.extend(remaining_cols)

        return df_processed[selected_cols]