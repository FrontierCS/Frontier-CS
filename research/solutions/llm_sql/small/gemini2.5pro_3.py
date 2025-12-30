import pandas as pd
import numpy as np

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

        # 1. Handle Column Merges
        if col_merge:
            df_processed = df.copy()
            merged_cols_set = set()
            for group in col_merge:
                for col in group:
                    merged_cols_set.add(col)
            
            unmerged_cols = [c for c in df.columns if c not in merged_cols_set]
            
            new_cols = []
            for i, group in enumerate(col_merge):
                new_col_name = f"__merged_{i}__"
                df_processed[new_col_name] = df_processed[group].astype(str).apply("".join, axis=1)
                new_cols.append(new_col_name)

            df = df_processed[unmerged_cols + new_cols]

        # 2. Edge case: 0 or 1 column
        if df.shape[1] <= 1:
            return df

        cols = df.columns.tolist()

        # 3. Preprocessing and Sampling
        sample_size = min(len(df), 5000)
        df_sample = df.head(sample_size).astype(str)
        
        # 4. Heuristic for high-cardinality columns and entropy calculation
        low_card_cols = []
        high_card_cols = []
        individual_entropies = {}

        for c in cols:
            counts = df_sample[c].value_counts()
            n_unique = len(counts)
            
            if n_unique <= 1:
                entropy = -1.0
            else:
                probs = counts / sample_size
                entropy = -np.sum(probs * np.log2(probs))
            
            individual_entropies[c] = entropy
            
            if n_unique / sample_size > distinct_value_threshold and n_unique > 1:
                high_card_cols.append(c)
            else:
                low_card_cols.append(c)

        # 5. Factorize low-cardinality columns for efficient processing
        num_low_card_cols = len(low_card_cols)
        
        if num_low_card_cols == 0:
            p_final = sorted(high_card_cols, key=lambda c: individual_entropies[c])
            return df[p_final]

        df_cat = pd.DataFrame(index=df_sample.index)
        max_cardinalities = {}
        for col in low_card_cols:
            codes, uniques = pd.factorize(df_sample[col], sort=True)
            df_cat[col] = codes
            max_cardinalities[col] = len(uniques)

        # 6. Greedy search using conditional entropy
        p_low = []
        remaining_cols = sorted(low_card_cols, key=lambda c: individual_entropies[c])
        
        group_ids = np.zeros(sample_size, dtype=np.int64)
        num_groups = 1

        for k in range(num_low_card_cols):
            if len(remaining_cols) <= col_stop:
                break
            
            scores = {}
            for c in remaining_cols:
                c_codes = df_cat[c].to_numpy()
                c_cardinality = max_cardinalities[c]
                
                contingency_table = np.zeros((num_groups, c_cardinality), dtype=np.int32)
                np.add.at(contingency_table, (group_ids, c_codes), 1)
                
                group_sizes = contingency_table.sum(axis=1)
                valid_groups_mask = group_sizes > row_stop
                
                if not np.any(valid_groups_mask):
                    scores[c] = 0.0
                    continue

                valid_contingency = contingency_table[valid_groups_mask]
                valid_group_sizes = group_sizes[valid_groups_mask]
                
                probs = valid_contingency / valid_group_sizes[:, np.newaxis]
                
                log_probs = np.zeros_like(probs, dtype=float)
                non_zero_mask = probs > 0
                log_probs[non_zero_mask] = np.log2(probs[non_zero_mask])
                
                group_entropies = -np.sum(probs * log_probs, axis=1)
                
                total_weighted_entropy = np.sum(valid_group_sizes * group_entropies)
                scores[c] = total_weighted_entropy
            
            if not scores:
                best_col = remaining_cols[0]
            else:
                min_score = min(scores.values())
                best_candidates = [c for c, s in scores.items() if s == min_score]
                best_col = min(best_candidates, key=lambda c: individual_entropies[c])

            p_low.append(best_col)
            remaining_cols.remove(best_col)
            
            if k < num_low_card_cols - 1 and remaining_cols:
                best_col_codes = df_cat[best_col].to_numpy()
                best_col_cardinality = max_cardinalities[best_col]
                
                group_ids = group_ids * best_col_cardinality + best_col_codes
                _, group_ids = np.unique(group_ids, return_inverse=True)
                num_groups = group_ids.max() + 1 if len(group_ids) > 0 else 1
        
        # 7. Combine and return final permutation
        p_low.extend(sorted(remaining_cols, key=lambda c: individual_entropies[c]))
        
        high_card_cols.sort(key=lambda c: individual_entropies[c])
        
        p_final = p_low + high_card_cols

        return df[p_final]