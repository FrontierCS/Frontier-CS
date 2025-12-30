import pandas as pd
from multiprocessing import Pool, cpu_count
import itertools

def _calculate_pairwise_score(c1, c2, df_sample):
    if c1 == c2:
        return (c1, c2, len(df_sample))
    return (c1, c2, len(df_sample[[c1, c2]].drop_duplicates()))

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
        
        original_cols_list = list(df.columns)
        work_df = df.copy()

        merged_col_to_originals = {}
        if col_merge:
            cols_to_drop = set()
            for i, group in enumerate(col_merge):
                group_in_df = [c for c in group if c in work_df.columns]
                if not group_in_df:
                    continue
                
                new_col_name = f"__merged_{i}__"
                
                original_group_ordered = [c for c in original_cols_list if c in group_in_df]
                merged_col_to_originals[new_col_name] = original_group_ordered
                
                work_df[new_col_name] = work_df[group_in_df].astype(str).agg(''.join, axis=1)
                cols_to_drop.update(group_in_df)
            
            if cols_to_drop:
                work_df.drop(columns=list(cols_to_drop), inplace=True)

        df_str = work_df.astype(str)
        sample_df = df_str.head(min(len(df_str), early_stop))
        
        if sample_df.shape[1] <= 1:
            return df[original_cols_list]

        num_rows_sample = len(sample_df)
        if num_rows_sample == 0:
            return df[original_cols_list]
            
        nunique = sample_df.nunique()
        high_card_cols = set(nunique[nunique / num_rows_sample > distinct_value_threshold].index)
        
        cols_to_order = [c for c in work_df.columns if c not in high_card_cols]
        
        if not cols_to_order:
            cols_to_order = list(work_df.columns)
            high_card_cols = set()

        scores = {}
        if len(cols_to_order) > 1:
            cols_pairs = list(itertools.combinations(cols_to_order, 2))
            num_cores = cpu_count() if parallel else 1
            if parallel and len(cols_pairs) > 1:
                with Pool(processes=min(num_cores, len(cols_pairs))) as pool:
                    args = [(c1, c2, sample_df) for c1, c2 in cols_pairs]
                    results = pool.starmap(_calculate_pairwise_score, args)
                for c1, c2, score in results:
                    scores[(c1, c2)] = score
                    scores[(c2, c1)] = score
            else:
                for c1, c2 in cols_pairs:
                    score = len(sample_df[[c1, c2]].drop_duplicates())
                    scores[(c1, c2)] = score
                    scores[(c2, c1)] = score
        
        ordered_low_card_cols = []
        if cols_to_order:
            start_col_candidates = {c: nunique[c] for c in cols_to_order}
            start_col = min(start_col_candidates, key=start_col_candidates.get)
            
            path = [start_col]
            unvisited = set(cols_to_order)
            unvisited.remove(start_col)
            current_col = start_col
            
            while unvisited:
                neighbors = {c: scores.get((current_col, c), float('inf')) for c in unvisited}
                if not neighbors: 
                    break
                next_col = min(neighbors, key=neighbors.get)
                
                path.append(next_col)
                unvisited.remove(next_col)
                current_col = next_col
            ordered_low_card_cols = path

        ordered_high_card_cols = sorted(list(high_card_cols), key=lambda c: nunique[c])
        
        final_ordered_merged_cols = ordered_low_card_cols + ordered_high_card_cols
        
        final_original_order = []
        for col in final_ordered_merged_cols:
            if col in merged_col_to_originals:
                final_original_order.extend(merged_col_to_originals[col])
            else:
                final_original_order.append(col)
        
        if len(final_original_order) != len(original_cols_list):
            present_cols = set(final_original_order)
            missing_cols = [c for c in original_cols_list if c not in present_cols]
            final_original_order.extend(missing_cols)

        return df[final_original_order]