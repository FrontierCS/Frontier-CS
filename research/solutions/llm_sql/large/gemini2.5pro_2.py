import pandas as pd
import numpy as np
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor, as_completed
import os

# This function must be defined at the top-level to be pickleable for multiprocessing.
def _calculate_cond_entropy_pair_job(series_c1: pd.Series, series_c2: pd.Series, h_c1: float) -> float:
    """
    Calculates the conditional entropy H(c2|c1).
    H(c2|c1) = H(c1, c2) - H(c1)
    """
    if series_c1.empty:
        return 0.0
    
    df_pair = pd.concat([series_c1, series_c2], axis=1)
    c1_name, c2_name = df_pair.columns
    
    joint_counts = df_pair.groupby([c1_name, c2_name], observed=True, sort=False).size()
    
    if joint_counts.empty:
        return -h_c1 

    joint_probs = joint_counts / len(df_pair)
    joint_entropy = -np.sum(joint_probs * np.log2(joint_probs))
    
    return joint_entropy - h_c1

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
        """
        Reorder columns in the DataFrame to maximize prefix hit rate.
        """
        
        work_df = df.copy()

        if col_merge:
            original_cols = work_df.columns.tolist()
            merged_cols_set = set()
            new_col_names = []
            for group in col_merge:
                if not group: continue
                mergable_group = [c for c in group if c in work_df.columns]
                if not mergable_group: continue
                
                merged_cols_set.update(mergable_group)
                new_col_name = '_'.join(mergable_group)
                new_col_names.append(new_col_name)
                work_df[new_col_name] = work_df[mergable_group].astype(str).agg(''.join, axis=1)
            
            unmerged_cols = [c for c in original_cols if c not in merged_cols_set]
            work_df = work_df[unmerged_cols + new_col_names]

        if work_df.shape[1] <= 1:
            return work_df

        sample_df = work_df.head(min(len(work_df), early_stop)).astype(str)
        
        final_permutation = self._find_best_permutation(sample_df, parallel)
        
        if not final_permutation:
            return work_df
        
        return work_df[final_permutation]

    def _get_entropy(self, series: pd.Series) -> float:
        if series.empty:
            return 0.0
        counts = series.value_counts()
        if counts.empty:
            return 0.0
        probs = counts / len(series)
        return -np.sum(probs * np.log2(probs))

    def _find_best_permutation(self, df_sample: pd.DataFrame, parallel: bool) -> list:
        columns = df_sample.columns.tolist()
        num_cols = len(columns)

        if num_cols <= 1:
            return columns
            
        entropies = {col: self._get_entropy(df_sample[col]) for col in columns}
        
        cond_entropies = defaultdict(dict)
        
        cpu_cores = os.cpu_count() or 1
        use_parallel = parallel and num_cols > 5 and cpu_cores > 1
        
        if use_parallel:
            with ProcessPoolExecutor(max_workers=cpu_cores) as executor:
                futures = {}
                for c1 in columns:
                    for c2 in columns:
                        if c1 != c2:
                            future = executor.submit(
                                _calculate_cond_entropy_pair_job, 
                                df_sample[c1], df_sample[c2], entropies[c1]
                            )
                            futures[future] = (c2, c1)
                
                for future in as_completed(futures):
                    c2, c1 = futures[future]
                    try:
                        cond_entropies[c1][c2] = future.result()
                    except Exception:
                        cond_entropies[c1][c2] = float('inf')
        else:
            for c1 in columns:
                for c2 in columns:
                    if c1 != c2:
                        cond_entropies[c1][c2] = _calculate_cond_entropy_pair_job(
                            df_sample[c1], df_sample[c2], entropies[c1]
                        )
        
        best_perm = []
        min_total_entropy = float('inf')

        num_starts = min(num_cols, max(1, int(num_cols * 0.2)))
        start_candidates = sorted(columns, key=lambda c: entropies[c])[:num_starts]

        for start_col in start_candidates:
            perm = [start_col]
            remaining = set(columns) - {start_col}
            current_col = start_col
            total_entropy = entropies[start_col]

            while remaining:
                next_col = min(remaining, key=lambda c: cond_entropies[current_col].get(c, float('inf')))
                perm.append(next_col)
                total_entropy += cond_entropies[current_col].get(next_col, float('inf'))
                remaining.remove(next_col)
                current_col = next_col
            
            if total_entropy < min_total_entropy:
                min_total_entropy = total_entropy
                best_perm = perm
        
        return best_perm if best_perm else columns