import pandas as pd
import numpy as np
from joblib import Parallel, delayed

def _entropy(series: pd.Series) -> float:
    """Helper function to calculate entropy of a series."""
    if series.empty:
        return 0.0
    
    counts = series.value_counts()
    probs = counts / len(series)
    
    if len(probs) <= 1:
        return 0.0
    
    return -np.sum(probs * np.log(probs))

def _calculate_joint_entropy(c: str, p_key: np.ndarray, df_sample: pd.DataFrame) -> tuple[str, float]:
    """Helper for parallel entropy calculation."""
    c_col = df_sample[c].to_numpy(dtype=str)
    pc_key = np.core.defchararray.add(p_key, c_col)
    pc_key_series = pd.Series(pc_key)
    return c, _entropy(pc_key_series)

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
        
        if col_merge:
            original_cols = df.columns.tolist()
            new_df_data = {}
            merged_cols = set()
            
            for i, group in enumerate(col_merge):
                merged_col_name = "_".join(map(str, group))
                new_df_data[merged_col_name] = df[group].astype(str).apply("".join, axis=1)
                for col in group:
                    merged_cols.add(col)
            
            for col in original_cols:
                if col not in merged_cols:
                    new_df_data[col] = df[col]
            
            df = pd.DataFrame(new_df_data)

        if df.shape[1] <= 1:
            return df

        sample_size = min(len(df), early_stop)
        if sample_size == 0:
            return df
        
        df_sample = df.iloc[:sample_size].astype(str)

        high_card_cols = []
        low_card_cols = []
        nunique_map = {}
        
        for col in df_sample.columns:
            n_unique = df_sample[col].nunique()
            nunique_map[col] = n_unique
            distinct_ratio = n_unique / sample_size if sample_size > 0 else 0
            if distinct_ratio > distinct_value_threshold and n_unique > 10:
                high_card_cols.append(col)
            else:
                low_card_cols.append(col)
        
        high_card_cols.sort(key=lambda c: nunique_map[c])
        
        ordered_low_card = []
        if low_card_cols:
            if len(low_card_cols) == 1:
                ordered_low_card = low_card_cols
            else:
                entropies = {c: _entropy(df_sample[c]) for c in low_card_cols}
                first_col = min(low_card_cols, key=lambda c: entropies[c])
                ordered_low_card.append(first_col)
                
                remaining_cols = [c for c in low_card_cols if c != first_col]
                p_key = df_sample[first_col].to_numpy(dtype=str)
                
                while remaining_cols:
                    if parallel and len(remaining_cols) > 1:
                        results = Parallel(n_jobs=-1, prefer="threads")(
                            delayed(_calculate_joint_entropy)(c, p_key, df_sample) for c in remaining_cols
                        )
                        entropies = {c: e for c, e in results}
                        best_c = min(entropies, key=entropies.get)
                    else:
                        best_c = None
                        min_joint_entropy = float('inf')
                        for c in remaining_cols:
                            _, joint_entropy = _calculate_joint_entropy(c, p_key, df_sample)
                            if joint_entropy < min_joint_entropy:
                                min_joint_entropy = joint_entropy
                                best_c = c

                    ordered_low_card.append(best_c)
                    remaining_cols.remove(best_c)
                    
                    if remaining_cols:
                        best_c_col = df_sample[best_c].to_numpy(dtype=str)
                        p_key = np.core.defchararray.add(p_key, best_c_col)

        final_order = ordered_low_card + high_card_cols
        return df[final_order]
