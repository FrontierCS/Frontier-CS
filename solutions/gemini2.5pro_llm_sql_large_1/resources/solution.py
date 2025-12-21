import pandas as pd
import numpy as np
from joblib import Parallel, delayed

class Solution:
    """
    Implements a solution to reorder columns of a DataFrame to maximize
    the prefix KV-cache hit rate for LLM inference.
    """

    def _calculate_score(
        self, col_name: str, active_groups: list, col_values_map: dict
    ) -> int:
        """
        Calculates the score for a candidate column. The score is the total
        number of new unique groups it would create within the existing active groups.
        Lower score is better.
        """
        score = 0
        col_values = col_values_map[col_name]
        for group_indices in active_groups:
            # np.unique on a pre-fetched numpy array is very fast
            score += len(np.unique(col_values[group_indices]))
        return score

    def _update_groups(
        self, col_name: str, df_int: pd.DataFrame, groups: list
    ) -> list:
        """
        Updates the row groups based on the values of the newly added column.
        Only keeps groups with more than one member, as smaller groups
        cannot contribute to LCP.
        """
        new_groups = []
        col_series = df_int[col_name]
        for group_indices in groups:
            sub_series = col_series.iloc[group_indices]
            # Group the sub-series by its own values to find new subgroups
            for _, group in sub_series.groupby(sub_series):
                if len(group) > 1:
                    new_groups.append(group.index.to_list())
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
        
        Args:
            df: Input DataFrame to optimize
            early_stop: Early stopping parameter (default: 100000)
            row_stop: Row stopping parameter (default: 4)
            col_stop: Column stopping parameter (default: 2)
            col_merge: List of column groups to merge (columns in each group are merged into one)
            one_way_dep: List of one-way dependencies (not used in this variant)
            distinct_value_threshold: Threshold for distinct values (default: 0.7)
            parallel: Whether to use parallel processing (default: True)
        
        Returns:
            DataFrame with reordered columns (same rows, different column order)
        """
        
        if df.empty:
            return df

        working_df = df.copy()

        if col_merge:
            for i, group in enumerate(col_merge):
                new_col_name = f'merged_{i}'
                working_df[new_col_name] = working_df[group].astype(str).agg(''.join, axis=1)
            
            cols_to_drop = [col for group in col_merge for col in group]
            working_df = working_df.drop(columns=cols_to_drop)

        num_rows = len(working_df)
        high_card_cols = []
        low_card_cols = []
        for col in working_df.columns:
            nunique = working_df[col].nunique()
            if nunique == num_rows or (num_rows > 0 and nunique / num_rows > distinct_value_threshold):
                high_card_cols.append(col)
            else:
                low_card_cols.append(col)
        
        if not low_card_cols:
            if high_card_cols:
                cardinalities_high = working_df[high_card_cols].nunique()
                high_card_sorted = cardinalities_high.sort_values().index.tolist()
                return working_df[high_card_sorted]
            return working_df

        if num_rows > early_stop:
            df_sample = working_df.sample(n=early_stop, random_state=42)
        else:
            df_sample = working_df
        
        df_sample = df_sample.reset_index(drop=True)

        df_int = pd.DataFrame(index=df_sample.index)
        for col in low_card_cols:
            df_int[col] = pd.factorize(df_sample[col].astype(str))[0]

        ordered_cols = []
        remaining_cols = list(low_card_cols)
        groups = [df_int.index.to_list()]
        
        num_greedy_steps = min(len(remaining_cols), col_stop if col_stop > 0 else len(remaining_cols))

        low_card_cards = df_int[low_card_cols].nunique()
        col_values_map = {c: df_int[c].values for c in low_card_cols}

        for k in range(num_greedy_steps):
            if not remaining_cols or not groups:
                break
            
            active_groups = [g for g in groups if len(g) >= row_stop]
            if not active_groups:
                break
            
            if parallel:
                scores = Parallel(n_jobs=-1, prefer="threads")(
                    delayed(self._calculate_score)(c, active_groups, col_values_map) for c in remaining_cols
                )
                min_score = np.min(scores)
                candidate_indices = [i for i, s in enumerate(scores) if s == min_score]
                candidates = [remaining_cols[i] for i in candidate_indices]
                best_col = min(candidates, key=lambda c: low_card_cards[c])
            else:
                min_score = float('inf')
                best_col = None
                for c in remaining_cols:
                    score = self._calculate_score(c, active_groups, col_values_map)
                    if score < min_score:
                        min_score = score
                        best_col = c
                    elif score == min_score:
                        if best_col is None or low_card_cards[c] < low_card_cards[best_col]:
                            best_col = c
            
            if best_col is None: break
            
            ordered_cols.append(best_col)
            remaining_cols.remove(best_col)
            
            if k < num_greedy_steps - 1 and remaining_cols:
                groups = self._update_groups(best_col, df_int, groups)

        if remaining_cols:
            remaining_sorted = low_card_cards[remaining_cols].sort_values().index.tolist()
            ordered_cols.extend(remaining_sorted)
            
        final_order = ordered_cols
        if high_card_cols:
            cardinalities_high = working_df[high_card_cols].nunique()
            high_card_sorted = cardinalities_high.sort_values().index.tolist()
            final_order.extend(high_card_sorted)
        
        final_col_set = set(final_order)
        for col in working_df.columns:
            if col not in final_col_set:
                final_order.append(col)

        return working_df[final_order]
