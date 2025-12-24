import pandas as pd
from joblib import Parallel, delayed

class Solution:
    def _find_best_order(
        self, df_sample: pd.DataFrame, cardinality: pd.Series, parallel: bool
    ) -> list:
        if df_sample.empty:
            return []

        cols = df_sample.columns.tolist()
        
        first_col = min(cols, key=lambda c: cardinality.get(c, float('inf')))
        
        ordered_cols = [first_col]
        remaining_cols = [c for c in cols if c != first_col]
        
        for _ in range(len(remaining_cols)):
            if not remaining_cols:
                break
            if len(remaining_cols) == 1:
                ordered_cols.append(remaining_cols[0])
                break

            current_groups = df_sample.groupby(ordered_cols, sort=False)
            
            def calculate_score(col: str) -> int:
                return current_groups[col].nunique().sum()

            if parallel and len(remaining_cols) > 1:
                scores = Parallel(n_jobs=-1, prefer="threads")(
                    delayed(calculate_score)(c) for c in remaining_cols
                )
                scores_map = dict(zip(remaining_cols, scores))
            else:
                scores_map = {c: calculate_score(c) for c in remaining_cols}

            best_col = min(scores_map, key=scores_map.get)
            
            ordered_cols.append(best_col)
            remaining_cols.remove(best_col)
            
        return ordered_cols

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
        if df.empty or len(df.columns) <= 1:
            return df
        
        df_processed = df.copy()

        if col_merge:
            all_cols = set(df_processed.columns)
            for group in col_merge:
                valid_group = [col for col in group if col in all_cols]
                if len(valid_group) > 1:
                    new_col_name = "_".join(valid_group)
                    temp_name = new_col_name
                    counter = 0
                    while temp_name in df_processed.columns:
                        counter += 1
                        temp_name = f"{new_col_name}_{counter}"
                    new_col_name = temp_name
                    
                    df_processed[new_col_name] = (
                        df_processed[valid_group].astype(str).agg("".join, axis=1)
                    )
                    df_processed = df_processed.drop(columns=valid_group)

        df_processed = df_processed.astype(str)

        sample_size = min(len(df_processed), 5000)
        sample_size = min(sample_size, early_stop)
        df_sample = df_processed.head(sample_size)

        if df_sample.empty:
            return df_processed
            
        cardinality = df_sample.nunique()
        
        if len(df_sample) > 0:
            distinct_count_threshold = len(df_sample) * distinct_value_threshold
        else:
            distinct_count_threshold = 0

        high_card_cols = cardinality[cardinality > distinct_count_threshold].index.tolist()
        low_card_cols = cardinality[cardinality <= distinct_count_threshold].index.tolist()
        
        high_card_cols.sort(key=lambda c: cardinality.get(c, float('inf')), reverse=True)
        
        df_sample_low_card = df_sample[low_card_cols] if low_card_cols else pd.DataFrame()
        
        ordered_low_card_cols = self._find_best_order(
            df_sample_low_card, cardinality, parallel
        )

        final_order = ordered_low_card_cols + high_card_cols
        
        if set(final_order) != set(df_processed.columns):
            return df_processed

        return df_processed[final_order]
