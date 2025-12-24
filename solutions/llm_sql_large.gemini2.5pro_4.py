import pandas as pd
from joblib import Parallel, delayed
from typing import List, Dict

class Solution:
    """
    An expert programmer's solution to reorder CSV columns for maximizing KV-cache hit rate.
    """

    def _handle_col_merge(self, df: pd.DataFrame, col_merge: list = None) -> pd.DataFrame:
        """
        Merges specified column groups into single columns.
        """
        if not col_merge:
            return df

        df_copy = df.copy()
        cols_to_drop = set()

        for i, group in enumerate(col_merge):
            new_col_name = f"_merged_{i}"
            valid_group = [c for c in group if c in df_copy.columns]
            if not valid_group:
                continue

            new_col_series = df_copy[valid_group[0]].astype(str)
            for col in valid_group[1:]:
                new_col_series += df_copy[col].astype(str)
            df_copy[new_col_name] = new_col_series

            for col in valid_group:
                cols_to_drop.add(col)
        
        df_copy.drop(columns=list(cols_to_drop), inplace=True, errors='ignore')
        return df_copy

    def _classify_columns(self, df: pd.DataFrame, threshold: float) -> (List[str], List[str]):
        """
        Classifies columns into high and low cardinality based on a threshold.
        """
        num_rows = len(df)
        if num_rows == 0:
            return [], list(df.columns)

        high_card_cols = []
        low_card_cols = []
        
        try:
            nunique_series = df.nunique()
        except TypeError: 
            nunique_series = pd.Series({col: df[col].nunique() for col in df.columns})

        for col in df.columns:
            if nunique_series.get(col, 0) / num_rows > threshold:
                high_card_cols.append(col)
            else:
                low_card_cols.append(col)
        
        return high_card_cols, low_card_cols

    def _calculate_score_for_col(
        self, col: str, groups: Dict[int, list], df_sample_pos: pd.DataFrame, row_stop: int
    ) -> float:
        """
        Calculates a score for a column based on its ability to extend common prefixes.
        """
        total_score = 0.0
        col_series = df_sample_pos[col]

        for group_indices in groups.values():
            if len(group_indices) < row_stop:
                continue
            
            sub_series = col_series.iloc[group_indices]
            value_counts = sub_series.value_counts()
            counts_gt1 = value_counts[value_counts > 1]

            if not counts_gt1.empty:
                for val, n in counts_gt1.items():
                    length = len(val)
                    total_score += n * (n - 1) * length
        
        return total_score

    def _update_groups(
        self, groups: Dict[int, list], col: str, df_sample_pos: pd.DataFrame
    ) -> Dict[int, list]:
        """
        Updates row groups by sub-grouping based on the values of the new column.
        """
        new_groups = {}
        col_series = df_sample_pos[col]
        group_id_counter = 0
        
        for group_indices in groups.values():
            sub_series = col_series.iloc[group_indices]
            for _, subgroup in sub_series.groupby(sub_series, sort=False):
                new_groups[group_id_counter] = list(subgroup.index)
                group_id_counter += 1
        return new_groups

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
        """
        Reorder columns in the DataFrame to maximize prefix hit rate.
        """
        
        work_df = self._handle_col_merge(df, col_merge)

        if work_df.shape[1] <= 1:
            return work_df

        df_str = work_df.astype(str)
        
        high_card_cols, low_card_cols = self._classify_columns(df_str, distinct_value_threshold)

        if not low_card_cols:
            return work_df[high_card_cols]

        num_rows = len(df_str)
        n_sample = min(num_rows, 4000)

        if n_sample == 0:
            return work_df[low_card_cols + high_card_cols]
            
        df_sample = df_str.sample(n=n_sample, random_state=42)
        df_sample_pos = df_sample.reset_index(drop=True)

        ordered_cols = []
        remaining_cols = list(low_card_cols)
        
        groups = {0: list(range(n_sample))}
        
        num_cols_to_order = len(remaining_cols)
        for _ in range(num_cols_to_order):
            if not remaining_cols:
                break
            
            if parallel and len(remaining_cols) > 1:
                scores = Parallel(n_jobs=-1)(
                    delayed(self._calculate_score_for_col)(
                        col, groups, df_sample_pos, row_stop
                    ) for col in remaining_cols
                )
                scores_map = dict(zip(remaining_cols, scores))
            else:
                scores_map = {
                    col: self._calculate_score_for_col(col, groups, df_sample_pos, row_stop)
                    for col in remaining_cols
                }
            
            if not scores_map:
                break
                
            best_col = max(scores_map, key=scores_map.get)
            
            ordered_cols.append(best_col)
            remaining_cols.remove(best_col)
            
            if remaining_cols:
                groups = self._update_groups(groups, best_col, df_sample_pos)

        final_order = ordered_cols + remaining_cols + high_card_cols
        return work_df[final_order]
