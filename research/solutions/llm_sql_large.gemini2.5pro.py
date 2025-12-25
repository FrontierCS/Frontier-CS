import pandas as pd
import numpy as np
from joblib import Parallel, delayed

# Helper functions for parallel processing.
# Defined at the top level for easier pickling by joblib.
def _calculate_cheap_score_job(col: str, prefixes: pd.Series, df_sample_col: pd.Series):
    """Calculates a simple score based on group sizes."""
    temp_prefixes = prefixes + df_sample_col
    groups = temp_prefixes.value_counts(sort=False)
    # The score is sum(k^2), rewarding larger groups.
    return col, (groups.values**2).sum()

def _calculate_full_score_job(col: str, prefixes: pd.Series, df_sample_col: pd.Series):
    """Calculates the LCP-proxy score and new prefixes."""
    new_prefixes = prefixes + df_sample_col
    groups = new_prefixes.value_counts(sort=False)
    
    if groups.empty:
        return col, 0.0, new_prefixes
        
    counts = groups.values
    # Efficiently get lengths of string index
    lengths = groups.index.str.len().to_numpy(dtype=np.int64)
    
    # Score is sum(k*(k-1) * len(prefix)), a proxy for total LCP.
    # We omit the /2 as it's a constant factor.
    score = np.dot(counts * (counts - 1), lengths)
    return col, score, new_prefixes


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
        
        original_df = df
        
        # 1. Handle column merges. Merged columns are processed as single units.
        working_df, merge_map = self._handle_merges(df, col_merge)
        
        # 2. Preprocess: convert to string and sample for performance.
        df_str = working_df.astype(str)
        n_rows = min(len(df_str), early_stop)
        if n_rows == 0:
            return original_df
            
        df_sample = df_str.head(n_rows)

        # 3. Heuristic: Separate high-cardinality columns to be placed at the end.
        high_card_cols = []
        search_cols = []
        for col in df_sample.columns:
            # A high ratio of unique values suggests an ID-like column.
            if df_sample[col].nunique() / n_rows >= distinct_value_threshold:
                high_card_cols.append(col)
            else:
                search_cols.append(col)

        # Sort high-cardinality columns by cardinality (most unique goes last).
        if high_card_cols:
            high_card_nunique = df_sample[high_card_cols].nunique()
            high_card_cols.sort(key=lambda c: high_card_nunique[c], reverse=True)

        # 4. Core logic: Beam search to find the best ordering for the remaining columns.
        beam_width = row_stop
        all_cols_to_search = set(search_cols)
        num_search_cols = len(all_cols_to_search)
        
        best_order_search = []
        if num_search_cols > 0:
            initial_prefixes = pd.Series([''] * n_rows, index=df_sample.index, dtype=str)
            # A beam state is (score, ordered_columns_list, prefixes_series)
            beam = [(0.0, [], initial_prefixes)]
            n_jobs = 8 if parallel else 1 # Use 8 cores as per environment spec

            for _ in range(num_search_cols):
                all_candidates = []
                
                for score, ordered, prefixes in beam:
                    remaining = sorted(list(all_cols_to_search - set(ordered)))
                    if not remaining:
                        # This permutation is complete, carry it forward.
                        all_candidates.append((score, ordered, prefixes))
                        continue

                    # Prune candidate columns using a cheaper score to speed up search.
                    top_cols = remaining
                    if len(remaining) > col_stop > 0:
                        if parallel:
                            cheap_scores = Parallel(n_jobs=n_jobs, prefer="threads")(
                                delayed(_calculate_cheap_score_job)(col, prefixes, df_sample[col]) for col in remaining
                            )
                        else:
                            cheap_scores = [_calculate_cheap_score_job(col, prefixes, df_sample[col]) for col in remaining]
                        
                        cheap_scores.sort(key=lambda x: x[1], reverse=True)
                        top_cols = [col for col, _ in cheap_scores[:col_stop]]
                    
                    if not top_cols: continue

                    # Evaluate the top candidates using the full LCP-proxy score.
                    if parallel:
                        results = Parallel(n_jobs=n_jobs, prefer="threads")(
                            delayed(_calculate_full_score_job)(col, prefixes, df_sample[col]) for col in top_cols
                        )
                    else:
                        results = [_calculate_full_score_job(col, prefixes, df_sample[col]) for col in top_cols]
                    
                    for col, new_score, new_prefixes in results:
                        new_ordered = ordered + [col]
                        all_candidates.append((new_score, new_ordered, new_prefixes))

                if not all_candidates:
                    break
                
                # Select the top `beam_width` candidates for the next step.
                all_candidates.sort(key=lambda x: x[0], reverse=True)
                beam = all_candidates[:beam_width]

            if beam:
                best_order_search = beam[0][1]
        
        # 5. Finalize: Combine the ordered search columns and high-cardinality columns.
        best_order = best_order_search + high_card_cols
        
        # Un-merge columns to get the final order of original columns.
        final_order = []
        for col in best_order:
            if col in merge_map:
                final_order.extend(merge_map[col])
            else:
                final_order.append(col)
        
        # Ensure all original columns are present in the final output.
        original_cols_set = set(original_df.columns)
        final_order_set = set(final_order)
        if len(original_cols_set) > len(final_order_set):
            missing_cols = sorted(list(original_cols_set - final_order_set))
            final_order.extend(missing_cols)

        return original_df[final_order]

    def _handle_merges(self, df: pd.DataFrame, col_merge: list):
        """
        Merges specified column groups into single columns.
        Returns a new DataFrame and a map from merged names to original names.
        """
        if not col_merge:
            return df, {}

        working_df = df.copy()
        merge_map = {}
        merged_cols_set = set()
        for i, group in enumerate(col_merge):
            if not isinstance(group, list) or not group: continue
            
            # Create a unique name for the new merged column.
            new_col_name = f"__merged_{i}__"
            merge_map[new_col_name] = group
            
            for col in group:
                merged_cols_set.add(col)
            
            working_df[new_col_name] = working_df[group].astype(str).agg(''.join, axis=1)
        
        cols_to_keep = [c for c in df.columns if c not in merged_cols_set] + list(merge_map.keys())
        return working_df[cols_to_keep], merge_map
